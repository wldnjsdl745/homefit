import json
from abc import ABC, abstractmethod

import httpx

from app.config import Settings
from app.schemas import Conditions


class LlmProvider(ABC):
    @abstractmethod
    async def extract_conditions(self, raw_message: str) -> Conditions:
        raise NotImplementedError


class DummyLlmProvider(LlmProvider):
    async def extract_conditions(self, raw_message: str) -> Conditions:
        return Conditions()


class OpenAICompatibleLlmProvider(LlmProvider):
    def __init__(self, settings: Settings):
        self.settings = settings

    async def extract_conditions(self, raw_message: str) -> Conditions:
        payload = {
            "model": self.settings.llm_model,
            "messages": [
                {"role": "system", "content": self._system_prompt()},
                {"role": "user", "content": raw_message},
            ],
            "temperature": 0,
            "top_p": 1,
            "max_tokens": 120,
        }

        async with httpx.AsyncClient(timeout=self.settings.llm_timeout_ms / 1000) as client:
            response = await client.post(
                f"{self.settings.llm_base_url.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.settings.llm_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        content = data["choices"][0]["message"]["content"].strip()
        parsed = json.loads(content)
        return Conditions.model_validate(parsed)

    def _system_prompt(self) -> str:
        return (
            "You are Homefit's semantic extraction module. "
            "Extract only structured housing search conditions from the Korean user message. "
            "Do not recommend regions. Do not rank anything. Do not explain. "
            "Return JSON only with optional keys: budget_max, deal_type. "
            "budget_max must be an integer in KRW. "
            "deal_type must be one of: jeonse, monthly_rent. "
            "Do not extract preference_text. Preferences are passed separately by the client. "
            "If a value is missing, omit the key."
        )


class SafeLlmProvider(LlmProvider):
    def __init__(self, provider: LlmProvider):
        self.provider = provider

    async def extract_conditions(self, raw_message: str) -> Conditions:
        try:
            return await self.provider.extract_conditions(raw_message)
        except (httpx.HTTPError, json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError):
            return Conditions()
