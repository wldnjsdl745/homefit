from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.schemas import BotTextMessage, ChatRequest, ChatResponse, ErrorResponse, HealthResponse
from app.services.backend_client import HttpBackendClient, MockBackendClient
from app.services.chat_service import ChatService
from app.services.llm_provider import (
    LlmProvider,
    OllamaNativeLlmProvider,
    OpenAICompatibleLlmProvider,
    SafeLlmProvider,
)


def _create_llm_provider(settings) -> LlmProvider | None:
    """AI_PROVIDER 환경변수에 따라 적절한 Provider 인스턴스 생성.

    분기:
      - `ollama_native` / `qwen_native` → OllamaNativeLlmProvider (think: false)
      - `qwen` / `openai_compatible`    → OpenAICompatibleLlmProvider
      - 그 외 (`dummy` 포함)            → None (LLM 미사용)
    """
    if not settings.use_llm_provider:
        return None
    if settings.use_ollama_native:
        return SafeLlmProvider(OllamaNativeLlmProvider(settings))
    return SafeLlmProvider(OpenAICompatibleLlmProvider(settings))


def create_chat_service() -> ChatService:
    settings = get_settings()
    backend_client = (
        MockBackendClient()
        if settings.use_mock_backend
        else HttpBackendClient(
            base_url=settings.backend_url,
            timeout_ms=settings.timeout_ms,
            filter_timeout_ms=settings.backend_filter_timeout_ms,
        )
    )
    llm_provider = _create_llm_provider(settings)
    return ChatService(
        backend_client=backend_client,
        settings=settings,
        llm_provider=llm_provider,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.chat_service = create_chat_service()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Homefit AI Server", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/healthz", response_model=HealthResponse)
    async def healthz() -> HealthResponse:
        return HealthResponse()

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        error = ErrorResponse(
            code="AI-REQ-001",
            message="입력값을 이해하지 못했어요. 다시 알려주세요.",
            detail=str(exc.errors()),
        )
        response = ChatResponse(
            session_id="invalid",
            state="asking",
            bot_messages=[
                BotTextMessage(type="bot.text", content=f"{error.message} ({error.code})"),
            ],
            error=error,
        )
        return JSONResponse(status_code=200, content=response.model_dump(mode="json"))

    @app.post("/chat", response_model=ChatResponse)
    async def chat(request: ChatRequest) -> ChatResponse:
        return await app.state.chat_service.handle(request)

    return app


app = create_app()
