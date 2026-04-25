from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class DealType(StrEnum):
    JEONSE = "jeonse"
    MONTHLY_RENT = "monthly_rent"


class Conditions(BaseModel):
    budget_max: Annotated[int | None, Field(gt=0, le=10_000_000_000)] = None
    deal_type: DealType | None = None


class ChatRequest(BaseModel):
    session_id: str | None = None
    raw: Conditions = Field(default_factory=Conditions)


class QuickReplyChip(BaseModel):
    id: str
    label: str


class BotTextMessage(BaseModel):
    type: Literal["bot.text"]
    content: str


class BotQuickRepliesMessage(BaseModel):
    type: Literal["bot.quick_replies"]
    chips: list[QuickReplyChip]


BotMessage = BotTextMessage | BotQuickRepliesMessage


class ChatResponse(BaseModel):
    session_id: str
    state: Literal["asking", "result"]
    bot_messages: list[BotMessage]


class UpsertConditionsRequest(BaseModel):
    session_id: str | None
    raw: Conditions
    conditions: Conditions


class UpsertConditionsResponse(BaseModel):
    session_id: str
    conditions: Conditions


class FilterRegionsRequest(BaseModel):
    conditions: Conditions


class FilterRegionsResponse(BaseModel):
    regions: list[str]


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detail: str
