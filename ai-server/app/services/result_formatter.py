from app.schemas import Conditions, DealType


class ResultFormatter:
    def format(self, conditions: Conditions, regions: list[str]) -> str:
        deal_type = self.format_deal_type(conditions.deal_type)
        budget = self.format_budget(conditions.budget_max)
        region_text = "·".join(regions)
        return f"{deal_type} {budget} 예산에 맞는 지역은 {region_text}입니다."

    def format_deal_type(self, deal_type: DealType | None) -> str:
        if deal_type == DealType.JEONSE:
            return "전세"
        if deal_type == DealType.MONTHLY_RENT:
            return "월세"
        return "거래 유형"

    def format_budget(self, value: int | None) -> str:
        if value is None:
            return "입력하신"

        if value >= 100_000_000:
            amount = value / 100_000_000
            return f"{amount:g}억"

        return f"{round(value / 10_000)}만원"
