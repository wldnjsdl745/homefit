from enum import StrEnum

from app.schemas import Conditions


class DialogStep(StrEnum):
    ASK_BUDGET = "ask_budget"
    ASK_DEAL_TYPE = "ask_deal_type"
    RESULT = "result"


class DialogPolicy:
    def next_step(self, conditions: Conditions) -> DialogStep:
        if conditions.budget_max is None:
            return DialogStep.ASK_BUDGET

        if conditions.deal_type is None:
            return DialogStep.ASK_DEAL_TYPE

        return DialogStep.RESULT
