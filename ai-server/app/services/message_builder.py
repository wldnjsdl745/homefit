from app.schemas import BotMessage, BotTextMessage, Conditions
from app.services.result_formatter import ResultFormatter


class MessageBuilder:
    def __init__(self, formatter: ResultFormatter | None = None):
        self.formatter = formatter or ResultFormatter()

    def ask_budget(self) -> list[BotMessage]:
        return [BotTextMessage(type="bot.text", content="먼저 자본금이 어느 정도인지 알려주세요.")]

    def ask_deal_type(self) -> list[BotMessage]:
        return [
            BotTextMessage(
                type="bot.text",
                content="전세/월세 중 어떤 걸 원하시는지 알려주세요.",
            )
        ]

    def result(self, conditions: Conditions, regions: list[str]) -> list[BotMessage]:
        if not regions:
            return self.empty_result()

        return [
            BotTextMessage(type="bot.text", content="잠시만요..."),
            BotTextMessage(type="bot.text", content=self.formatter.format(conditions, regions)),
        ]

    def empty_result(self) -> list[BotMessage]:
        return [
            BotTextMessage(
                type="bot.text",
                content="조건에 맞는 지역을 찾지 못했어요. 새 대화로 다시 입력해볼까요?",
            )
        ]

    def fallback(self) -> list[BotMessage]:
        return [BotTextMessage(type="bot.text", content="잠시 문제가 있어요. 다시 입력해주세요.")]
