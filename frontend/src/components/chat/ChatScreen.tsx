import { useChat } from "../../hooks/useChat";
import { ChatInput } from "./ChatInput";
import { MessageList } from "./MessageList";

export function ChatScreen() {
  const { messages, isWaiting, submitText, restart } = useChat();

  return (
    <main className="min-h-screen bg-cream font-pixel text-ink">
      {/* 도트 그리드 배경 */}
      <div className="pointer-events-none fixed inset-0 bg-dot-grid" />
      {/* 스캔라인 (선택) */}
      <div className="pointer-events-none fixed inset-0 bg-scanlines" />

      <header className="sticky top-0 z-10 border-b-[3px] border-ink bg-ink text-cream">
        <div className="mx-auto flex h-20 max-w-[760px] items-center justify-between px-4">
          <div className="flex items-center gap-3">
            {/* 픽셀 아트 로고 (집 모양) */}
            <div
              className="flex size-12 items-center justify-center border-[3px] border-cream bg-coral"
              aria-hidden="true"
            >
              <PixelHouse />
            </div>
            <div className="leading-none">
              <span className="block text-xl tracking-widest">HOMEFIT</span>
              <span className="mt-2 block text-[11px] text-mustard">
                AI HOUSING CHAT
              </span>
            </div>
          </div>
          <button
            type="button"
            onClick={() => void restart()}
            className="btn-pixel border-[3px] border-cream bg-mint px-3 py-2 text-xs text-ink shadow-pixel-sm transition hover:bg-mustard focus:outline-none focus:ring-2 focus:ring-mustard"
            aria-label="새 대화"
            title="새 대화"
          >
            ↻ 다시
          </button>
        </div>
      </header>

      <section className="relative mx-auto flex min-h-[calc(100vh-5rem)] max-w-[760px] flex-col px-4">
        <MessageList messages={messages} isWaiting={isWaiting} />
        <ChatInput disabled={isWaiting} onSubmit={submitText} />
      </section>
    </main>
  );
}

/** 8x8 픽셀 아트 집 (SVG로 픽셀 그리드 표현) */
function PixelHouse() {
  // 1 = 본체(cream), 2 = 지붕(mustard), 3 = 문(ink)
  const grid = [
    [0, 0, 0, 2, 2, 0, 0, 0],
    [0, 0, 2, 2, 2, 2, 0, 0],
    [0, 2, 2, 2, 2, 2, 2, 0],
    [2, 2, 2, 2, 2, 2, 2, 2],
    [0, 1, 1, 1, 1, 1, 1, 0],
    [0, 1, 1, 3, 3, 1, 1, 0],
    [0, 1, 1, 3, 3, 1, 1, 0],
    [0, 1, 1, 3, 3, 1, 1, 0],
  ];
  const colors: Record<number, string> = {
    1: "#f4ecd0",
    2: "#f9a826",
    3: "#1a1d2e",
  };
  return (
    <svg
      viewBox="0 0 8 8"
      width="28"
      height="28"
      shapeRendering="crispEdges"
      aria-hidden="true"
    >
      {grid.map((row, y) =>
        row.map((cell, x) =>
          cell ? (
            <rect
              key={`${x}-${y}`}
              x={x}
              y={y}
              width={1}
              height={1}
              fill={colors[cell]}
            />
          ) : null,
        ),
      )}
    </svg>
  );
}
