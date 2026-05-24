from app.schemas import CommuteDestination, Conditions, DealType, RegionDetail

_COMMUTE_LABEL: dict[CommuteDestination, str] = {
    CommuteDestination.GANGNAM: "강남",
    CommuteDestination.YEOUIDO: "여의도",
    CommuteDestination.GWANGHWAMUN: "광화문",
    CommuteDestination.HONGDAE: "홍대",
    CommuteDestination.JAMSIL: "잠실",
}


class ResultFormatter:
    def format(
        self,
        conditions: Conditions,
        regions: list[str],
        region_details: list[RegionDetail] | None = None,
    ) -> str:
        detail_map = {d.name: d for d in (region_details or [])}

        parts = []
        for name in regions:
            detail = detail_map.get(name)
            tags: list[str] = []
            if detail and detail.commute_minutes is not None and conditions.commute_destination:
                dest_label = _COMMUTE_LABEL.get(conditions.commute_destination, "")
                tags.append(f"{dest_label} {detail.commute_minutes}분")
            if detail and detail.safety_grade and conditions.deal_type == DealType.JEONSE:
                tags.append(f"안전도 {detail.safety_grade}")
            parts.append(f"{name}({', '.join(tags)})" if tags else name)

        region_text = " · ".join(parts)

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
