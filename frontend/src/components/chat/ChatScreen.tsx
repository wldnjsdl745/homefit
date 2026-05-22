import { useChat } from "../../hooks/useChat";
import { ChatInput } from "./ChatInput";
import { MessageList } from "./MessageList";

export function ChatScreen() {
  const { messages, isWaiting, submitText } = useChat();

  return (
    <main className="min-h-screen bg-paper text-ink">
      <div className="pointer-events-none fixed inset-0 bg-editorial-grid opacity-70" />

      <header className="relative z-10 border-b border-ink bg-paper">
        <div className="mx-auto flex h-16 max-w-6xl items-center px-5">
          <a className="text-[13px] font-semibold tracking-[0.32em]" href="/">
            HOMEFIT
          </a>
        </div>
      </header>

      <section className="relative z-10 mx-auto grid min-h-[calc(100vh-4rem)] max-w-6xl grid-rows-[auto_1fr] px-5 py-7 sm:py-10">
        <div className="border-b border-ink pb-7">
          <div>
            <p className="mb-4 text-[12px] font-semibold uppercase tracking-[0.22em] text-muted">
              Ask Homefit anything
            </p>
            <h1 className="max-w-4xl text-[clamp(44px,10vw,112px)] font-black uppercase leading-[0.88] tracking-[-0.04em]">
              Find your next neighborhood.
            </h1>
          </div>
        </div>

        <div className="mx-auto grid min-h-0 w-full max-w-3xl pt-6">
          <div className="flex min-h-[560px] flex-col border border-neutral-300 bg-paper shadow-soft">
            <div className="flex h-10 items-center justify-between border-b border-neutral-200 px-4">
              <span className="text-[12px] font-semibold uppercase tracking-[0.18em] text-muted">Chat</span>
              <span className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted">
                {isWaiting ? "Thinking" : "Ready"}
              </span>
            </div>
            <div className="flex min-h-0 flex-1 flex-col px-4 sm:px-6">
              <MessageList messages={messages} isWaiting={isWaiting} />
              <ChatInput disabled={isWaiting} onSubmit={submitText} />
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
