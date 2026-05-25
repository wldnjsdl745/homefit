from app.schemas import ApartmentDetail, Conditions, DealType
from app.services.result_formatter import ResultFormatter


def test_result_formatter_formats_apartment_result() -> None:
    formatter = ResultFormatter()
    apartments = [
        ApartmentDetail(sigungu="마포구", dong="합정동", name="마포 한강 자이", avg_price_manwon=50_000, avg_area_sqm=59.0, built_year=2018),
        ApartmentDetail(sigungu="성동구", dong="성수동", name="서울숲 리버뷰", avg_price_manwon=55_000, avg_area_sqm=84.0, built_year=2021),
    ]

    result = formatter.format(
        Conditions(budget_max=500_000_000, deal_type=DealType.JEONSE),
        apartments,
    )

    assert "전세" in result
    assert "5억" in result
    assert "마포 한강 자이" in result
    assert "서울숲 리버뷰" in result


def test_result_formatter_shows_commute_label() -> None:
    from app.schemas import CommuteDestination

    formatter = ResultFormatter()
    apartments = [
        ApartmentDetail(sigungu="마포구", dong="합정동", name="마포 한강 자이", avg_price_manwon=50_000, avg_area_sqm=59.0, built_year=2018, commute_minutes=20),
    ]

    result = formatter.format(
        Conditions(budget_max=500_000_000, deal_type=DealType.JEONSE, commute_destination=CommuteDestination.HONGDAE),
        apartments,
    )

    assert "홍대" in result
    assert "20분" in result
