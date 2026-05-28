"""ChatService — 조건 기반 대화 오케스트레이션.

핵심 정책:
  - 사용자가 한 문장에 조건을 모두 말하면 즉시 결과로 간다.
  - 조건이 부족하면 누락된 항목만 이어서 질문한다.
  - 결과 이후에도 같은 session_id로 조건을 바꾸면 기존 조건 위에 덮어쓴다.
  - 텍스트 입력은 로컬 규칙 + LLM 의미 추출을 매 턴 병합한다.

Dialog 흐름:
  예산 → 거래 유형 → 월세 상한(월세인 경우) → 희망 지역 → 통근/자주 가는 곳
  → 선호 연령층 → 중요 인프라 → 결과.

BE 호출 규칙:
  - upsert-conditions: raw(이번 턴 입력) + conditions(누적 머지 결과) 분리 전달.
  - 세션 상태(누적 conditions)는 in-memory로 유지. (데모용, 재시작 시 손실)
"""

from __future__ import annotations

import re

import httpx

from app.config import Settings
from app.schemas import (
    AgeGroupPreference,
    ChatRequest,
    ChatResponse,
    CommuteDestination,
    Conditions,
    DealType,
    ErrorResponse,
    InfrastructurePriority,
)
from app.services.backend_client import BackendClient, BackendClientError
from app.services.dialog_policy import DialogPolicy, DialogStep
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


_NO_PREFERENCE_RE = re.compile(r"(상관\s*없|무관|아무\s*곳|아무\s*데|없어|없음|괜찮)")

_SEOUL_REGION_RE = re.compile(r"([가-힣]{2,}(?:구|동))")


class _SessionState:
    __slots__ = ("conditions", "messages")

    def __init__(self) -> None:
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
        self.dialog_policy = DialogPolicy()
        # In-memory 세션 상태. 데모용. ai-server 재시작 시 손실.
        self._session_state: dict[str, _SessionState] = {}

    async def handle(self, request: ChatRequest) -> ChatResponse:
        if self.settings.dummy_fail:
            return self._fallback(request.session_id, _SYS_ERROR)

        try:
            # 1) 이전 누적 조건 조회 → 이번 턴 raw/텍스트 추출 결과를 모두 머지
            prior = (
                self._session_state[request.session_id]
                if request.session_id and request.session_id in self._session_state
                else _SessionState()
            )

            merged = self.merge_service.merge(prior.conditions, request.raw)
            turn_raw = request.raw

            if request.raw_message:
                extracted = await self._extract_from_text(request.raw_message)
                merged = self.merge_service.merge(merged, extracted)
                turn_raw = self.merge_service.merge(turn_raw, extracted)

                contextual = self._contextual_no_preference(request.raw_message, merged)
                merged = self.merge_service.merge(merged, contextual)
                turn_raw = self.merge_service.merge(turn_raw, contextual)
                prior.messages.append(request.raw_message)

            merged = self._resolve_derived_fields(merged)
            turn_raw = self._resolve_derived_fields(turn_raw)

            # 2) BE에 세션 등록 + raw(이번 턴) / conditions(누적 머지) 분리 저장
            upserted = await self.backend_client.upsert_conditions(
                session_id=request.session_id,
                raw=turn_raw,
                conditions=merged,
            )
            sid = upserted.session_id

            # 3) 세션 상태 초기화/조회 (sid 기준)
            state = self._session_state.setdefault(sid, _SessionState())
            # BE 응답을 기본 truth로 삼되, 이번 턴에서 AI 서버가 이미 검증한
            # 조건을 다시 얹는다. 운영에서 BE 응답/이전 세션 상태가 일부 키를
            # 누락해도 현재 턴의 명시 입력이 대화 단계에서 사라지지 않게 한다.
            state.conditions = self.merge_service.merge(upserted.conditions, turn_raw)
            state.messages = prior.messages

            # 4) 누락된 조건만 이어서 질문한다. 이미 충분하면 즉시 결과를 반환한다.
            conditions = self._resolve_derived_fields(state.conditions)
            state.conditions = conditions
            next_step = self.dialog_policy.next_step(conditions)

            if next_step == DialogStep.ASK_BUDGET:
                return ChatResponse(
                    session_id=sid,
                    state="asking",
                    bot_messages=self.message_builder.ask_budget(),
                )

            if next_step == DialogStep.ASK_DEAL_TYPE:
                return ChatResponse(
                    session_id=sid,
                    state="asking",
                    bot_messages=self.message_builder.ask_deal_type(),
                )

            if next_step == DialogStep.ASK_MONTHLY_RENT:
                return ChatResponse(
                    session_id=sid,
                    state="asking",
                    bot_messages=self.message_builder.ask_monthly_rent(),
                )

            if next_step == DialogStep.ASK_PREFERRED_REGION:
                return ChatResponse(
                    session_id=sid,
                    state="asking",
                    bot_messages=self.message_builder.ask_preferred_region(),
                )

            if next_step == DialogStep.ASK_COMMUTE:
                return ChatResponse(
                    session_id=sid,
                    state="asking",
                    bot_messages=self.message_builder.ask_commute(),
                )

            if next_step == DialogStep.ASK_AGE_GROUP:
                return ChatResponse(
                    session_id=sid,
                    state="asking",
                    bot_messages=self.message_builder.ask_age_group(),
                )

            if next_step == DialogStep.ASK_INFRASTRUCTURE:
                return ChatResponse(
                    session_id=sid,
                    state="asking",
                    bot_messages=self.message_builder.ask_infrastructure(),
                )

            # 5) BE 필터링 → 결과. 이후 같은 session_id로 조건을 바꾸면 여기로 다시 온다.
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

    async def _extract_from_text(self, raw_message: str) -> Conditions:
        local = self._extract_locally(raw_message)
        llm = await self.llm_provider.extract_conditions(raw_message)
        # 로컬 규칙은 금액/거래유형/자주 쓰는 키워드의 결정론적 보정용이다.
        return self.merge_service.merge(llm, local)

    def _resolve_derived_fields(self, conditions: Conditions) -> Conditions:
        if conditions.workplace and conditions.commute_destination is None:
            resolved = _resolve_commute(conditions.workplace)
            if resolved:
                return conditions.model_copy(update={"commute_destination": resolved})
        return conditions

    def _contextual_no_preference(self, raw_message: str, conditions: Conditions) -> Conditions:
        if not _NO_PREFERENCE_RE.search(raw_message):
            return Conditions()

        next_step = self.dialog_policy.next_step(conditions)
        updates = {}
        compact = raw_message.replace(" ", "")

        if next_step == DialogStep.ASK_PREFERRED_REGION or "지역" in compact:
            updates.setdefault("preferred_region", "상관없음")
        if (
            next_step == DialogStep.ASK_COMMUTE
            or "출근" in compact
            or "출퇴근" in compact
            or "직장" in compact
            or "회사" in compact
        ):
            updates.setdefault("workplace", "상관없음")
        if next_step == DialogStep.ASK_AGE_GROUP or "연령" in compact or "나이" in compact:
            updates.setdefault("age_group", AgeGroupPreference.ANY)
        if next_step == DialogStep.ASK_INFRASTRUCTURE or "인프라" in compact:
            updates.setdefault("infrastructure_priorities", [])

        return Conditions(**updates)

    def _extract_locally(self, raw_message: str) -> Conditions:
        text = raw_message.strip()
        compact = text.replace(" ", "")
        updates: dict = {}

        deal_type = self._extract_deal_type(compact)
        if deal_type is not None:
            updates["deal_type"] = deal_type

        monthly_rent = self._extract_monthly_rent(compact)
        if monthly_rent is not None:
            updates["deal_type"] = DealType.MONTHLY_RENT
            updates["monthly_rent_max"] = monthly_rent

        budget = self._extract_budget(compact)
        if budget is not None:
            updates["budget_max"] = budget

        workplace = self._extract_workplace(compact)
        if workplace:
            updates["workplace"] = workplace

        preferred_region = self._extract_preferred_region(text)
        if preferred_region:
            updates["preferred_region"] = preferred_region

        age_group = self._extract_age_group(compact)
        if age_group is not None:
            updates["age_group"] = age_group

        infrastructure = self._extract_infrastructure(compact)
        if infrastructure is not None:
            updates["infrastructure_priorities"] = infrastructure

        return Conditions(**updates)

    def _extract_deal_type(self, compact: str) -> DealType | None:
        hits: list[tuple[int, DealType]] = []
        for keyword, deal_type in (
            ("전세", DealType.JEONSE),
            ("월세", DealType.MONTHLY_RENT),
            ("매매", DealType.SALE),
            ("구매", DealType.SALE),
        ):
            idx = compact.rfind(keyword)
            if idx >= 0:
                hits.append((idx, deal_type))
        return max(hits)[1] if hits else None

    def _extract_budget(self, compact: str) -> int | None:
        labeled = re.search(r"(?:예산|자본금|보증금|매매가|돈)(?:은|는|이|가)?(.{0,12})", compact)
        if labeled:
            value = self._parse_money(labeled.group(1), default_unit="만원")
            if value is not None:
                return value

        monthly_span = self._monthly_rent_span(compact)
        for match in re.finditer(r"\d+(?:\.\d+)?(?:억|천만|만원|만)?", compact):
            if monthly_span and monthly_span[0] <= match.start() < monthly_span[1]:
                continue
            value = self._parse_money(match.group(0), default_unit=None)
            if value is not None and value >= 10_000_000:
                return value
        return None

    def _extract_monthly_rent(self, compact: str) -> int | None:
        span = self._monthly_rent_span(compact)
        if not span:
            return None
        value = self._parse_money(compact[span[0] : span[1]], default_unit="만원")
        if value is not None and value <= 10_000_000:
            return value
        return None

    def _monthly_rent_span(self, compact: str) -> tuple[int, int] | None:
        match = re.search(r"월세(?:는|가|은)?(\d+(?:\.\d+)?(?:만원|만|억)?)", compact)
        if not match:
            return None
        return match.start(1), match.end(1)

    def _parse_money(self, text: str, default_unit: str | None) -> int | None:
        match = re.search(r"(\d+(?:\.\d+)?)(억|천만|만원|만)?", text)
        if not match:
            return None
        amount = float(match.group(1))
        unit = match.group(2) or default_unit
        if unit == "억":
            return int(amount * 100_000_000)
        if unit == "천만":
            return int(amount * 10_000_000)
        if unit in {"만원", "만"}:
            return int(amount * 10_000)
        return None

    def _extract_workplace(self, compact: str) -> str | None:
        if not any(word in compact for word in ("출근", "출퇴근", "회사", "직장", "근무", "일해")):
            return None
        for keyword in _WORKPLACE_TO_COMMUTE:
            if keyword in compact:
                return keyword
        return None

    def _extract_preferred_region(self, text: str) -> str | None:
        if _NO_PREFERENCE_RE.search(text) and "지역" in text.replace(" ", ""):
            return "상관없음"

        if not any(word in text for word in ("희망", "선호", "살고", "거주", "지역", "동네")):
            return None
        match = _SEOUL_REGION_RE.search(text)
        return match.group(1) if match else None

    def _extract_age_group(self, compact: str) -> AgeGroupPreference | None:
        if ("연령" in compact or "나이" in compact) and _NO_PREFERENCE_RE.search(compact):
            return AgeGroupPreference.ANY
        if any(word in compact for word in ("20대", "30대", "2030", "청년", "젊은")):
            return AgeGroupPreference.YOUNG_ADULT
        if any(word in compact for word in ("아이", "자녀", "가족", "육아", "신혼")):
            return AgeGroupPreference.FAMILY
        if any(word in compact for word in ("고령", "노년", "어르신", "시니어")):
            return AgeGroupPreference.SENIOR
        return None

    def _extract_infrastructure(self, compact: str) -> list[InfrastructurePriority] | None:
        priorities: list[InfrastructurePriority] = []
        if any(word in compact for word in ("학교", "초등", "중학교", "고등학교", "학군")):
            priorities.append(InfrastructurePriority.SCHOOL)
        if any(word in compact for word in ("병원", "의료", "약국")):
            priorities.append(InfrastructurePriority.MEDICAL)
        if any(
            word in compact
            for word in ("체육관", "운동시설", "헬스", "헬스장", "필라테스", "수영장")
        ):
            priorities.append(InfrastructurePriority.FITNESS)
        if any(word in compact for word in ("교통", "역세권", "지하철", "버스")):
            priorities.append(InfrastructurePriority.TRANSIT)
        if any(word in compact for word in ("조용", "유흥적", "술집적")):
            priorities.append(InfrastructurePriority.QUIET)
        if any(word in compact for word in ("유흥", "술집", "놀거리")) and not any(
            word in compact for word in ("적은", "적고", "적게", "없")
        ):
            priorities.append(InfrastructurePriority.NIGHTLIFE)

        if priorities:
            return list(dict.fromkeys(priorities))
        if ("인프라" in compact or "시설" in compact) and _NO_PREFERENCE_RE.search(compact):
            return []
        return None

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
