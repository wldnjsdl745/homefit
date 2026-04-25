import type { ChatMessage } from "../../types/chat";

type MessageBubbleProps = {
  message: ChatMessage;
};

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const content = isUser ? message.label : message.body.type === "bot.text" ? message.body.content : "";

  if (!content) {
    return null;
  }

  return (
    <div className={`flex items-end gap-3 ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser ? (
        <div
          className="mb-1 flex size-8 shrink-0 items-center justify-center border border-neutral-300 bg-paper text-[10px] font-black text-muted"
          aria-hidden="true"
        >
          AI
        </div>
      ) : null}
      <div
        className={`max-w-[88%] border px-4 py-3 text-[15px] leading-7 sm:max-w-[76%] ${
          isUser
            ? "border-neutral-300 bg-[#f7f7f3] text-ink"
            : "border-neutral-200 bg-paper text-ink"
        }`}
      >
        {content}
      </div>
      {isUser ? (
        <div
          className="mb-1 flex size-8 shrink-0 items-center justify-center border border-neutral-300 bg-paper text-[10px] font-black text-muted"
          aria-hidden="true"
        >
          ME
        </div>
      ) : null}
    </div>
  );
}
