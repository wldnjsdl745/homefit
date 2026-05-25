from app.schemas import Conditions, DealType
from app.services.dialog_policy import DialogPolicy, DialogStep


def test_dialog_policy_orders_budget_deal_region_commute_age_infra_then_result() -> None:
    policy = DialogPolicy()

    assert policy.next_step(Conditions()) == DialogStep.ASK_BUDGET
    assert policy.next_step(Conditions(budget_max=200_000_000)) == DialogStep.ASK_DEAL_TYPE
    assert (
        policy.next_step(Conditions(budget_max=200_000_000, deal_type=DealType.JEONSE))
        == DialogStep.ASK_PREFERRED_REGION
    )
    assert (
        policy.next_step(
            Conditions(
                budget_max=200_000_000,
                deal_type=DealType.JEONSE,
                preferred_region="마포구",
            )
        )
        == DialogStep.ASK_COMMUTE
    )
    assert (
        policy.next_step(
            Conditions(
                budget_max=200_000_000,
                deal_type=DealType.SALE,
                preferred_region="상관없음",
                workplace="상관없어요",
            )
        )
        == DialogStep.ASK_AGE_GROUP
    )
    assert (
        policy.next_step(
            Conditions(
                budget_max=200_000_000,
                deal_type=DealType.SALE,
                preferred_region="상관없음",
                workplace="상관없어요",
                age_group="any",
            )
        )
        == DialogStep.ASK_INFRASTRUCTURE
    )
    assert (
        policy.next_step(
            Conditions(
                budget_max=200_000_000,
                deal_type=DealType.SALE,
                preferred_region="상관없음",
                workplace="상관없어요",
                age_group="any",
                infrastructure_priorities=[],
            )
        )
        == DialogStep.RESULT
    )


def test_dialog_policy_asks_monthly_rent_for_monthly_rent_type() -> None:
    policy = DialogPolicy()

    assert (
        policy.next_step(
            Conditions(budget_max=200_000_000, deal_type=DealType.MONTHLY_RENT)
        )
        == DialogStep.ASK_MONTHLY_RENT
    )
    assert (
        policy.next_step(
            Conditions(
                budget_max=200_000_000,
                deal_type=DealType.MONTHLY_RENT,
                preferred_region="마포구",
                workplace="홍대",
            )
        )
        == DialogStep.ASK_MONTHLY_RENT
    )
    assert (
        policy.next_step(
            Conditions(
                budget_max=200_000_000,
                deal_type=DealType.MONTHLY_RENT,
                preferred_region="마포구",
                workplace="홍대",
                monthly_rent_max=800_000,
            )
        )
        == DialogStep.ASK_AGE_GROUP
    )
    assert (
        policy.next_step(
            Conditions(
                budget_max=200_000_000,
                deal_type=DealType.MONTHLY_RENT,
                monthly_rent_max=800_000,
            )
        )
        == DialogStep.ASK_PREFERRED_REGION
    )
