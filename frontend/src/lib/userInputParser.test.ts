import { describe, expect, it } from "vitest";
import { UserInputParser } from "./userInputParser";

describe("UserInputParser", () => {
  it("parses first numeric input as budget_max", () => {
    const parser = new UserInputParser();

    expect(parser.parse({}, "200000000")).toEqual({ budget_max: 200000000 });
  });

  it("parses deal type after budget is present", () => {
    const parser = new UserInputParser();

    expect(parser.parse({ budget_max: 200000000 }, "전세")).toEqual({ deal_type: "jeonse" });
    expect(parser.parse({ budget_max: 200000000 }, "월세")).toEqual({
      deal_type: "monthly_rent",
    });
  });
});
