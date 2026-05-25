import re

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

        has_named_complex = any(apt.name for apt in apartments)
        target_label = "아파트" if has_named_complex else "지역 후보"

        if dest_label:
            header = f"**{dest_label} 출퇴근 기준 추천 {target_label}**"
        else:
            header = f"**조건에 맞는 서울 {target_label}**"

        if conditions.deal_type == DealType.MONTHLY_RENT:
            budget = self._fmt_budget(conditions.budget_max)
            rent = self._fmt_budget(conditions.monthly_rent_max)
            budget_line = f"보증금 {budget} · 월세 {rent} 이하"
        else:
            deal = self._fmt_deal(conditions.deal_type)
            budget_line = f"{deal} {self._fmt_budget(conditions.budget_max)} 이하"

        parts: list[str] = []
        for index, apt in enumerate(apartments[:3], start=1):
            location = f"{apt.dong} {apt.name}" if apt.name else " ".join(
                part for part in (apt.sigungu, apt.dong) if part
            )
            summary: list[str] = [apt.sigungu]
            if apt.avg_price_manwon:
                summary.append(f"평균 **{self._fmt_manwon_value(apt.avg_price_manwon)}**")
            if apt.commute_minutes is not None and dest_label:
                summary.append(f"{dest_label} **{apt.commute_minutes}분**")
            if apt.deal_count:
                summary.append(f"거래 {apt.deal_count}건")

            reason = self._short_reason(apt)
            parts.append(
                f"### {index}. {location}\n"
                f"- {' · '.join(summary)}\n"
                f"- {reason}"
            )

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
        return f"평균 {self._fmt_manwon_value(manwon)}"

    def _fmt_manwon_value(self, manwon: int) -> str:
        """만원 단위 금액 값만 '억' 또는 '만원'으로 표기."""
        won = manwon * 10_000
        if won >= 100_000_000:
            return f"{won / 100_000_000:g}억"
        return f"{manwon}만원"

    def _short_reason(self, apt: ApartmentDetail) -> str:
        reasons: list[str] = []

        if apt.age_profile:
            reasons.append(apt.age_profile)

        if apt.infrastructure_summary:
            infra = self._parse_infra(apt.infrastructure_summary)
            school = infra.get("학교", 0)
            medical = infra.get("의료", 0)
            nightlife = infra.get("유흥시설", 0)
            transit = infra.get("교통", 0)

            if school > 0:
                reasons.append(f"학교 {school}곳")
            if medical > 0:
                reasons.append(f"의료 {medical}곳")
            if transit > 0:
                reasons.append(f"교통 {transit}곳")
            if nightlife <= 3:
                reasons.append("유흥시설 적음")

        if not reasons and apt.recommendation_reason:
            text = apt.recommendation_reason.replace("추천 이유: ", "")
            reasons.extend(text.split(", ")[:2])

        if not reasons:
            reasons.append("예산과 출퇴근 조건에 맞는 후보")

        return " · ".join(reasons[:3])

    def _parse_infra(self, text: str) -> dict[str, int]:
        result: dict[str, int] = {}
        for key, value in re.findall(r"(학교|의료|운동시설|유흥시설|교통) (\d+)", text):
            result[key] = int(value)
        return result
