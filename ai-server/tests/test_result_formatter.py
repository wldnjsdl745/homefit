from app.schemas import ApartmentDetail, Conditions, DealType
from app.services.result_formatter import ResultFormatter


def test_result_formatter_formats_apartment_result() -> None:
    formatter = ResultFormatter()
    apartments = [
        ApartmentDetail(
            sigungu="마포구",
            dong="합정동",
            name="마포 한강 자이",
            avg_price_manwon=50_000,
            avg_area_sqm=59.0,
            built_year=2018,
        ),
        ApartmentDetail(
            sigungu="성동구",
            dong="성수동",
            name="서울숲 리버뷰",
            avg_price_manwon=55_000,
            avg_area_sqm=84.0,
            built_year=2021,
        ),
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
        ApartmentDetail(
            sigungu="마포구",
            dong="합정동",
            name="마포 한강 자이",
            avg_price_manwon=50_000,
            avg_area_sqm=59.0,
            built_year=2018,
            commute_minutes=20,
        ),
    ]

    result = formatter.format(
        Conditions(
            budget_max=500_000_000,
            deal_type=DealType.JEONSE,
            commute_destination=CommuteDestination.HONGDAE,
        ),
        apartments,
    )

    assert "홍대" in result
    assert "20분" in result


def test_result_formatter_shows_region_lifestyle_explanations() -> None:
    formatter = ResultFormatter()
    apartments = [
        ApartmentDetail(
            sigungu="마포구",
            dong="공덕동",
            avg_price_manwon=45_000,
            deal_count=18,
            age_profile="연령층: 유소년 10.2%, 청년 32.1%, 고령층 15.4%",
            infrastructure_summary="인프라: 학교 8, 의료 12, 운동시설 3, 유흥시설 1, 교통 4",
            recommendation_reason="추천 이유: 선호 연령층과 유사, 중요 인프라 조건이 좋음",
        ),
    ]

    result = formatter.format(
        Conditions(budget_max=500_000_000, deal_type=DealType.JEONSE),
        apartments,
    )

    assert "서울 지역 후보" in result
    assert "법정동 단위로 계산" in result
    assert "예산 내 평균" in result
    assert "연령층" in result
    assert "학교 8곳" in result
    assert "의료 12곳" in result


def test_result_formatter_marks_gu_level_infrastructure() -> None:
    formatter = ResultFormatter()
    apartments = [
        ApartmentDetail(
            sigungu="송파구",
            dong="마천동",
            avg_price_manwon=13_522,
            deal_count=800,
            infrastructure_summary=(
                "인프라(송파구 전체): 학교 90, 의료 0, "
                "운동시설 0, 유흥시설 210, 교통 0"
            ),
            recommendation_reason="추천 이유: 최근 거래 표본이 충분함",
        ),
    ]

    result = formatter.format(
        Conditions(budget_max=200_000_000, deal_type=DealType.JEONSE),
        apartments,
    )

    assert "송파구 전체 기준 학교 90곳" in result
    assert "최근 거래 표본이 충분함" not in result
