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

    def ask_preference(self) -> list[BotMessage]:
        return [
            BotTextMessage(
                type="bot.text",
                content="추가로 희망하시는 조건이 있나요?",
            )
        ]

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
            BotTextMessage(type="bot.text", content="잠시만요..."),
            BotTextMessage(type="bot.text", content=content),
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

    def unsupported_conditions(self) -> list[BotMessage]:
        return [
            BotTextMessage(
                type="bot.text",
                content=(
                    "죄송해요, 아직 해당 조건은 이해하지 못해요. "
                    "예산과 전세/월세를 알려주세요."
                ),
            )
        ]
