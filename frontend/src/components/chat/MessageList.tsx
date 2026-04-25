import { useEffect, useRef } from "react";
import type { ChatMessage } from "../../types/chat";
import { MessageBubble } from "./MessageBubble";

type MessageListProps = {
  messages: ChatMessage[];
  isWaiting: boolean;
};

export function MessageList({ messages, isWaiting }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages.length, isWaiting]);

  return (
    <div className="flex flex-1 flex-col py-6 sm:py-8">
      <div className="flex-1 space-y-4" aria-live="polite">
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}

        {isWaiting ? (
          <div className="flex items-end gap-3">
            <div
              className="mb-1 flex size-9 shrink-0 items-center justify-center border-[3px] border-ink bg-mint text-sm text-ink shadow-pixel-sm"
              aria-hidden="true"
            >
              ▲
            </div>
            <div className="border-[3px] border-ink bg-paper px-4 py-3 text-sm text-ink shadow-pixel-sm">
              <span className="inline-flex items-center gap-1">
                <Dot delay={0} />
                <Dot delay={150} />
                <Dot delay={300} />
              </span>
            </div>
          </div>
        ) : null}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}

function Dot({ delay }: { delay: number }) {
  return (
    <span
      className="size-2 animate-bounce bg-coral"
      style={{ animationDelay: `${delay}ms` }}
    />
  );
}
