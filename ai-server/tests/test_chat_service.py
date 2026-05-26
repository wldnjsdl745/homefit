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


class ScenarioLlmProvider:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def extract_conditions(self, raw_message: str) -> Conditions:
        self.calls.append(raw_message)
        if "매매" in raw_message:
            return Conditions(budget_max=500_000_000, deal_type="sale")
        return Conditions(
            budget_max=200_000_000,
            deal_type="jeonse",
            preferred_region="마포구",
            workplace="논현",
            age_group="young_adult",
            infrastructure_priorities=["medical", "fitness"],
        )


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
async def test_chat_service_returns_result_when_text_contains_all_conditions() -> None:
    """한 문장에 필요한 조건이 모두 들어오면 중간 질문 없이 결과로 간다."""
    from app.services.backend_client import MockBackendClient

    llm = ScenarioLlmProvider()
    service = ChatService(
        backend_client=MockBackendClient(),
        settings=Settings(AI_BACKEND_MODE="mock"),
        llm_provider=llm,
    )

    response = await service.handle(
        ChatRequest(
            session_id=None,
            raw=Conditions(),
            raw_message="2억 전세, 마포구 희망, 논현 출근, 20대 많고 병원 체육관 중요",
        )
    )

    assert response.state == "result"
    assert len(llm.calls) == 1
    assert "전세" in response.bot_messages[0].content
    assert "강남" in response.bot_messages[0].content


@pytest.mark.asyncio
async def test_chat_service_can_change_conditions_after_result() -> None:
    """결과 이후 같은 세션에서 조건을 바꾸면 기존 조건 위에 덮어쓴다."""
    from app.services.backend_client import MockBackendClient

    llm = ScenarioLlmProvider()
    service = ChatService(
        backend_client=MockBackendClient(),
        settings=Settings(AI_BACKEND_MODE="mock"),
        llm_provider=llm,
    )

    first = await service.handle(
        ChatRequest(
            session_id=None,
            raw=Conditions(),
            raw_message="2억 전세, 마포구 희망, 논현 출근, 연령 상관없고 인프라 상관없음",
        )
    )
    assert first.state == "result"

    changed = await service.handle(
        ChatRequest(
            session_id=first.session_id,
            raw=Conditions(),
            raw_message="매매 5억으로 바꿔줘",
        )
    )

    assert changed.state == "result"
    assert changed.bot_messages[0].type == "bot.text"
    assert "매매" in changed.bot_messages[0].content
    assert "5억" in changed.bot_messages[0].content
