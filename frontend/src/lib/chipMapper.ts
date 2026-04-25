import type { Conditions } from "../types/chat";

export type ChipAction =
  | { kind: "submit"; raw: Conditions; label: string }
  | { kind: "restart"; label: string }
  | { kind: "retry"; label: string };

export class ChipMapper {
  private readonly actions = new Map<string, ChipAction>([
    ["budget_under_1", { kind: "submit", raw: { budget_max: 50000000 }, label: "1억 미만" }],
    ["budget_1_3", { kind: "submit", raw: { budget_max: 200000000 }, label: "1-3억" }],
    ["budget_3_5", { kind: "submit", raw: { budget_max: 400000000 }, label: "3-5억" }],
    ["budget_5_above", { kind: "submit", raw: { budget_max: 700000000 }, label: "5억 이상" }],
    ["deal_jeonse", { kind: "submit", raw: { deal_type: "jeonse" }, label: "전세" }],
    ["deal_monthly_rent", { kind: "submit", raw: { deal_type: "monthly_rent" }, label: "월세" }],
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
