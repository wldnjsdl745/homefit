from app.schemas import Conditions, DealType
from app.services.dialog_policy import DialogPolicy, DialogStep


def test_dialog_policy_orders_budget_then_deal_type_then_result() -> None:
    policy = DialogPolicy()

    assert policy.next_step(Conditions()) == DialogStep.ASK_BUDGET
    assert policy.next_step(Conditions(budget_max=200_000_000)) == DialogStep.ASK_DEAL_TYPE
    assert (
        policy.next_step(Conditions(budget_max=200_000_000, deal_type=DealType.JEONSE))
        == DialogStep.RESULT
    )
