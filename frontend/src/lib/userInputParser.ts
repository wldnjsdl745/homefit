import type { ChatRequest, Conditions } from "../types/chat";

export type ParsedUserInput = Pick<ChatRequest, "raw" | "raw_message">;

export class UserInputParser {
  parse(current: Conditions, input: string): ParsedUserInput {
    const normalized = input.trim();

    if (!current.budget_max) {
      return this.parseBudgetTurn(normalized);
    }

    if (!current.deal_type) {
      return this.parseDealTypeTurn(normalized);
    }

    return {
      raw: { preference_text: normalized },
      raw_message: normalized,
    };
  }

  private parseBudgetTurn(input: string): ParsedUserInput {
    const amount = this.parseKoreanAmount(input);
    if (amount !== null) {
      return { raw: { budget_max: amount }, raw_message: input };
    }
    return { raw: {}, raw_message: input };
  }

  private parseKoreanAmount(input: string): number | null {
    // 순수 숫자 (원 단위)
    if (/^\d+$/.test(input)) {
      return Number(input);
    }
    // "2억", "2억5000만" 등 — 억 포함 (만 선택)
    const eokMatch = input.match(/(\d+(?:\.\d+)?)\s*억(?:\s*(\d+(?:\.\d+)?)\s*만)?/);
    if (eokMatch) {
      const eok = parseFloat(eokMatch[1]) * 100_000_000;
      const man = eokMatch[2] ? parseFloat(eokMatch[2]) * 10_000 : 0;
      return eok + man;
    }
    // "5000만" 등 — 만 단독
    const manMatch = input.match(/(\d+(?:\.\d+)?)\s*만/);
    if (manMatch) {
      return parseFloat(manMatch[1]) * 10_000;
    }
    return null;
  }

  private parseDealTypeTurn(input: string): ParsedUserInput {
    if (input === "전세") {
      return { raw: { deal_type: "jeonse" }, raw_message: input };
    }
    if (input === "월세") {
      return { raw: { deal_type: "monthly_rent" }, raw_message: input };
    }
    if (input === "매매") {
      return { raw: { deal_type: "sale" }, raw_message: input };
    }
    return { raw: {}, raw_message: input };
  }
}
