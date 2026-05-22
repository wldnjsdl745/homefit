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
    if (/^\d+$/.test(input)) {
      return { raw: { budget_max: Number(input) }, raw_message: input };
    }

    return { raw: {}, raw_message: input };
  }

  private parseDealTypeTurn(input: string): ParsedUserInput {
    if (input === "전세") {
      return { raw: { deal_type: "jeonse" }, raw_message: input };
    }

    if (input === "월세") {
      return { raw: { deal_type: "monthly_rent" }, raw_message: input };
    }

    return { raw: {}, raw_message: input };
  }
}
