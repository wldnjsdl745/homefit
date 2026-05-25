import pytest

from app.config import Settings
from app.schemas import ChatRequest, Conditions
from app.services.backend_client import (
    BackendClient,
    FilterRegionsResponse,
    UpsertConditionsResponse,
)
from app.services.chat_service import ChatService


class FailingBackendClient(BackendClient):
    async def upsert_conditions(
        self,
        session_id: str | None,
        raw: Conditions,
        conditions: Conditions,
    ) -> UpsertConditionsResponse:
        raise ValueError("backend failed")

    async def filter_regions(self, conditions: Conditions) -> FilterRegionsResponse:
        raise ValueError("backend failed")


class StaticLlmProvider:
    async def extract_conditions(self, raw_message: str) -> Conditions:
        return Conditions(budget_max=200_000_000, deal_type="jeonse")


@pytest.mark.asyncio
async def test_chat_service_returns_fallback_when_backend_fails() -> None:
    service = ChatService(
        backend_client=FailingBackendClient(),
        settings=Settings(AI_BACKEND_MODE="mock"),
    )

    response = await service.handle(ChatRequest(session_id=None, raw=Conditions()))

    assert response.state == "asking"
    assert response.bot_messages[0].content == "죄송해요, 다시 시도해주세요."


@pytest.mark.asyncio
async def test_chat_service_returns_fallback_when_dummy_fail_enabled() -> None:
    service = ChatService(
        backend_client=FailingBackendClient(),
        settings=Settings(AI_BACKEND_MODE="mock", AI_DUMMY_FAIL=True),
    )

    response = await service.handle(ChatRequest(session_id=None, raw=Conditions()))

    assert response.state == "asking"
    assert "AI-SYS-001" in response.bot_messages[0].content


@pytest.mark.asyncio
async def test_chat_service_uses_llm_provider_once_at_dialog_complete() -> None:
    """단일 LLM 호출 정책: 턴별 추출 없이 누적 → 완료 시 1회 추출.

    turn 1 (자본금 텍스트): LLM 미호출, 거래 유형 질문.
    turn 2 (거래 유형 텍스트): 희망 지역 질문.
    turn 3-5: 통근지/연령층/인프라 질문.
    turn 6: 완료 → LLM 1회 → mock filter → 결과.
    """
    from app.services.backend_client import MockBackendClient

    service = ChatService(
        backend_client=MockBackendClient(),
        settings=Settings(AI_BACKEND_MODE="mock"),
        llm_provider=StaticLlmProvider(),
    )

    turn1 = await service.handle(
        ChatRequest(session_id=None, raw=Conditions(), raw_message="2억 정도 있어요")
    )
    assert turn1.state == "asking"
    assert (
        turn1.bot_messages[0].content
        == "서울 실거래 데이터 기준으로 전세, 월세, 매매 중 어떤 거래를 볼까요?"
    )

    turn2 = await service.handle(
        ChatRequest(
            session_id=turn1.session_id,
            raw=Conditions(),
            raw_message="전세로 가자",
        )
    )
    assert turn2.state == "asking"
    assert "희망하는 지역" in turn2.bot_messages[0].content

    turn3 = await service.handle(
        ChatRequest(
            session_id=turn2.session_id,
            raw=Conditions(),
            raw_message="상관없어요",
        )
    )
    assert turn3.state == "asking"
    assert "직장이나 자주 가는 곳" in turn3.bot_messages[0].content

    turn4 = await service.handle(
        ChatRequest(
            session_id=turn3.session_id,
            raw=Conditions(),
            raw_message="상관없어요",
        )
    )
    assert turn4.state == "asking"
    assert "연령층" in turn4.bot_messages[0].content

    turn5 = await service.handle(
        ChatRequest(
            session_id=turn4.session_id,
            raw=Conditions(age_group="any"),
        )
    )
    assert turn5.state == "asking"
    assert "주변 인프라" in turn5.bot_messages[0].content

    turn6 = await service.handle(
        ChatRequest(
            session_id=turn5.session_id,
            raw=Conditions(infrastructure_priorities=[]),
        )
    )
    assert turn6.state == "result"
    assert turn6.bot_messages[0].type == "bot.text"
    assert "전세" in turn6.bot_messages[0].content
    assert "이하" in turn6.bot_messages[0].content
