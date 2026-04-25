from app.schemas import Conditions, DealType
from app.services.result_formatter import ResultFormatter


def test_result_formatter_formats_korean_result_text() -> None:
    formatter = ResultFormatter()

    result = formatter.format(
        Conditions(budget_max=200_000_000, deal_type=DealType.JEONSE),
        ["분당", "성남", "경기도"],
    )

    assert result == "전세 2억 예산에 맞는 지역은 분당·성남·경기도입니다."
