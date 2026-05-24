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
    // "2억", "2억5000만", "5000만" 등 한국어 금액
    const match = input.match(/(?:(\d+(?:\.\d+)?)\s*억)?\s*(?:(\d+(?:\.\d+)?)\s*만)?/);
    if (match && (match[1] || match[2])) {
      const eok = parseFloat(match[1] ?? "0") * 100_000_000;
      const man = parseFloat(match[2] ?? "0") * 10_000;
      const total = eok + man;
      return total > 0 ? total : null;
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
