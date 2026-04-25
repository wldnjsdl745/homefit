import httpx

from app.config import Settings
from app.schemas import ChatRequest, ChatResponse
from app.services.backend_client import BackendClient
from app.services.dialog_policy import DialogPolicy, DialogStep
from app.services.message_builder import MessageBuilder


class ChatService:
    def __init__(
        self,
        backend_client: BackendClient,
        settings: Settings,
        dialog_policy: DialogPolicy | None = None,
        message_builder: MessageBuilder | None = None,
    ):
        self.backend_client = backend_client
        self.settings = settings
        self.dialog_policy = dialog_policy or DialogPolicy()
        self.message_builder = message_builder or MessageBuilder()

    async def handle(self, request: ChatRequest) -> ChatResponse:
        if self.settings.dummy_fail:
            return self._fallback(request.session_id)

        try:
            upserted = await self.backend_client.upsert_conditions(
                session_id=request.session_id,
                raw=request.raw,
                conditions=request.raw,
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
