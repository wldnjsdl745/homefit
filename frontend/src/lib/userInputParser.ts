import type { Conditions } from "../types/chat";

export class UserInputParser {
  parse(current: Conditions, input: string): Conditions {
    const normalized = input.trim();

    if (!current.budget_max) {
      return { budget_max: this.parseBudget(normalized) };
    }

    if (!current.deal_type) {
      return { deal_type: this.parseDealType(normalized) };
    }

    return { budget_max: this.parseBudget(normalized) };
  }

  private parseBudget(input: string): number {
    if (!/^\d+$/.test(input)) {
      throw new Error("Budget input must be digits only.");
    }

    return Number(input);
  }

  private parseDealType(input: string): "jeonse" | "monthly_rent" {
    if (input === "전세") {
      return "jeonse";
    }

    if (input === "월세") {
      return "monthly_rent";
    }

    throw new Error("Deal type input must be 전세 or 월세.");
  }
}
