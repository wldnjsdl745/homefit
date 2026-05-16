"""pytest 공통 설정.

단위/API 테스트는 **결정론적**이어야 하므로 외부 의존(실제 BE, 실제 LLM)을
강제로 끈다:
  - AI_BACKEND_MODE=mock  → MockBackendClient (하드코딩 regions)
  - AI_PROVIDER=dummy      → LLM 미호출
  - AI_DUMMY_FAIL=false

docker compose run 시 ai-server 서비스 env(AI_BACKEND_MODE=http 등)가
주입되는데, 그대로 두면 API 테스트가 실제 backend/LLM에 붙어
시드 데이터에 따라 결과가 달라진다. autouse fixture로 차단한다.

통합 테스트(`-m integration`, test_qwen_extraction)는 자체적으로
`Settings(ai_provider="qwen")`를 직접 구성하므로 영향 없다.
"""

from __future__ import annotations

import pytest

from app.config import get_settings


@pytest.fixture(autouse=True)
def _force_test_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AI_BACKEND_MODE", "mock")
    monkeypatch.setenv("AI_PROVIDER", "dummy")
    monkeypatch.setenv("AI_DUMMY_FAIL", "false")
    # get_settings 는 lru_cache. env 변경 반영을 위해 캐시 초기화.
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
