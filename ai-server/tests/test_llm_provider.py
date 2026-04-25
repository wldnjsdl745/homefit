import httpx
import pytest

from app.config import Settings
from app.schemas import Conditions
from app.services.llm_provider import LlmProvider, SafeLlmProvider


class WorkingProvider(LlmProvider):
    async def extract_conditions(self, raw_message: str) -> Conditions:
        return Conditions(budget_max=200_000_000, deal_type="jeonse")


class FailingProvider(LlmProvider):
    async def extract_conditions(self, raw_message: str) -> Conditions:
        raise httpx.ConnectError("llm runtime is down")


@pytest.mark.asyncio
async def test_safe_llm_provider_returns_extracted_conditions() -> None:
    provider = SafeLlmProvider(WorkingProvider())

    result = await provider.extract_conditions("전세 2억")

    assert result == Conditions(budget_max=200_000_000, deal_type="jeonse")


@pytest.mark.asyncio
async def test_safe_llm_provider_falls_back_when_runtime_fails() -> None:
    provider = SafeLlmProvider(FailingProvider())

    result = await provider.extract_conditions("전세 2억")

    assert result == Conditions()


def test_settings_enable_qwen_provider() -> None:
    settings = Settings(AI_PROVIDER="qwen")

    assert settings.use_llm_provider is True
