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
    <div className="flex min-h-0 flex-1 flex-col py-5 sm:py-6">
      <div className="flex-1 space-y-4 overflow-y-auto pr-1" aria-live="polite">
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}

        {isWaiting ? (
          <div className="flex justify-start">
            <div className="flex items-center gap-2 border border-ink bg-paper px-4 py-3 text-sm text-muted">
              <span className="size-2 animate-pulse bg-ink" />
              생각 중
            </div>
          </div>
        ) : null}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
