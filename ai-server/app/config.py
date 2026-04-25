from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    backend_url: str = "http://backend:8080"
    backend_mode: str = Field(default="mock", alias="AI_BACKEND_MODE")
    ai_provider: str = Field(default="dummy", alias="AI_PROVIDER")
    dummy_fail: bool = Field(default=False, alias="AI_DUMMY_FAIL")
    timeout_ms: int = Field(default=5000, alias="AI_TIMEOUT_MS")
    llm_base_url: str = Field(default="http://llm-runtime:8000/v1", alias="OPENAI_BASE_URL")
    llm_api_key: str = Field(default="EMPTY", alias="OPENAI_API_KEY")
    llm_model: str = Field(default="Qwen/Qwen3.5-2B", alias="OPENAI_MODEL")
    llm_timeout_ms: int = Field(default=15000, alias="LLM_TIMEOUT_MS")
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

    @property
    def use_llm_provider(self) -> bool:
        return self.ai_provider in {"qwen", "openai_compatible"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
