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


@pytest.mark.asyncio
async def test_chat_service_uses_llm_provider_once_at_dialog_complete() -> None:
    """단일 LLM 호출 정책: 턴별 추출 없이 누적 → 완료 시 1회 추출.

    turn 1 (자본금 텍스트): LLM 미호출, 거래 유형 질문.
    turn 2 (거래 유형 텍스트): 완료 → LLM 1회 → mock filter → 결과.
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
    assert turn1.bot_messages[-1].content == "전세/월세 중 어떤 걸 원하시는지 알려주세요."

    turn2 = await service.handle(
        ChatRequest(
            session_id=turn1.session_id,
            raw=Conditions(),
            raw_message="전세로 가자",
        )
    )
    assert turn2.state == "result"
    assert (
        turn2.bot_messages[-1].content
        == "전세 2억 예산에 맞는 지역은 분당·성남·경기도입니다."
    )
