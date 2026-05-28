from enum import StrEnum

from app.schemas import Conditions, DealType


class DialogStep(StrEnum):
    ASK_BUDGET = "ask_budget"
    ASK_DEAL_TYPE = "ask_deal_type"
    ASK_PREFERRED_REGION = "ask_preferred_region"
    ASK_COMMUTE = "ask_commute"
    ASK_MONTHLY_RENT = "ask_monthly_rent"
    ASK_AGE_GROUP = "ask_age_group"
    ASK_INFRASTRUCTURE = "ask_infrastructure"
    RESULT = "result"


class DialogPolicy:
    def next_step(self, conditions: Conditions) -> DialogStep:
        if conditions.budget_max is None:
            return DialogStep.ASK_BUDGET

        if conditions.deal_type is None:
            return DialogStep.ASK_DEAL_TYPE

        if conditions.deal_type == DealType.MONTHLY_RENT and conditions.monthly_rent_max is None:
            return DialogStep.ASK_MONTHLY_RENT

        if conditions.preferred_region is None:
            return DialogStep.ASK_PREFERRED_REGION

        if conditions.commute_destination is None and conditions.workplace is None:
            return DialogStep.ASK_COMMUTE

        if conditions.age_group is None:
            return DialogStep.ASK_AGE_GROUP

        if conditions.infrastructure_priorities is None:
            return DialogStep.ASK_INFRASTRUCTURE

        return DialogStep.RESULT
