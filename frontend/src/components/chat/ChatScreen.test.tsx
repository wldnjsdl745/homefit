import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ChatScreen } from "./ChatScreen";

describe("ChatScreen", () => {
  it("renders the mock v0 chat flow", async () => {
    render(<ChatScreen />);

    expect(await screen.findByText("먼저 자본금이 어느 정도인지 알려주세요.")).toBeInTheDocument();

    const input = screen.getByLabelText("채팅 입력");

    fireEvent.change(input, { target: { value: "200000000" } });
    fireEvent.click(screen.getByRole("button", { name: "전송" }));

    expect(await screen.findByText("전세/월세 중 어떤 걸 원하시는지 알려주세요.")).toBeInTheDocument();

    fireEvent.change(input, { target: { value: "전세" } });
    fireEvent.click(screen.getByRole("button", { name: "전송" }));

    expect(await screen.findByText("추가로 희망하시는 조건이 있나요?")).toBeInTheDocument();

    fireEvent.change(input, { target: { value: "역 가까운 곳" } });
    fireEvent.click(screen.getByRole("button", { name: "전송" }));

    await waitFor(() => {
      expect(screen.getByText("전세 2억 예산에 맞는 지역은 분당·성남·경기도입니다.")).toBeInTheDocument();
    });
  });
});
