from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    backend_url: str = "http://backend:8080"
    backend_mode: str = Field(default="mock", alias="AI_BACKEND_MODE")
    dummy_fail: bool = Field(default=False, alias="AI_DUMMY_FAIL")
    timeout_ms: int = Field(default=5000, alias="AI_TIMEOUT_MS")
    port: int = Field(default=8000, alias="AI_PORT")
    cors_allow_origins: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allow_origins.split(",") if origin.strip()]

    @property
    def use_mock_backend(self) -> bool:
        return self.backend_mode == "mock"


@lru_cache
def get_settings() -> Settings:
    return Settings()
