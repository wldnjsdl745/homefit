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

    // 출퇴근 단계: workplace가 아직 없으면 그대로 담아 전송 (AI 서버가 매핑)
    if (current.workplace === undefined) {
      return { raw: { workplace: normalized }, raw_message: normalized };
    }

    // 월세 단계: 금액 사전 파싱
    if (current.deal_type === "monthly_rent" && !current.monthly_rent_max) {
      return this.parseMonthlyRentTurn(normalized);
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

  private parseMonthlyRentTurn(input: string): ParsedUserInput {
    const amount = this.parseKoreanAmount(input);
    if (amount !== null) {
      return { raw: { monthly_rent_max: amount }, raw_message: input };
    }
    return { raw: {}, raw_message: input };
  }

  private parseDealTypeTurn(input: string): ParsedUserInput {
    // 월세가 포함되면 우선 월세 (전세보다 먼저 체크 — "전세 말고 월세" 대응)
    if (input.includes("월세")) {
      return { raw: { deal_type: "monthly_rent" }, raw_message: input };
    }
    if (input.includes("전세")) {
      return { raw: { deal_type: "jeonse" }, raw_message: input };
    }
    if (input.includes("매매") || input.includes("구매") || input.includes("분양")) {
      return { raw: { deal_type: "sale" }, raw_message: input };
    }
    return { raw: {}, raw_message: input };
  }
}
