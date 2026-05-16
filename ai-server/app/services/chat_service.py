"""ChatService — 단일 LLM 호출 모델.

핵심 정책:
  - LLM은 dialog 완료 시점에 단 1회만 호출한다.
  - 칩 턴은 BE raw 저장만. 텍스트 입력은 누적 → 완료 시 LLM 1회 추출.

Dialog 흐름:
  step 0 (첫 호출):     자본금 질문
  step 1 (답변 1번):    거래 유형 질문 (전세/월세/매매 칩)
  step 2 (답변 2번):
    - deal_type=monthly_rent & monthly_rent_max 없음 → 월세 예산 질문
    - 그 외 (전세/매매) → 완료
  step 3 (답변 3번):    완료 (월세 예산 받은 후)

완료 = 누적 raw_message가 있으면 LLM 1회 → BE 필터 → 결과.
"""

from __future__ import annotations

import httpx

from app.config import Settings
from app.schemas import ChatRequest, ChatResponse, Conditions, DealType
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

            conditions = upserted.conditions

            if step == 2 and conditions.deal_type == DealType.MONTHLY_RENT and conditions.monthly_rent_max is None:
                # 월세 선택 → 월세 예산 추가 질문
                return ChatResponse(
                    session_id=sid,
                    state="asking",
                    bot_messages=self.message_builder.ask_monthly_rent(),
                )

            # step >= 2 (전세/매매) 또는 step >= 3 (월세): dialog 완료.
            # 누적 텍스트 있으면 LLM 1회 호출.
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
        """raw에 의미 있는 값이 있으면 True."""
        return bool(raw.model_dump(exclude_none=True, exclude={"preference_text"}))

    @staticmethod
    def _needs_extraction(conditions: Conditions) -> bool:
        """LLM 추출이 필요한 경우: 필수 키 누락."""
        if conditions.budget_max is None or conditions.deal_type is None:
            return True
        if conditions.deal_type == DealType.MONTHLY_RENT and conditions.monthly_rent_max is None:
            return True
        return False
