/**
 * 칩 매핑 — `chip_id` → `(라벨, raw)` 변환.
 *
 * **단일 진실(canonical source)**: `ai-server/app/services/chip_catalog.py`
 * 본 파일은 그 카탈로그의 1:1 TypeScript 미러다.
 * 변경 시 ai-server 측 `chip_catalog.py` + 본 파일을 동시 갱신할 것.
 *
 * 정의된 칩 그룹:
 *  - 자본금 (`budget_*`): Q1 단계, `Conditions.budget_max` 매핑
 *  - 거래 유형 (`deal_*`): Q2 단계, `Conditions.deal_type` 매핑
 *  - 액션 (`restart` / `budget_restart` / `retry`): 값 매핑 없음, FE가 의도 처리
 */

import type { Conditions } from "../types/chat";

export type ChipAction =
  | { kind: "submit"; raw: Conditions; label: string }
  | { kind: "restart"; label: string }
  | { kind: "retry"; label: string };

export class ChipMapper {
  private readonly actions = new Map<string, ChipAction>([
    // ─── Q1: 자본금 ─────────────────────────────────────
    ["budget_under_1", { kind: "submit", raw: { budget_max: 50000000 }, label: "1억 미만" }],
    ["budget_1_3", { kind: "submit", raw: { budget_max: 200000000 }, label: "1-3억" }],
    ["budget_3_5", { kind: "submit", raw: { budget_max: 400000000 }, label: "3-5억" }],
    ["budget_5_above", { kind: "submit", raw: { budget_max: 700000000 }, label: "5억 이상" }],

    // ─── Q2: 거래 유형 ──────────────────────────────────
    ["deal_jeonse", { kind: "submit", raw: { deal_type: "jeonse" }, label: "전세" }],
    ["deal_monthly_rent", { kind: "submit", raw: { deal_type: "monthly_rent" }, label: "월세" }],
    ["deal_sale", { kind: "submit", raw: { deal_type: "sale" }, label: "매매" }],

    // ─── Q3: 통근 목적지 ─────────────────────────────────
    ["commute_gangnam", { kind: "submit", raw: { commute_destination: "gangnam" }, label: "강남" }],
    ["commute_yeouido", { kind: "submit", raw: { commute_destination: "yeouido" }, label: "여의도" }],
    ["commute_gwanghwamun", { kind: "submit", raw: { commute_destination: "gwanghwamun" }, label: "광화문" }],
    ["commute_hongdae", { kind: "submit", raw: { commute_destination: "hongdae" }, label: "홍대" }],
    ["commute_jamsil", { kind: "submit", raw: { commute_destination: "jamsil" }, label: "잠실" }],
    ["commute_skip", { kind: "submit", raw: { commute_skipped: true }, label: "상관없어요" }],

    // ─── 액션 (값 매핑 없음) ────────────────────────────
    ["restart", { kind: "restart", label: "다시 추천" }],
    ["budget_restart", { kind: "restart", label: "자본금 다시" }],
    ["retry", { kind: "retry", label: "재시도" }],
  ]);

  getAction(chipId: string): ChipAction {
    const action = this.actions.get(chipId);

    if (!action) {
      throw new Error(`Unsupported quick reply chip: ${chipId}`);
    }

    return action;
  }
}
