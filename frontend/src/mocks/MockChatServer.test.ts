import { describe, expect, it } from "vitest";
import { MockChatServer } from "./MockChatServer";

describe("MockChatServer", () => {
  it("runs the v0 welcome, deal question, and result flow", async () => {
    const server = new MockChatServer();

    const welcome = await server.handle({ session_id: null, raw: {} });
    expect(welcome.state).toBe("asking");
    expect(welcome.bot_messages).toEqual([
      { type: "bot.text", content: "먼저 자본금이 어느 정도인지 알려주세요." },
    ]);

    const dealQuestion = await server.handle({
      session_id: welcome.session_id,
      raw: { budget_max: 200000000 },
    });
    expect(dealQuestion.state).toBe("asking");
    expect(dealQuestion.bot_messages[0]).toEqual({
      type: "bot.text",
      content: "전세/월세 중 어떤 걸 원하시는지 알려주세요.",
    });

    const result = await server.handle({
      session_id: welcome.session_id,
      raw: { deal_type: "jeonse" },
    });
    expect(result.state).toBe("result");
    expect(JSON.stringify(result.bot_messages)).toContain("분당·성남·경기도");
  });
});
