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
    assert (
        policy.next_step(Conditions(budget_max=200_000_000, deal_type=DealType.SALE))
        == DialogStep.RESULT
    )


def test_dialog_policy_asks_monthly_rent_for_monthly_rent_type() -> None:
    policy = DialogPolicy()

    assert (
        policy.next_step(Conditions(budget_max=200_000_000, deal_type=DealType.MONTHLY_RENT))
        == DialogStep.ASK_MONTHLY_RENT
    )
    assert (
        policy.next_step(
            Conditions(
                budget_max=200_000_000,
                deal_type=DealType.MONTHLY_RENT,
                monthly_rent_max=800_000,
            )
        )
        == DialogStep.RESULT
    )
