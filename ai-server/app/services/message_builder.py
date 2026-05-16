from app.schemas import BotMessage, BotQuickRepliesMessage, BotTextMessage, Conditions
from app.services.chip_catalog import (
    CHIP_BUDGET_RESTART,
    CHIP_DEAL_JEONSE,
    CHIP_DEAL_MONTHLY_RENT,
    CHIP_DEAL_SALE,
    CHIP_RESTART,
    CHIP_RETRY,
    quick_replies,
)
from app.services.result_formatter import ResultFormatter


class MessageBuilder:
    def __init__(self, formatter: ResultFormatter | None = None):
        self.formatter = formatter or ResultFormatter()

    def ask_budget(self) -> list[BotMessage]:
        return [BotTextMessage(type="bot.text", content="먼저 자본금이 어느 정도인지 알려주세요.")]

    def ask_deal_type(self) -> list[BotMessage]:
        return [
            BotTextMessage(type="bot.text", content="전세, 월세, 매매 중 어떤 걸 원하시는지 알려주세요."),
            BotQuickRepliesMessage(
                type="bot.quick_replies",
                chips=quick_replies(CHIP_DEAL_JEONSE, CHIP_DEAL_MONTHLY_RENT, CHIP_DEAL_SALE),
            ),
        ]

    def ask_monthly_rent(self) -> list[BotMessage]:
        return [BotTextMessage(type="bot.text", content="월마다 나가는 월세 예산을 얼마로 생각하시나요?")]

    def result(
        self,
        conditions: Conditions,
        regions: list[str],
        result_text: str | None = None,
    ) -> list[BotMessage]:
        if not regions:
            return self.empty_result()

        content = result_text or self.formatter.format(conditions, regions)
        return [
            BotTextMessage(type="bot.text", content=content),
            BotQuickRepliesMessage(
                type="bot.quick_replies",
                chips=quick_replies(CHIP_RESTART),
            ),
        ]

    def empty_result(self) -> list[BotMessage]:
        return [
            BotTextMessage(
                type="bot.text",
                content="입력한 조건에 맞는 서울 지역을 찾지 못했어요. 자본금을 다시 입력해볼까요?",
            ),
            BotQuickRepliesMessage(
                type="bot.quick_replies",
                chips=quick_replies(CHIP_BUDGET_RESTART, CHIP_RESTART),
            ),
        ]

    def fallback(self) -> list[BotMessage]:
        return [
            BotTextMessage(type="bot.text", content="죄송해요, 다시 시도해주세요."),
            BotQuickRepliesMessage(
                type="bot.quick_replies",
                chips=quick_replies(CHIP_RETRY),
            ),
        ]
