from app.schemas import (
    ApartmentDetail,
    BotMessage,
    BotQuickRepliesMessage,
    BotTextMessage,
    Conditions,
)
from app.services.chip_catalog import (
    CHIP_AGE_ANY,
    CHIP_AGE_FAMILY,
    CHIP_AGE_SENIOR,
    CHIP_AGE_YOUNG,
    CHIP_BUDGET_1_3,
    CHIP_BUDGET_3_5,
    CHIP_BUDGET_5_ABOVE,
    CHIP_BUDGET_RESTART,
    CHIP_BUDGET_UNDER_1,
    CHIP_DEAL_JEONSE,
    CHIP_DEAL_MONTHLY_RENT,
    CHIP_DEAL_SALE,
    CHIP_INFRA_ANY,
    CHIP_INFRA_FITNESS,
    CHIP_INFRA_MEDICAL,
    CHIP_INFRA_QUIET,
    CHIP_INFRA_SCHOOL,
    CHIP_INFRA_TRANSIT,
    CHIP_RESTART,
    CHIP_RETRY,
    quick_replies,
)
from app.services.result_formatter import ResultFormatter


class MessageBuilder:
    def __init__(self, formatter: ResultFormatter | None = None):
        self.formatter = formatter or ResultFormatter()

    def ask_budget(self) -> list[BotMessage]:
        return [
            BotTextMessage(
                type="bot.text",
                content=(
                    "거래 가능한 예산 상한을 알려주세요. "
                    "매매는 매매가, 전세와 월세는 보증금 기준이에요."
                ),
            ),
            BotQuickRepliesMessage(
                type="bot.quick_replies",
                chips=quick_replies(
                    CHIP_BUDGET_UNDER_1,
                    CHIP_BUDGET_1_3,
                    CHIP_BUDGET_3_5,
                    CHIP_BUDGET_5_ABOVE,
                ),
            ),
        ]

    def ask_deal_type(self) -> list[BotMessage]:
        return [
            BotTextMessage(
                type="bot.text",
                content="서울 실거래 데이터 기준으로 전세, 월세, 매매 중 어떤 거래를 볼까요?",
            ),
            BotQuickRepliesMessage(
                type="bot.quick_replies",
                chips=quick_replies(CHIP_DEAL_JEONSE, CHIP_DEAL_MONTHLY_RENT, CHIP_DEAL_SALE),
            ),
        ]

    def ask_commute(self) -> list[BotMessage]:
        return [
            BotTextMessage(
                type="bot.text",
                content=(
                    "직장이나 자주 가는 곳이 있나요? "
                    "논현, 역삼, 광화문처럼 알려주시면 통근 시간을 함께 반영할게요. "
                    "(없으면 '상관없어요'라고 입력해주세요)"
                ),
            ),
        ]

    def ask_monthly_rent(self) -> list[BotMessage]:
        return [
            BotTextMessage(
                type="bot.text",
                content="월세는 월 납입 상한도 필요해요. 매달 얼마까지 괜찮으신가요?",
            )
        ]

    def ask_preferred_region(self) -> list[BotMessage]:
        return [
            BotTextMessage(
                type="bot.text",
                content=(
                    "희망하는 지역이 있나요? 강남구, 마포구, 성수동처럼 알려주세요. "
                    "없으면 '상관없어요'라고 입력해주세요."
                ),
            )
        ]

    def ask_age_group(self) -> list[BotMessage]:
        return [
            BotTextMessage(
                type="bot.text",
                content="비슷한 생활권으로 어떤 연령층의 동네가 편하신가요?",
            ),
            BotQuickRepliesMessage(
                type="bot.quick_replies",
                chips=quick_replies(
                    CHIP_AGE_YOUNG,
                    CHIP_AGE_FAMILY,
                    CHIP_AGE_SENIOR,
                    CHIP_AGE_ANY,
                ),
            ),
        ]

    def ask_infrastructure(self) -> list[BotMessage]:
        return [
            BotTextMessage(
                type="bot.text",
                content="추천할 때 가장 중요하게 볼 주변 인프라를 골라주세요.",
            ),
            BotQuickRepliesMessage(
                type="bot.quick_replies",
                chips=quick_replies(
                    CHIP_INFRA_SCHOOL,
                    CHIP_INFRA_MEDICAL,
                    CHIP_INFRA_FITNESS,
                    CHIP_INFRA_QUIET,
                    CHIP_INFRA_TRANSIT,
                    CHIP_INFRA_ANY,
                ),
            ),
        ]

    def result(
        self,
        conditions: Conditions,
        apartments: list[ApartmentDetail],
        result_text: str | None = None,
    ) -> list[BotMessage]:
        if not apartments:
            return self.empty_result()

        content = result_text or self.formatter.format(conditions, apartments)
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
                content=(
                    "입력한 조건에 맞는 서울 지역 후보를 찾지 못했어요. "
                    "예산을 다시 입력해볼까요?"
                ),
            ),
            BotQuickRepliesMessage(
                type="bot.quick_replies",
                chips=quick_replies(CHIP_BUDGET_RESTART, CHIP_RESTART),
            ),
        ]

    def fallback(self, message: str = "죄송해요, 다시 시도해주세요.") -> list[BotMessage]:
        return [
            BotTextMessage(type="bot.text", content=message),
            BotQuickRepliesMessage(
                type="bot.quick_replies",
                chips=quick_replies(CHIP_RETRY),
            ),
        ]
