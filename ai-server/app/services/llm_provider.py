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
        # Qwen3.x 시리즈는 thinking 모드가 기본값. 우리는 의미 추출만 필요하므로
        # `/no_think` 디렉티브를 user 메시지 끝에 추가해 reasoning을 끈다.
        # (Qwen3 공식 가이드: per-message로 thinking을 비활성화하는 표준 방법)
        user_content = f"{raw_message}\n/no_think"

        payload = {
            "model": self.settings.llm_model,
            "messages": [
                {"role": "system", "content": self._system_prompt()},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0,
            "top_p": 1,
            # /no_think로 reasoning을 껐어도 안전 마진으로 넉넉히 둔다.
            "max_tokens": 256,
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
            "당신은 Homefit의 의미 추출기입니다. "
            "한국어 사용자 메시지에서 주거 검색 조건만 JSON으로 추출하세요. "
            "지역 추천, 순위, 설명은 절대 하지 않습니다. "
            "JSON은 다음 선택 키만 포함합니다: budget_max, deal_type. "
            "  - budget_max: 정수, 단위는 원 (예: '2억' → 200000000, '5천만원' → 50000000) "
            "  - deal_type: 'jeonse' (전세) 또는 'monthly_rent' (월세) 둘 중 하나 "
            "사용자가 명시적으로 언급하지 않은 키는 절대 포함하지 마세요. "
            "추측하거나 추정하지 마세요. 명시되지 않으면 해당 키를 생략합니다. "
            "preference_text는 추출하지 마세요. 클라이언트가 별도로 전달합니다. "
            "다른 텍스트 없이 JSON만 반환하세요. 예: {\"budget_max\": 200000000}"
        )


class SafeLlmProvider(LlmProvider):
    def __init__(self, provider: LlmProvider):
        self.provider = provider

    async def extract_conditions(self, raw_message: str) -> Conditions:
        try:
            return await self.provider.extract_conditions(raw_message)
        except (httpx.HTTPError, json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError):
            return Conditions()
