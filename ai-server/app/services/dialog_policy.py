from enum import StrEnum

from app.schemas import Conditions, DealType


class DialogStep(StrEnum):
    ASK_BUDGET = "ask_budget"
    ASK_DEAL_TYPE = "ask_deal_type"
    ASK_COMMUTE = "ask_commute"
    ASK_MONTHLY_RENT = "ask_monthly_rent"
    RESULT = "result"


class DialogPolicy:
    def next_step(self, conditions: Conditions) -> DialogStep:
        if conditions.budget_max is None:
            return DialogStep.ASK_BUDGET

        if conditions.deal_type is None:
            return DialogStep.ASK_DEAL_TYPE

        if conditions.commute_destination is None and not conditions.commute_skipped:
            return DialogStep.ASK_COMMUTE

        if conditions.deal_type == DealType.MONTHLY_RENT and conditions.monthly_rent_max is None:
            return DialogStep.ASK_MONTHLY_RENT

        return DialogStep.RESULT
