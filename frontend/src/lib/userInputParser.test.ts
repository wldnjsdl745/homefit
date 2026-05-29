import { describe, expect, it } from "vitest";
import { UserInputParser } from "./userInputParser";

describe("UserInputParser", () => {
  it("parses first numeric input as budget_max", () => {
    const parser = new UserInputParser();

    expect(parser.parse({}, "200000000")).toEqual({
      raw: { budget_max: 200000000 },
    });
  });

  it("parses deal type after budget is present", () => {
    const parser = new UserInputParser();

    expect(parser.parse({ budget_max: 200000000 }, "전세")).toEqual({
      raw: { deal_type: "jeonse" },
    });
    expect(parser.parse({ budget_max: 200000000 }, "월세")).toEqual({
      raw: { deal_type: "monthly_rent" },
    });
    expect(parser.parse({ budget_max: 200000000 }, "매매")).toEqual({
      raw: { deal_type: "sale" },
    });
  });

  it("passes natural language as raw_message", () => {
    const parser = new UserInputParser();

    expect(parser.parse({}, "2억 정도 있어요")).toEqual({
      raw: { budget_max: 200000000 },
      raw_message: "2억 정도 있어요",
    });
  });

  it("parses monthly rent before commute", () => {
    const parser = new UserInputParser();

    expect(parser.parse({ budget_max: 200000000, deal_type: "monthly_rent" }, "500000")).toEqual({
      raw: { monthly_rent_max: 500000 },
    });
  });

  it("parses preferred region before commute", () => {
    const parser = new UserInputParser();

    expect(parser.parse({ budget_max: 200000000, deal_type: "jeonse" }, "강남구")).toEqual({
      raw: { preferred_region: "강남구" },
      raw_message: "강남구",
    });
  });

  it("parses commute after preferred region is present", () => {
    const parser = new UserInputParser();

    expect(
      parser.parse(
        { budget_max: 200000000, deal_type: "jeonse", preferred_region: "강남구" },
        "논현",
      ),
    ).toEqual({
      raw: { workplace: "논현" },
      raw_message: "논현",
    });
  });

  it("stores preference text after budget and deal type", () => {
    const parser = new UserInputParser();

    expect(
      parser.parse(
        {
          budget_max: 200000000,
          deal_type: "jeonse",
          preferred_region: "상관없음",
          workplace: "상관없음",
        },
        "역 가까운 곳",
      ),
    ).toEqual({
      raw: { preference_text: "역 가까운 곳" },
      raw_message: "역 가까운 곳",
    });
  });
});
