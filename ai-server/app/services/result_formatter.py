from app.schemas import ApartmentDetail, CommuteDestination, Conditions, DealType

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
        apartments: list[ApartmentDetail],
    ) -> str:
        dest_label = (
            _COMMUTE_LABEL.get(conditions.commute_destination, "")
            if conditions.commute_destination
            else ""
        )

        if dest_label:
            header = f"{dest_label} 출퇴근을 고려해서 추천한 아파트예요."
        else:
            header = "조건에 맞는 서울 아파트예요."

        if conditions.deal_type == DealType.MONTHLY_RENT:
            budget = self._fmt_budget(conditions.budget_max)
            rent = self._fmt_budget(conditions.monthly_rent_max)
            budget_line = f"보증금 {budget} · 월세 {rent} 이하"
        else:
            deal = self._fmt_deal(conditions.deal_type)
            budget_line = f"{deal} {self._fmt_budget(conditions.budget_max)} 이하"

        parts: list[str] = []
        for apt in apartments:
            location = f"{apt.dong} {apt.name}" if apt.name else apt.dong or apt.sigungu
            tags: list[str] = []
            if apt.avg_price_manwon:
                tags.append(self._fmt_manwon(apt.avg_price_manwon))
            if apt.avg_area_sqm:
                tags.append(f"{apt.avg_area_sqm:.0f}㎡")
            if apt.built_year:
                tags.append(f"{apt.built_year}년")
            if apt.commute_minutes is not None and dest_label:
                tags.append(f"{dest_label} {apt.commute_minutes}분")
            tag_str = " · ".join(tags)
            parts.append(f"{location} ({apt.sigungu})\n  {tag_str}" if tag_str else f"{location} ({apt.sigungu})")

        apt_text = "\n\n".join(parts)
        return f"{header}\n{budget_line}\n\n{apt_text}"

    def _fmt_deal(self, deal_type: DealType | None) -> str:
        if deal_type == DealType.JEONSE:
            return "전세"
        if deal_type == DealType.SALE:
            return "매매"
        return "거래 유형"

    def _fmt_budget(self, value: int | None) -> str:
        if value is None:
            return "입력하신"
        if value >= 100_000_000:
            return f"{value / 100_000_000:g}억"
        return f"{round(value / 10_000)}만원"

    def _fmt_manwon(self, manwon: int) -> str:
        """만원 단위 금액을 '억' 또는 '만원'으로 표기."""
        won = manwon * 10_000
        if won >= 100_000_000:
            return f"평균 {won / 100_000_000:g}억"
        return f"평균 {manwon}만원"
