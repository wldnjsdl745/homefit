from app.schemas import Conditions, DealType


class ResultFormatter:
    def format(self, conditions: Conditions, regions: list[str]) -> str:
        region_text = "·".join(regions)

        if conditions.deal_type == DealType.MONTHLY_RENT:
            budget = self.format_budget(conditions.budget_max)
            rent = self.format_budget(conditions.monthly_rent_max)
            return f"월세 보증금 {budget}, 월세 {rent} 이하 조건에 맞는 서울 지역은 {region_text}입니다."

        deal_type = self.format_deal_type(conditions.deal_type)
        budget = self.format_budget(conditions.budget_max)
        return f"{deal_type} {budget} 예산에 맞는 서울 지역은 {region_text}입니다."

    def format_deal_type(self, deal_type: DealType | None) -> str:
        if deal_type == DealType.JEONSE:
            return "전세"
        if deal_type == DealType.SALE:
            return "매매"
        return "거래 유형"

    def format_budget(self, value: int | None) -> str:
        if value is None:
            return "입력하신"

        if value >= 100_000_000:
            amount = value / 100_000_000
            return f"{amount:g}억"

        return f"{round(value / 10_000)}만원"
