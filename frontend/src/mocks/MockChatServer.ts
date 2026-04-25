import fixture from "./chat.v0.json";
import type { BotMessage, ChatRequest, ChatResponse, Conditions, DealType } from "../types/chat";

type Session = {
  conditions: Conditions;
};

export class MockChatServer {
  private readonly sessions = new Map<string, Session>();
  private sequence = 0;

  async handle(request: ChatRequest): Promise<ChatResponse> {
    await this.delay();

    const sessionId = request.session_id ?? this.createSession();
    const session = this.sessions.get(sessionId) ?? { conditions: {} };
    session.conditions = { ...session.conditions, ...request.raw };
    this.sessions.set(sessionId, session);

    if (!session.conditions.budget_max) {
      return this.response(sessionId, "asking", fixture.welcome as BotMessage[]);
    }

    if (!session.conditions.deal_type) {
      return this.response(sessionId, "asking", fixture.dealQuestion as BotMessage[]);
    }

    return this.response(
      sessionId,
      "result",
      this.resultMessages({
        budget_max: session.conditions.budget_max,
        deal_type: session.conditions.deal_type,
      }),
    );
  }

  private resultMessages(conditions: Required<Conditions>): BotMessage[] {
    if (conditions.budget_max < 60000000 && conditions.deal_type === "jeonse") {
      return fixture.empty as BotMessage[];
    }

    const dealType = this.formatDealType(conditions.deal_type);
    const budget = this.formatBudget(conditions.budget_max);
    const regions = conditions.deal_type === "jeonse" ? "분당·성남·경기도" : "봉천동·신림동·사당동";

    return [
      { type: "bot.text", content: "잠시만요..." },
      {
        type: "bot.text",
        content: `${dealType} ${budget} 예산에 맞는 지역은 ${regions}입니다.`,
      },
    ];
  }

  private response(
    sessionId: string,
    state: ChatResponse["state"],
    botMessages: BotMessage[],
  ): ChatResponse {
    return {
      session_id: sessionId,
      state,
      bot_messages: botMessages,
    };
  }

  private createSession(): string {
    this.sequence += 1;
    const sessionId = `mock_session_${this.sequence}`;
    this.sessions.set(sessionId, { conditions: {} });
    return sessionId;
  }

  private formatDealType(dealType: DealType): string {
    return dealType === "jeonse" ? "전세" : "월세";
  }

  private formatBudget(value: number): string {
    if (value >= 100000000) {
      return `${value / 100000000}억`;
    }

    return `${Math.round(value / 10000)}만원`;
  }

  private delay(): Promise<void> {
    return new Promise((resolve) => window.setTimeout(resolve, 250));
  }
}
