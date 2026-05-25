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
        dest_label = (
            _COMMUTE_LABEL.get(conditions.commute_destination, "")
            if conditions.commute_destination
            else ""
        )

        parts = []
        for name in regions:
            detail = detail_map.get(name)
            tags: list[str] = []
            if detail and detail.commute_minutes is not None and dest_label:
                tags.append(f"{dest_label}까지 {detail.commute_minutes}분")
            if detail and detail.safety_grade and conditions.deal_type == DealType.JEONSE:
                tags.append(f"안전도 {detail.safety_grade}")
            parts.append(f"{name}({', '.join(tags)})" if tags else name)

        region_text = " · ".join(parts)

        # 헤더: 통근지 명시 여부로 분기
        if dest_label:
            header = f"{dest_label} 출퇴근을 고려해서 추천한 지역이에요."
        else:
            header = "조건에 맞는 서울 지역이에요."

        # 예산 요약
        if conditions.deal_type == DealType.MONTHLY_RENT:
            budget = self.format_budget(conditions.budget_max)
            rent = self.format_budget(conditions.monthly_rent_max)
            budget_line = f"보증금 {budget} · 월세 {rent} 이하"
        else:
            deal = self.format_deal_type(conditions.deal_type)
            budget_line = f"{deal} {self.format_budget(conditions.budget_max)} 이하"

        return f"{header}\n{budget_line} 기준으로 살기 좋은 곳이에요.\n\n{region_text}"

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
