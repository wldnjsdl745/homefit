"""칩(quick_reply) 정의 카탈로그 — 단일 진실(single source of truth).

각 칩은 `chip_id` → `(라벨, 매핑되는 conditions 부분)` 으로 정의된다.

용도:
  1. AI 서버 `MessageBuilder`가 `bot.quick_replies` 메시지를 만들 때
     이 카탈로그를 참고한다.
  2. AI 서버는 `chip_id → raw` 변환을 직접 하지 않는다 (FE가 변환해서 보냄).
  3. FE의 [`chipMapper.ts`](../../../frontend/src/lib/chipMapper.ts)는 본 카탈로그를
     1:1 미러링한다. 변경 시 양쪽 동시 갱신.

`Conditions` 스키마와의 관계:
  - 각 칩의 `raw`는 [`Conditions`](../schemas.py)의 부분 인스턴스.
  - Pydantic `extra="forbid"`로 알 수 없는 키는 차단됨.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas import (
    AgeGroupPreference,
    Conditions,
    DealType,
    InfrastructurePriority,
    QuickReplyChip,
)


@dataclass(frozen=True)
class ChipDefinition:
    """단일 칩 정의."""

    chip_id: str
    label: str
    raw: Conditions

    def to_quick_reply(self) -> QuickReplyChip:
        return QuickReplyChip(id=self.chip_id, label=self.label)


# ─── Q1: 자본금 (budget_max) ──────────────────────────────

CHIP_BUDGET_UNDER_1: ChipDefinition = ChipDefinition(
    chip_id="budget_under_1",
    label="1억 미만",
    raw=Conditions(budget_max=50_000_000),
)
CHIP_BUDGET_1_3: ChipDefinition = ChipDefinition(
    chip_id="budget_1_3",
    label="1-3억",
    raw=Conditions(budget_max=200_000_000),
)
CHIP_BUDGET_3_5: ChipDefinition = ChipDefinition(
    chip_id="budget_3_5",
    label="3-5억",
    raw=Conditions(budget_max=400_000_000),
)
CHIP_BUDGET_5_ABOVE: ChipDefinition = ChipDefinition(
    chip_id="budget_5_above",
    label="5억 이상",
    raw=Conditions(budget_max=700_000_000),
)

BUDGET_CHIPS: tuple[ChipDefinition, ...] = (
    CHIP_BUDGET_UNDER_1,
    CHIP_BUDGET_1_3,
    CHIP_BUDGET_3_5,
    CHIP_BUDGET_5_ABOVE,
)

# ─── Q2: 거래 유형 (deal_type) ────────────────────────────

CHIP_DEAL_JEONSE: ChipDefinition = ChipDefinition(
    chip_id="deal_jeonse",
    label="전세",
    raw=Conditions(deal_type=DealType.JEONSE),
)
CHIP_DEAL_MONTHLY_RENT: ChipDefinition = ChipDefinition(
    chip_id="deal_monthly_rent",
    label="월세",
    raw=Conditions(deal_type=DealType.MONTHLY_RENT),
)

CHIP_DEAL_SALE: ChipDefinition = ChipDefinition(
    chip_id="deal_sale",
    label="매매",
    raw=Conditions(deal_type=DealType.SALE),
)

DEAL_CHIPS: tuple[ChipDefinition, ...] = (
    CHIP_DEAL_JEONSE,
    CHIP_DEAL_MONTHLY_RENT,
    CHIP_DEAL_SALE,
)

# ─── Q5: 선호 연령층/생활 단계 ──────────────────────────

CHIP_AGE_YOUNG: ChipDefinition = ChipDefinition(
    chip_id="age_young_adult",
    label="20-30대 많은 곳",
    raw=Conditions(age_group=AgeGroupPreference.YOUNG_ADULT),
)
CHIP_AGE_FAMILY: ChipDefinition = ChipDefinition(
    chip_id="age_family",
    label="아이 키우는 가족",
    raw=Conditions(age_group=AgeGroupPreference.FAMILY),
)
CHIP_AGE_SENIOR: ChipDefinition = ChipDefinition(
    chip_id="age_senior",
    label="조용한 고령층 지역",
    raw=Conditions(age_group=AgeGroupPreference.SENIOR),
)
CHIP_AGE_ANY: ChipDefinition = ChipDefinition(
    chip_id="age_any",
    label="상관없음",
    raw=Conditions(age_group=AgeGroupPreference.ANY),
)

AGE_CHIPS: tuple[ChipDefinition, ...] = (
    CHIP_AGE_YOUNG,
    CHIP_AGE_FAMILY,
    CHIP_AGE_SENIOR,
    CHIP_AGE_ANY,
)

# ─── Q6: 중요 인프라 ───────────────────────────────────

CHIP_INFRA_SCHOOL: ChipDefinition = ChipDefinition(
    chip_id="infra_school",
    label="학교",
    raw=Conditions(infrastructure_priorities=[InfrastructurePriority.SCHOOL]),
)
CHIP_INFRA_MEDICAL: ChipDefinition = ChipDefinition(
    chip_id="infra_medical",
    label="병원",
    raw=Conditions(infrastructure_priorities=[InfrastructurePriority.MEDICAL]),
)
CHIP_INFRA_FITNESS: ChipDefinition = ChipDefinition(
    chip_id="infra_fitness",
    label="운동시설",
    raw=Conditions(infrastructure_priorities=[InfrastructurePriority.FITNESS]),
)
CHIP_INFRA_QUIET: ChipDefinition = ChipDefinition(
    chip_id="infra_quiet",
    label="조용한 곳",
    raw=Conditions(infrastructure_priorities=[InfrastructurePriority.QUIET]),
)
CHIP_INFRA_TRANSIT: ChipDefinition = ChipDefinition(
    chip_id="infra_transit",
    label="교통",
    raw=Conditions(infrastructure_priorities=[InfrastructurePriority.TRANSIT]),
)
CHIP_INFRA_ANY: ChipDefinition = ChipDefinition(
    chip_id="infra_any",
    label="상관없음",
    raw=Conditions(infrastructure_priorities=[]),
)

INFRA_CHIPS: tuple[ChipDefinition, ...] = (
    CHIP_INFRA_SCHOOL,
    CHIP_INFRA_MEDICAL,
    CHIP_INFRA_FITNESS,
    CHIP_INFRA_QUIET,
    CHIP_INFRA_TRANSIT,
    CHIP_INFRA_ANY,
)

# ─── 액션 칩 (값 매핑 없음) ──────────────────────────────
# 사용자 의도 표시용. raw는 비어 있고 FE가 처리(세션 재시작 등).

CHIP_RESTART: ChipDefinition = ChipDefinition(
    chip_id="restart",
    label="다시 추천",
    raw=Conditions(),
)
CHIP_BUDGET_RESTART: ChipDefinition = ChipDefinition(
    chip_id="budget_restart",
    label="자본금 다시",
    raw=Conditions(),
)
CHIP_RETRY: ChipDefinition = ChipDefinition(
    chip_id="retry",
    label="재시도",
    raw=Conditions(),
)

ACTION_CHIPS: tuple[ChipDefinition, ...] = (
    CHIP_RESTART,
    CHIP_BUDGET_RESTART,
    CHIP_RETRY,
)

# ─── 통합 인덱스 ─────────────────────────────────────────

CHIP_DEFINITIONS: dict[str, ChipDefinition] = {
    chip.chip_id: chip
    for chip in (*BUDGET_CHIPS, *DEAL_CHIPS, *AGE_CHIPS, *INFRA_CHIPS, *ACTION_CHIPS)
}



def quick_replies(*chips: ChipDefinition) -> list[QuickReplyChip]:
    """주어진 ChipDefinition들을 QuickReplyChip 리스트로 변환."""

    return [chip.to_quick_reply() for chip in chips]


def lookup(chip_id: str) -> ChipDefinition:
    """chip_id로 정의를 찾는다. 없으면 KeyError.

    AI 서버는 보통 chip_id를 직접 해석할 일이 없지만 (FE가 raw로 변환해 보냄),
    감사/디버깅 용도로 제공.
    """

    try:
        return CHIP_DEFINITIONS[chip_id]
    except KeyError as exc:
        raise KeyError(f"Unknown chip_id: {chip_id!r}") from exc
