import { describe, expect, it } from "vitest";
import { ChipMapper } from "./chipMapper";

describe("ChipMapper", () => {
  it("maps budget chips to raw conditions", () => {
    const mapper = new ChipMapper();

    expect(mapper.getAction("budget_1_3")).toEqual({
      kind: "submit",
      raw: { budget_max: 200000000 },
      label: "1-3억",
    });
  });

  it("maps restart chip to restart action", () => {
    const mapper = new ChipMapper();

    expect(mapper.getAction("restart")).toEqual({
      kind: "restart",
      label: "다시 추천",
    });
  });
});
