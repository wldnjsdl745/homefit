import type { ChatMessage } from "../../types/chat";

type MessageBubbleProps = {
  message: ChatMessage;
};

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const content = isUser
    ? message.label
    : message.body.type === "bot.text"
      ? message.body.content
      : "";

  if (!content) {
    return null;
  }

  return (
    <div className={`flex items-end gap-3 ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser ? (
        <div
          className="mb-1 flex size-9 shrink-0 items-center justify-center border-[3px] border-ink bg-mint text-sm text-ink shadow-pixel-sm"
          aria-hidden="true"
        >
          ▲
        </div>
      ) : null}
      <div
        className={`max-w-[88%] border-[3px] border-ink px-4 py-3 text-[15px] leading-7 shadow-pixel-sm sm:max-w-[76%] ${
          isUser ? "bg-coral text-cream" : "bg-paper text-ink"
        }`}
      >
        {content}
      </div>
      {isUser ? (
        <div
          className="mb-1 flex size-9 shrink-0 items-center justify-center border-[3px] border-ink bg-mustard text-sm text-ink shadow-pixel-sm"
          aria-hidden="true"
        >
          ●
        </div>
      ) : null}
    </div>
  );
}
