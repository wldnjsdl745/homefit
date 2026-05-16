from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    backend_url: str = "http://backend:8080"
    backend_mode: str = Field(default="mock", alias="AI_BACKEND_MODE")
    ai_provider: str = Field(default="dummy", alias="AI_PROVIDER")
    dummy_fail: bool = Field(default=False, alias="AI_DUMMY_FAIL")
    timeout_ms: int = Field(default=5000, alias="AI_TIMEOUT_MS")
    llm_base_url: str = Field(default="http://llm-runtime:11434/v1", alias="OPENAI_BASE_URL")
    llm_api_key: str = Field(default="EMPTY", alias="OPENAI_API_KEY")
    llm_model: str = Field(default="qwen3.5:4b", alias="OPENAI_MODEL")
    llm_timeout_ms: int = Field(default=120000, alias="LLM_TIMEOUT_MS")
    llm_prompt_style: str = Field(default="hermes", alias="LLM_PROMPT_STYLE")
    port: int = Field(default=8000, alias="AI_PORT")
    cors_allow_origins: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]

    @property
    def use_mock_backend(self) -> bool:
        return self.backend_mode == "mock"

    # 지원하는 LLM Provider 값:
    #   - "qwen" / "openai_compatible" → OpenAICompatibleLlmProvider (/v1/chat/completions)
    #   - "qwen_native" / "ollama_native" → OllamaNativeLlmProvider (/api/chat, think:false)
    _LLM_PROVIDER_VALUES = frozenset({
        "qwen",
        "openai_compatible",
        "qwen_native",
        "ollama_native",
    })

    @property
    def use_llm_provider(self) -> bool:
        return self.ai_provider in self._LLM_PROVIDER_VALUES

    @property
    def use_ollama_native(self) -> bool:
        """`/api/chat` (Ollama native) 사용 여부.

        True면 `think: false` 옵션으로 Qwen3 thinking을 확실히 끄고,
        `format: "json"`으로 출력 형식을 강제할 수 있다.
        """
        return self.ai_provider in {"qwen_native", "ollama_native"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
