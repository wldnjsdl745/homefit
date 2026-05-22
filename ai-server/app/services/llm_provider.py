"""LLM Provider 구현 모음.

Provider 종류:
  - `DummyLlmProvider`: LLM 호출 없이 빈 Conditions 반환 (개발/테스트).
  - `OpenAICompatibleLlmProvider`: OpenAI 호환 `/v1/chat/completions` 사용.
      장점: Claude/OpenAI 등 다른 OpenAI-호환 LLM과 그대로 교체 가능.
      단점: Ollama 고유 옵션(`think: false` 등) 미지원.
  - `OllamaNativeLlmProvider`: Ollama 고유 `/api/chat` 사용.
      장점: Qwen3 thinking 완전 비활성화(`think: false`), `format: "json"` 강제.
      단점: Ollama 외 다른 LLM 백엔드 사용 시 코드 변경 필요.
  - `SafeLlmProvider`: 위 Provider를 감싸 실패 시 빈 Conditions로 안전 흡수.

선택은 `AI_PROVIDER` 환경변수로:
  - `dummy`              → DummyLlmProvider
  - `qwen`/`openai_compatible` → OpenAICompatibleLlmProvider
  - `qwen_native`/`ollama_native` → OllamaNativeLlmProvider

main.py가 환경변수 값으로 Provider를 생성한다.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod

import httpx

from app.config import Settings
from app.schemas import Conditions

# 공통 system prompt — 두 Provider에서 동일.
#
# 한국어 단위 변환표 (LLM이 헷갈리기 쉬워서 명시적으로 나열):
#   1만 = 10_000           (10⁴)
#   1천만 = 10_000_000     (10⁷)
#   1억 = 100_000_000      (10⁸)
#   1조 = 1_000_000_000_000 (10¹²)
_SYSTEM_PROMPT_KO = (
    "당신은 Homefit의 의미 추출기입니다. "
    "한국어 사용자 메시지에서 주거 검색 조건만 JSON으로 추출하세요. "
    "지역 추천, 순위, 설명은 절대 하지 않습니다.\n"
    "\n"
    "출력 JSON 키:\n"
    "  - budget_max: 정수, 단위는 원(KRW)\n"
    "  - deal_type: 'jeonse'(전세) 또는 'monthly_rent'(월세)\n"
    "\n"
    "한국어 금액 단위 변환 (반드시 정확히 따를 것):\n"
    "  - 1만원 = 10000\n"
    "  - 10만원 = 100000\n"
    "  - 100만원 = 1000000\n"
    "  - 1천만원 = 10000000\n"
    "  - 5천만원 = 50000000\n"
    "  - 1억(원) = 100000000\n"
    "  - 2억(원) = 200000000     ← '2억' 또는 '2억 정도'는 반드시 이 값\n"
    "  - 3억(원) = 300000000\n"
    "  - 5억(원) = 500000000\n"
    "  - 1.5억 = 150000000\n"
    "  - 10억 = 1000000000\n"
    "\n"
    "규칙:\n"
    "1. 사용자가 명시한 키만 JSON에 포함. 명시 안 된 키는 절대 추가하지 말 것 (null도 안 됨).\n"
    "2. '한 2억', '2억 정도', '약 2억' 등 모호한 표현도 위 변환표의 정수 그대로 사용.\n"
    "3. preference_text는 절대 추출하지 말 것 (클라이언트가 별도 전달).\n"
    "4. 다른 텍스트 없이 JSON 객체만 반환. markdown 코드 블록(```)으로 감싸지 말 것.\n"
    "\n"
    '예시:\n'
    '  입력: "2억 정도 있어요"        → {"budget_max": 200000000}\n'
    '  입력: "5천만원"                 → {"budget_max": 50000000}\n'
    '  입력: "전세로 보고 있어"        → {"deal_type": "jeonse"}\n'
    '  입력: "1.5억 전세"              → {"budget_max": 150000000, "deal_type": "jeonse"}\n'
    '  입력: "강남 근처면 좋겠어요"   → {}'
)


def _parse_json_content(content: str) -> dict:
    """LLM 응답 문자열에서 JSON 객체를 안전하게 추출.

    일부 모델(deepseek 등)은 프롬프트로 금지해도 markdown 코드 블록
    (```json ... ```)으로 감싸서 반환한다. 펜스를 제거하고, 그래도 실패하면
    문자열에서 첫 `{` ~ 마지막 `}` 구간을 잘라 파싱한다.
    """
    text = content.strip()

    # ```json ... ``` 또는 ``` ... ``` 펜스 제거
    if text.startswith("```"):
        text = text[3:]
        if text[:4].lower() == "json":
            text = text[4:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # 마지막 방어: 첫 '{' ~ 마지막 '}' 구간만 추출
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise


class LlmProvider(ABC):
    @abstractmethod
    async def extract_conditions(self, raw_message: str) -> Conditions:
        raise NotImplementedError


class DummyLlmProvider(LlmProvider):
    async def extract_conditions(self, raw_message: str) -> Conditions:
        return Conditions()


class OpenAICompatibleLlmProvider(LlmProvider):
    """OpenAI `/v1/chat/completions` 호환 API 사용.

    Anthropic Claude, OpenAI GPT, Ollama, vLLM 등 OpenAI 호환 LLM 어디든 동작.
    Qwen3 thinking 비활성화는 user 메시지에 `/no_think` 디렉티브로 시도 — 단
    모델 버전에 따라 무시될 수 있다(qwen3.5:4b가 그 케이스). 그런 경우
    `OllamaNativeLlmProvider`로 전환하면 `think: false`로 확실하게 끈다.
    """

    def __init__(self, settings: Settings):
        self.settings = settings

    async def extract_conditions(self, raw_message: str) -> Conditions:
        # Qwen3 표준 `/no_think` 디렉티브 (작동 보장 X — 모델별 편차).
        user_content = f"{raw_message}\n/no_think"

        payload = {
            "model": self.settings.llm_model,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT_KO},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0,
            "top_p": 1,
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

        content = data["choices"][0]["message"]["content"]
        parsed = _parse_json_content(content)
        return Conditions.model_validate(parsed)


class OllamaNativeLlmProvider(LlmProvider):
    """Ollama 고유 `/api/chat` 엔드포인트 사용.

    OpenAI 호환 API에 없는 Ollama 전용 기능을 활용:
      - `think: false`: Qwen3 thinking 모드 완전 비활성화
      - `format: "json"`: JSON 출력 강제 (스키마 위반 응답 차단)
      - `options.num_predict`: 응답 토큰 한도

    `llm_base_url`이 `/v1`로 끝나면 자동 제거하여 native 엔드포인트로 호출.
    """

    def __init__(self, settings: Settings):
        self.settings = settings

    @property
    def _native_base(self) -> str:
        url = self.settings.llm_base_url.rstrip("/")
        if url.endswith("/v1"):
            url = url[: -len("/v1")]
        return url

    async def extract_conditions(self, raw_message: str) -> Conditions:
        payload = {
            "model": self.settings.llm_model,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT_KO},
                {"role": "user", "content": raw_message},
            ],
            # Qwen3 thinking 완전 비활성화 (Ollama 0.5+).
            "think": False,
            "stream": False,
            # JSON 출력 강제. 모델이 잘못된 형식 출력 못 함.
            "format": "json",
            "options": {
                "temperature": 0,
                "top_p": 1,
                "num_predict": 256,
            },
        }

        async with httpx.AsyncClient(timeout=self.settings.llm_timeout_ms / 1000) as client:
            response = await client.post(f"{self._native_base}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()

        content = data["message"]["content"]
        parsed = _parse_json_content(content)
        return Conditions.model_validate(parsed)


class SafeLlmProvider(LlmProvider):
    def __init__(self, provider: LlmProvider):
        self.provider = provider

    async def extract_conditions(self, raw_message: str) -> Conditions:
        try:
            return await self.provider.extract_conditions(raw_message)
        except (httpx.HTTPError, json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError):
            return Conditions()
