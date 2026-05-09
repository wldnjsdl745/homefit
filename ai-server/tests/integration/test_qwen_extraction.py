"""Qwen LLM 통합 테스트.

이 테스트는 **실제로 동작 중인 Ollama 런타임**(`OPENAI_BASE_URL`)이 필요하다.

실행:
  - `make qwen-test`               # docker-compose 안에서 실행
  - `pytest -m integration`        # 로컬 venv (Ollama 직접 띄운 경우)

기본 `pytest` 실행에서는 자동 제외된다 (pyproject.toml addopts).

각 케이스가 LLM 호출을 수행하므로 Mac CPU 추론 기준 케이스당 ~25-30초 소요.

테스트 케이스 카탈로그(`EXTRACTION_CASES`)는 본 파일이 단일 진실이다.
새 시나리오 추가 시 dict 한 줄만 추가하면 자동으로 parametrize 된다.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx
import pytest

from app.config import Settings
from app.schemas import Conditions, DealType
from app.services.llm_provider import OpenAICompatibleLlmProvider

pytestmark = pytest.mark.integration


# ─── 테스트 케이스 카탈로그 ────────────────────────────────


@dataclass(frozen=True)
class ExtractionCase:
    """단일 추출 케이스 정의.

    - `expected`: LLM이 추출하기를 기대하는 Conditions.
    - `strict`: True면 추출 결과가 expected와 정확히 일치해야 함.
                False면 hallucination 허용 (관찰용).
    """

    name: str
    raw_message: str
    expected: Conditions
    strict: bool = True


EXTRACTION_CASES: tuple[ExtractionCase, ...] = (
    # ── 단일 키 추출 ───────────────────────────────
    ExtractionCase(
        name="budget_only_2eok",
        raw_message="2억 정도 있어요",
        expected=Conditions(budget_max=200_000_000),
    ),
    ExtractionCase(
        name="budget_only_5cheonman",
        raw_message="5천만원 있어요",
        expected=Conditions(budget_max=50_000_000),
    ),
    ExtractionCase(
        name="deal_type_jeonse",
        raw_message="전세로 보고 있어요",
        expected=Conditions(deal_type=DealType.JEONSE),
    ),
    ExtractionCase(
        name="deal_type_monthly_rent",
        raw_message="월세 살래요",
        expected=Conditions(deal_type=DealType.MONTHLY_RENT),
    ),
    # ── 복합 추출 ──────────────────────────────────
    ExtractionCase(
        name="budget_and_deal_type",
        raw_message="1.5억 전세",
        expected=Conditions(budget_max=150_000_000, deal_type=DealType.JEONSE),
    ),
    # ── 추출 거부 (관찰용, strict=False) ─────────────
    ExtractionCase(
        name="unsupported_preference_only",
        raw_message="강남 근처면 좋겠어요",
        expected=Conditions(),
        strict=False,
    ),
    ExtractionCase(
        name="irrelevant_input",
        raw_message="오늘 날씨 어때?",
        expected=Conditions(),
        strict=False,
    ),
)


# ─── Fixture / 헬퍼 ────────────────────────────────────────


def _is_runtime_reachable(base_url: str) -> bool:
    """Ollama가 살아있는지 빠르게 확인. 살아있으면 True."""
    root = base_url.rstrip("/").rsplit("/v1", 1)[0]
    try:
        with httpx.Client(timeout=3.0) as client:
            response = client.get(f"{root}/api/tags")
        return response.status_code == 200
    except httpx.HTTPError:
        return False


@pytest.fixture(scope="module")
def settings() -> Settings:
    return Settings(ai_provider="qwen")


@pytest.fixture(scope="module")
def llm_provider(settings: Settings) -> OpenAICompatibleLlmProvider:
    if not _is_runtime_reachable(settings.llm_base_url):
        pytest.skip(
            f"Ollama runtime not reachable at {settings.llm_base_url}. "
            "Bring up the stack with `make up` first."
        )
    return OpenAICompatibleLlmProvider(settings)


# ─── 추출 테스트 (parametrize) ─────────────────────────────


@pytest.mark.parametrize(
    "case",
    EXTRACTION_CASES,
    ids=lambda c: c.name,
)
@pytest.mark.asyncio
async def test_extract(case: ExtractionCase, llm_provider: OpenAICompatibleLlmProvider):
    result = await llm_provider.extract_conditions(case.raw_message)

    actual_dump = result.model_dump(exclude_none=True)
    expected_dump = case.expected.model_dump(exclude_none=True)

    if case.strict:
        assert actual_dump == expected_dump, (
            f"[{case.name}] '{case.raw_message}'\n"
            f"  expected={expected_dump}\n"
            f"  actual={actual_dump}"
        )
    else:
        # 관찰용: 결과를 출력만 한다 (실패 처리 안 함).
        print(
            f"\n[observe:{case.name}] '{case.raw_message}'\n"
            f"  expected_empty_or={expected_dump}\n"
            f"  actual={actual_dump}"
        )
        # 최소 보장: 알 수 없는 키 없음(Pydantic이 차단함).
        assert isinstance(result, Conditions)


# ─── 환경 정보 (디버깅용) ─────────────────────────────────


def test_print_runtime_info(settings: Settings):
    """실제 어디로 호출되는지 로그로 확인용. 항상 통과."""
    assert settings.llm_base_url
    print(
        f"\n[qwen-test] base_url={settings.llm_base_url} "
        f"model={settings.llm_model} "
        f"timeout={settings.llm_timeout_ms}ms "
        f"provider=qwen"
    )
