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


@pytest.mark.asyncio
async def test_chat_service_returns_fallback_when_backend_fails() -> None:
    service = ChatService(
        backend_client=FailingBackendClient(),
        settings=Settings(AI_BACKEND_MODE="mock"),
    )

    response = await service.handle(ChatRequest(session_id=None, raw=Conditions()))

    assert response.state == "asking"
    assert response.bot_messages[0].content == "잠시 문제가 있어요. 다시 입력해주세요."


@pytest.mark.asyncio
async def test_chat_service_returns_fallback_when_dummy_fail_enabled() -> None:
    service = ChatService(
        backend_client=FailingBackendClient(),
        settings=Settings(AI_BACKEND_MODE="mock", AI_DUMMY_FAIL=True),
    )

    response = await service.handle(ChatRequest(session_id=None, raw=Conditions()))

    assert response.state == "asking"
    assert response.bot_messages[0].content == "잠시 문제가 있어요. 다시 입력해주세요."
