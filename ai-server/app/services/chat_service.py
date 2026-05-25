"""ChatService — 단일 LLM 호출 모델.

핵심 정책:
  - LLM은 dialog 완료 시점에 단 1회만 호출한다.
  - 칩 턴은 BE raw 저장만. 텍스트 입력은 누적 → 완료 시 LLM 1회 추출.

Dialog 흐름:
  step 0 (첫 호출):     자본금 질문
  step 1 (답변 1번):    거래 유형 질문 (전세/월세/매매 칩)
  step 2 (답변 2번):    통근 목적지 질문 (업무지구 칩)
  step 3 (답변 3번):
    - deal_type=monthly_rent & monthly_rent_max 없음 → 월세 예산 질문
    - 그 외 (전세/매매) → 완료
  step 4 (답변 4번):    완료 (월세 예산 받은 후)

완료 = 누적 raw_message가 있으면 LLM 1회 → BE 필터 → 결과.

BE 호출 규칙:
  - upsert-conditions: raw(이번 턴 입력) + conditions(누적 머지 결과) 분리 전달.
  - 세션 상태(step, 누적 conditions)는 in-memory로 유지. (데모용, 재시작 시 손실)
"""

from __future__ import annotations

import httpx

from app.config import Settings
from app.schemas import ChatRequest, ChatResponse, CommuteDestination, Conditions, DealType, ErrorResponse
from app.services.backend_client import BackendClient, BackendClientError
from app.services.llm_provider import DummyLlmProvider, LlmProvider
from app.services.merge_service import MergeService
from app.services.message_builder import MessageBuilder

_WORKPLACE_TO_COMMUTE: dict[str, CommuteDestination] = {
    # 강남권
    "강남": CommuteDestination.GANGNAM,
    "논현": CommuteDestination.GANGNAM,
    "역삼": CommuteDestination.GANGNAM,
    "선릉": CommuteDestination.GANGNAM,
    "삼성": CommuteDestination.GANGNAM,
    "도곡": CommuteDestination.GANGNAM,
    "양재": CommuteDestination.GANGNAM,
    "신논현": CommuteDestination.GANGNAM,
    "테헤란": CommuteDestination.GANGNAM,
    "대치": CommuteDestination.GANGNAM,
    # 여의도권
    "여의도": CommuteDestination.YEOUIDO,
    "영등포": CommuteDestination.YEOUIDO,
    "당산": CommuteDestination.YEOUIDO,
    # 광화문권
    "광화문": CommuteDestination.GWANGHWAMUN,
    "종로": CommuteDestination.GWANGHWAMUN,
    "을지로": CommuteDestination.GWANGHWAMUN,
    "시청": CommuteDestination.GWANGHWAMUN,
    "청계천": CommuteDestination.GWANGHWAMUN,
    "세종대로": CommuteDestination.GWANGHWAMUN,
    "명동": CommuteDestination.GWANGHWAMUN,
    # 홍대권
    "홍대": CommuteDestination.HONGDAE,
    "신촌": CommuteDestination.HONGDAE,
    "합정": CommuteDestination.HONGDAE,
    "망원": CommuteDestination.HONGDAE,
    "연남": CommuteDestination.HONGDAE,
    "상수": CommuteDestination.HONGDAE,
    # 잠실권
    "잠실": CommuteDestination.JAMSIL,
    "송파": CommuteDestination.JAMSIL,
    "석촌": CommuteDestination.JAMSIL,
    "문정": CommuteDestination.JAMSIL,
    "가락": CommuteDestination.JAMSIL,
}


def _resolve_commute(workplace: str | None) -> CommuteDestination | None:
    if not workplace:
        return None
    normalized = workplace.replace(" ", "")
    for keyword, dest in _WORKPLACE_TO_COMMUTE.items():
        if keyword in normalized:
            return dest
    return None


_SYS_ERROR = ErrorResponse(
    code="AI-SYS-001",
    message="AI 서버가 테스트 실패 모드로 실행 중이에요.",
    detail="dummy_fail=True",
)


class _SessionState:
    __slots__ = ("step", "conditions", "messages")

    def __init__(self) -> None:
        self.step: int = 0
        self.conditions: Conditions = Conditions()
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
            return self._fallback(request.session_id, _SYS_ERROR)

        try:
            # 1) 이전 누적 조건 조회 → 이번 턴 raw 머지
            prior = (
                self._session_state[request.session_id]
                if request.session_id and request.session_id in self._session_state
                else _SessionState()
            )
            merged = self.merge_service.merge(prior.conditions, request.raw)

            # 1.5) workplace 있으면 즉시 commute_destination으로 변환 (LLM 불필요)
            if merged.workplace and merged.commute_destination is None:
                resolved = _resolve_commute(merged.workplace)
                if resolved:
                    merged = merged.model_copy(update={"commute_destination": resolved})

            # 2) BE에 세션 등록 + raw(이번 턴) / conditions(누적 머지) 분리 저장
            upserted = await self.backend_client.upsert_conditions(
                session_id=request.session_id,
                raw=request.raw,
                conditions=merged,
            )
            sid = upserted.session_id

            # 3) 세션 상태 초기화/조회 (sid 기준)
            state = self._session_state.setdefault(sid, _SessionState())
            state.conditions = upserted.conditions  # BE 반환값을 truth로

            # 4) 사용자가 이번 턴에 응답했는지 판정 (칩 또는 텍스트)
            responded = self._has_chip_response(request.raw) or bool(request.raw_message)
            if responded:
                state.step += 1
                if request.raw_message:
                    state.messages.append(request.raw_message)

            step = state.step

            # 5) 단계별 응답
            if step == 0:
                return ChatResponse(
                    session_id=sid,
                    state="asking",
                    bot_messages=self.message_builder.ask_budget(),
                )

            if step == 1:
                return ChatResponse(
                    session_id=sid,
                    state="asking",
                    bot_messages=self.message_builder.ask_deal_type(),
                )

            if step == 2:
                return ChatResponse(
                    session_id=sid,
                    state="asking",
                    bot_messages=self.message_builder.ask_commute(),
                )

            conditions = state.conditions

            if step == 3 and conditions.deal_type == DealType.MONTHLY_RENT and conditions.monthly_rent_max is None:
                return ChatResponse(
                    session_id=sid,
                    state="asking",
                    bot_messages=self.message_builder.ask_monthly_rent(),
                )

            # 6) Dialog 완료. 누적 텍스트 있으면 LLM 1회 추출 → workplace 매핑 → BE 재저장.
            if state.messages:
                combined = " / ".join(state.messages)
                extracted = await self.llm_provider.extract_conditions(combined)
                # workplace → commute_destination 매핑 (LLM이 동네 이름을 추출했으면)
                if extracted.workplace and extracted.commute_destination is None:
                    resolved = _resolve_commute(extracted.workplace)
                    if resolved:
                        extracted = extracted.model_copy(update={"commute_destination": resolved})
                conditions = self.merge_service.merge(conditions, extracted)
                upserted2 = await self.backend_client.upsert_conditions(
                    session_id=sid,
                    raw=extracted,
                    conditions=conditions,
                )
                conditions = upserted2.conditions
                state.conditions = conditions

            # 7) 필수 조건 검증 — LLM 추출 후에도 없으면 다시 질문
            if conditions.deal_type is None:
                state.step = 1  # ask_deal_type 재진입
                return ChatResponse(
                    session_id=sid,
                    state="asking",
                    bot_messages=self.message_builder.ask_deal_type(),
                )

            if conditions.budget_max is None:
                state.step = 0  # ask_budget 재진입
                return ChatResponse(
                    session_id=sid,
                    state="asking",
                    bot_messages=self.message_builder.ask_budget(),
                )

            # 8) BE 필터링 → 결과
            regions = await self.backend_client.filter_regions(conditions)
            return ChatResponse(
                session_id=sid,
                state="result",
                bot_messages=self.message_builder.result(conditions, regions.apartments),
            )

        except BackendClientError as exc:
            return self._fallback(request.session_id, exc.error)
        except (httpx.HTTPError, ValueError):
            return self._fallback(request.session_id)

    def _fallback(self, session_id: str | None, error: ErrorResponse | None = None) -> ChatResponse:
        if error:
            msg = f"{error.message} ({error.code})"
        else:
            msg = "죄송해요, 다시 시도해주세요."
        return ChatResponse(
            session_id=session_id or "fallback",
            state="asking",
            error=error,
            bot_messages=self.message_builder.fallback(msg),
        )

    @staticmethod
    def _has_chip_response(raw: Conditions) -> bool:
        """raw에 의미 있는 값이 있으면 True."""
        return bool(raw.model_dump(exclude_none=True, exclude={"preference_text"}))
