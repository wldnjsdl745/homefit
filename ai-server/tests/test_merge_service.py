from app.schemas import Conditions, DealType
from app.services.merge_service import MergeService


def test_merge_service_overwrites_raw_values() -> None:
    service = MergeService()

    merged = service.merge(
        Conditions(budget_max=100_000_000, deal_type=DealType.JEONSE),
        Conditions(budget_max=200_000_000),
    )

    assert merged == Conditions(budget_max=200_000_000, deal_type=DealType.JEONSE)
