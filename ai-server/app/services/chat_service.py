import httpx

from app.config import Settings
from app.schemas import ChatRequest, ChatResponse, Conditions
from app.services.backend_client import BackendClient
from app.services.dialog_policy import DialogPolicy, DialogStep
from app.services.llm_provider import DummyLlmProvider, LlmProvider
from app.services.merge_service import MergeService
from app.services.message_builder import MessageBuilder


class ChatService:
    def __init__(
        self,
        backend_client: BackendClient,
        settings: Settings,
        dialog_policy: DialogPolicy | None = None,
        message_builder: MessageBuilder | None = None,
        llm_provider: LlmProvider | None = None,
        merge_service: MergeService | None = None,
    ):
        self.backend_client = backend_client
        self.settings = settings
        self.dialog_policy = dialog_policy or DialogPolicy()
        self.message_builder = message_builder or MessageBuilder()
        self.llm_provider = llm_provider or DummyLlmProvider()
        self.merge_service = merge_service or MergeService()

    async def handle(self, request: ChatRequest) -> ChatResponse:
        if self.settings.dummy_fail:
            return self._fallback(request.session_id)

        try:
            raw = request.raw
            if request.raw_message:
                extracted = await self.llm_provider.extract_conditions(request.raw_message)
                raw = self.merge_service.merge(raw, extracted)
                if self._is_empty(raw):
                    return ChatResponse(
                        session_id=request.session_id or "unsupported",
                        state="asking",
                        bot_messages=self.message_builder.unsupported_conditions(),
                    )

            upserted = await self.backend_client.upsert_conditions(
                session_id=request.session_id,
                raw=raw,
                conditions=raw,
            )

            step = self.dialog_policy.next_step(upserted.conditions)

            if step == DialogStep.ASK_BUDGET:
                return ChatResponse(
                    session_id=upserted.session_id,
                    state="asking",
                    bot_messages=self.message_builder.ask_budget(),
                )

            if step == DialogStep.ASK_DEAL_TYPE:
                return ChatResponse(
                    session_id=upserted.session_id,
                    state="asking",
                    bot_messages=self.message_builder.ask_deal_type(),
                )

            if step == DialogStep.ASK_PREFERENCE:
                return ChatResponse(
                    session_id=upserted.session_id,
                    state="asking",
                    bot_messages=self.message_builder.ask_preference(),
                )

            regions = await self.backend_client.filter_regions(upserted.conditions)
            return ChatResponse(
                session_id=upserted.session_id,
                state="result",
                bot_messages=self.message_builder.result(upserted.conditions, regions.regions),
            )
        except (httpx.HTTPError, ValueError):
            return self._fallback(request.session_id)

    def _fallback(self, session_id: str | None) -> ChatResponse:
        return ChatResponse(
            session_id=session_id or "fallback",
            state="asking",
            bot_messages=self.message_builder.fallback(),
        )

    def _is_empty(self, conditions: Conditions) -> bool:
        return not conditions.model_dump(exclude_none=True)
