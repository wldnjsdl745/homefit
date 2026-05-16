"""ChatService — 단일 LLM 호출 모델.

핵심 정책 (사용자 요구):
  - LLM은 **dialog 완료 시점에 단 1회만** 호출한다.
  - 턴별 LLM 호출 없음 (느리고 낭비). 칩으로 답한 turn은 BE에 raw 저장만.
  - 사용자가 텍스트로 답한 경우 raw_message를 누적 → 완료 시점에 한 번 합쳐서 추출.

Dialog 흐름 (preference 단계 제거됨):
  step 0 (첫 호출):     자본금 질문
  step 1 (답변 1번):    거래 유형 질문
  step 2 (답변 2번):    완료 → 누적 raw_message가 있으면 LLM 1회 호출 → BE 필터 → 결과

세션 상태는 ai-server 메모리에 유지(`_session_state`). 데모 단계엔 충분하고,
BE 영속화는 추후 BE에서 turn_count/messages 노출 시 옮길 수 있다.
"""

from __future__ import annotations

import httpx

from app.config import Settings
from app.schemas import ChatRequest, ChatResponse, Conditions
from app.services.backend_client import BackendClient
from app.services.llm_provider import DummyLlmProvider, LlmProvider
from app.services.merge_service import MergeService
from app.services.message_builder import MessageBuilder


class _SessionState:
    __slots__ = ("step", "messages")

    def __init__(self) -> None:
        self.step: int = 0
        self.messages: list[str] = []


class ChatService:
    def __init__(
        self,
        backend_client: BackendClient,
        settings: Settings,
        message_builder: MessageBuilder | None = None,
        llm_provider: LlmProvider | None = None,
        merge_service: MergeService | None = None,
    ):
        self.backend_client = backend_client
        self.settings = settings
        self.message_builder = message_builder or MessageBuilder()
        self.llm_provider = llm_provider or DummyLlmProvider()
        self.merge_service = merge_service or MergeService()
        # In-memory 세션 상태. 데모용. ai-server 재시작 시 손실.
        self._session_state: dict[str, _SessionState] = {}

    async def handle(self, request: ChatRequest) -> ChatResponse:
        if self.settings.dummy_fail:
            return self._fallback(request.session_id)

        try:
            # 1) BE에 세션 등록 + 칩에서 받은 raw 저장 (LLM 호출 X)
            upserted = await self.backend_client.upsert_conditions(
                session_id=request.session_id,
                raw=request.raw,
                conditions=request.raw,
            )
            sid = upserted.session_id

            # 2) 세션 상태 초기화/조회
            state = self._session_state.setdefault(sid, _SessionState())

            # 3) 사용자가 이번 턴에 응답했는지 판정 (칩 또는 텍스트)
            responded = self._has_chip_response(request.raw) or bool(request.raw_message)
            if responded:
                state.step += 1
                if request.raw_message:
                    state.messages.append(request.raw_message)

            step = state.step

            # 4) 단계별 응답
            if step == 0:
                # 첫 호출 — 환영 + 자본금 질문
                return ChatResponse(
                    session_id=sid,
                    state="asking",
                    bot_messages=self.message_builder.ask_budget(),
                )

            if step == 1:
                # 자본금 답변 받음 — 거래 유형 질문
                return ChatResponse(
                    session_id=sid,
                    state="asking",
                    bot_messages=self.message_builder.ask_deal_type(),
                )

            # step >= 2: dialog 완료. 누적 텍스트 있으면 LLM 1회 호출.
            conditions = upserted.conditions
            if self._needs_extraction(conditions) and state.messages:
                combined = " / ".join(state.messages)
                extracted = await self.llm_provider.extract_conditions(combined)
                conditions = self.merge_service.merge(conditions, extracted)
                # 추출된 conditions를 BE에 반영
                upserted2 = await self.backend_client.upsert_conditions(
                    session_id=sid,
                    raw=conditions,
                    conditions=conditions,
                )
                conditions = upserted2.conditions

            # 5) BE 필터링 → 결과
            regions = await self.backend_client.filter_regions(conditions)
            return ChatResponse(
                session_id=sid,
                state="result",
                bot_messages=self.message_builder.result(conditions, regions.regions),
            )

        except (httpx.HTTPError, ValueError):
            return self._fallback(request.session_id)

    def _fallback(self, session_id: str | None) -> ChatResponse:
        return ChatResponse(
            session_id=session_id or "fallback",
            state="asking",
            bot_messages=self.message_builder.fallback(),
        )

    @staticmethod
    def _has_chip_response(raw: Conditions) -> bool:
        """raw에 의미 있는 값(budget_max 또는 deal_type)이 있으면 True."""
        return bool(raw.model_dump(exclude_none=True, exclude={"preference_text"}))

    @staticmethod
    def _needs_extraction(conditions: Conditions) -> bool:
        """budget_max 또는 deal_type 중 하나라도 비어있으면 LLM 추출 필요."""
        return conditions.budget_max is None or conditions.deal_type is None
