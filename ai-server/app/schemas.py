"""Pydantic 스키마 — 시스템 전체의 단일 진실(single source of truth).

각 필드는 type / range / 의미 / 추출 방법 / 단계 / 예시를 description에 명시한다.
FastAPI가 이 정보를 OpenAPI 문서로 자동 노출하므로 별도 카탈로그 MD가 필요 없다.

참고: 칩(chip_id) → conditions 매핑은 `app.services.chip_catalog` 참고.
"""

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class DealType(StrEnum):
    """거래 유형. jeonse / monthly_rent / sale."""

    JEONSE = "jeonse"
    MONTHLY_RENT = "monthly_rent"
    SALE = "sale"


class CommuteDestination(StrEnum):
    """통근 목적지 업무지구. BE region_commute 테이블의 destination_key와 일치."""

    GANGNAM = "gangnam"
    YEOUIDO = "yeouido"
    GWANGHWAMUN = "gwanghwamun"
    HONGDAE = "hongdae"
    JAMSIL = "jamsil"


class AgeGroupPreference(StrEnum):
    """사용자가 함께 살고 싶어 하는 동네 연령층/생활 단계."""

    YOUNG_ADULT = "young_adult"
    FAMILY = "family"
    SENIOR = "senior"
    ANY = "any"


class InfrastructurePriority(StrEnum):
    """지역 추천에 반영할 주변 인프라 우선순위."""

    SCHOOL = "school"
    MEDICAL = "medical"
    FITNESS = "fitness"
    QUIET = "quiet"
    TRANSIT = "transit"
    NIGHTLIFE = "nightlife"


class Conditions(BaseModel):
    """사용자 추천 조건 누적 상태.

    - `extra="forbid"`: 정의되지 않은 키는 거부 (LLM의 hallucinated 키 방어).
    - 모든 필드 optional: 대화가 진행되면서 점진적으로 채워진다.
    """

    model_config = ConfigDict(extra="forbid")

    budget_max: Annotated[
        int | None,
        Field(
            default=None,
            gt=0,
            le=10_000_000_000,
            description=(
                "사용자 자본금 상한 (원 단위 정수). "
                "추출 방법: LLM(자연어) / 칩(`budget_*`) / FE 정규식(숫자). "
                "단계: v0. 예: '2억' → 200000000."
            ),
            examples=[200_000_000, 50_000_000, 700_000_000],
        ),
    ] = None

    deal_type: Annotated[
        DealType | None,
        Field(
            default=None,
            description=(
                "거래 유형. jeonse / monthly_rent / sale. "
                "추출 방법: LLM(자연어) / 칩(`deal_jeonse` / `deal_monthly_rent` / `deal_sale`). "
            ),
            examples=["jeonse", "monthly_rent", "sale"],
        ),
    ] = None

    monthly_rent_max: Annotated[
        int | None,
        Field(
            default=None,
            gt=0,
            le=100_000_000,
            description=(
                "월세 상한 (원 단위 정수). deal_type=monthly_rent 일 때만 사용. "
                "전세/매매는 null. 예: '80만원' → 800000."
            ),
            examples=[500_000, 800_000, 1_000_000],
        ),
    ] = None

    preferred_region: Annotated[
        str | None,
        Field(
            default=None,
            description=(
                "사용자가 희망하는 서울 지역명. 구/동/역세권 자유 텍스트. "
                "예: '마포구', '성수동', '강남 근처'. 없으면 null."
            ),
            examples=["마포구", "성수동", "강남 근처"],
        ),
    ] = None

    commute_destination: Annotated[
        CommuteDestination | None,
        Field(
            default=None,
            description=(
                "주요 통근 목적지 업무지구. "
                "gangnam / yeouido / gwanghwamun / hongdae / jamsil. "
                "null이면 통근 시간 점수 미적용. "
                "추출 방법: AI 서버가 workplace → 업무지구 매핑."
            ),
            examples=["gangnam", "yeouido"],
        ),
    ] = None

    workplace: Annotated[
        str | None,
        Field(
            default=None,
            description=(
                "사용자가 말한 직장/출퇴근 지역 (자유 텍스트). "
                "예: '논현', '역삼역', '광화문 근처'. "
                "AI 서버가 commute_destination으로 변환."
            ),
            examples=["논현", "역삼", "광화문"],
        ),
    ] = None

    preference_text: Annotated[
        str | None,
        Field(
            default=None,
            description=(
                "사용자 추가 희망 사항 자유 텍스트. "
                "추출 방법: **FE가 raw에 직접 넣어 전송** (LLM은 정책상 추출 거부). "
            ),
            examples=["강남 근처면 좋겠어요", "역세권 선호", ""],
        ),
    ] = None

    age_group: Annotated[
        AgeGroupPreference | None,
        Field(
            default=None,
            description=(
                "비슷한 생활권으로 선호하는 연령층/생활 단계. "
                "young_adult / family / senior / any."
            ),
            examples=["young_adult", "family", "senior", "any"],
        ),
    ] = None

    infrastructure_priorities: Annotated[
        list[InfrastructurePriority] | None,
        Field(
            default=None,
            description=(
                "추천에 강조할 인프라 목록. school / medical / fitness / quiet / "
                "transit / nightlife. 여러 개 가능."
            ),
            examples=[["school", "medical"], ["quiet", "transit"]],
        ),
    ] = None


# ─── /chat (FE → AI) ──────────────────────────────────────


class ChatRequest(BaseModel):
    """FE → AI 서버 요청.

    - `session_id=None`: 첫 호출. AI 서버가 새 UUID 발급.
    - `raw`: 이번 턴에서 명시된 구조화 입력 (칩 또는 FE 매핑 결과).
    - `raw_message`: (선택) 자유 텍스트. AI 서버의 LLM이 의미 추출에 사용.
    """

    session_id: str | None = Field(
        default=None,
        description="세션 식별자(UUID). 첫 호출엔 null/생략, 응답으로 받은 값을 재사용.",
    )
    raw: Conditions = Field(
        default_factory=Conditions,
        description="이번 턴의 구조화 입력. 누적은 BE가 보유하므로 매 턴 부분 입력만 보낸다.",
    )
    raw_message: str | None = Field(
        default=None,
        description="자유 텍스트 입력(선택). LLM이 raw로 추출 시도.",
        examples=["2억 정도 있어요", "전세로 보고 있어"],
    )


class QuickReplyChip(BaseModel):
    id: str = Field(description="칩 식별자. `chip_catalog.CHIP_DEFINITIONS`의 키와 일치.")
    label: str = Field(description="사용자에게 노출되는 한국어 라벨.")


class BotTextMessage(BaseModel):
    type: Literal["bot.text"]
    content: str


class BotQuickRepliesMessage(BaseModel):
    type: Literal["bot.quick_replies"]
    chips: list[QuickReplyChip]


BotMessage = BotTextMessage | BotQuickRepliesMessage


class ChatResponse(BaseModel):
    """AI 서버 → FE 응답.

    `bot_messages` 배열 순서대로 FE가 챗봇 메시지로 렌더한다.
    """

    session_id: str
    state: Literal["asking", "result"]
    bot_messages: list[BotMessage]
    error: "ErrorResponse | None" = None


# ─── 내부 API (AI 서버 → BE) ──────────────────────────────


class UpsertConditionsRequest(BaseModel):
    """AI 서버 → BE: 세션 조회/생성 + 머지된 conditions 저장."""

    session_id: str | None
    raw: Conditions
    conditions: Conditions


class UpsertConditionsResponse(BaseModel):
    session_id: str
    conditions: Conditions


class FilterRegionsRequest(BaseModel):
    """AI 서버 → BE: conditions로 지역 필터링 요청 (저장 안 됨)."""

    conditions: Conditions


class RegionDetail(BaseModel):
    name: str
    commute_minutes: int | None = None
    safety_grade: str | None = None


class ApartmentDetail(BaseModel):
    sigungu: str
    dong: str | None = None
    name: str | None = None
    avg_price_manwon: int | None = Field(default=None, alias="avg_price_manwon")
    min_price_manwon: int | None = Field(default=None, alias="min_price_manwon")
    max_price_manwon: int | None = Field(default=None, alias="max_price_manwon")
    avg_area_sqm: float | None = Field(default=None, alias="avg_area_sqm")
    built_year: int | None = Field(default=None, alias="built_year")
    commute_minutes: int | None = Field(default=None, alias="commute_minutes")
    deal_count: int | None = Field(default=None, alias="deal_count")
    age_profile: str | None = Field(default=None, alias="age_profile")
    infrastructure_summary: str | None = Field(default=None, alias="infrastructure_summary")
    recommendation_reason: str | None = Field(default=None, alias="recommendation_reason")

    model_config = ConfigDict(populate_by_name=True)


class FilterRegionsResponse(BaseModel):
    regions: list[str] = Field(
        description="추천 지역 한국어 이름 리스트. 시군구 단위.",
        examples=[["마포구", "성동구", "광진구"]],
    )
    region_details: list[RegionDetail] = Field(default_factory=list)
    apartments: list[ApartmentDetail] = Field(default_factory=list)


# ─── 헬스체크 / 에러 ──────────────────────────────────────


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    detail: str
