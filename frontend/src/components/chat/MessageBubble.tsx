import type { ChatMessage } from "../../types/chat";
import { QuickReplyChips } from "./QuickReplyChips";

type MessageBubbleProps = {
  message: ChatMessage;
  onChipClick?: (chipId: string) => void;
  chipsDisabled?: boolean;
};

export function MessageBubble({ message, onChipClick, chipsDisabled }: MessageBubbleProps) {
  const isUser = message.role === "user";

  if (isUser) {
    return (
      <div className="flex items-end justify-end gap-3">
        <div className="max-w-[88%] border border-neutral-300 bg-[#f7f7f3] px-4 py-3 text-[15px] leading-7 text-ink sm:max-w-[76%]">
          {message.label}
        </div>
        <div
          className="mb-1 flex size-8 shrink-0 items-center justify-center border border-neutral-300 bg-paper text-[10px] font-black text-muted"
          aria-hidden="true"
        >
          ME
        </div>
      </div>
    );
  }

  if (message.body.type === "bot.text") {
    return (
      <div className="flex items-end justify-start gap-3">
        <div
          className="mb-1 flex size-8 shrink-0 items-center justify-center border border-neutral-300 bg-paper text-[10px] font-black text-muted"
          aria-hidden="true"
        >
          AI
        </div>
        <div className="max-w-[88%] border border-neutral-200 bg-paper px-4 py-3 text-[15px] leading-7 text-ink sm:max-w-[76%]">
          {message.body.content}
        </div>
      </div>
    );
  }

  if (message.body.type === "bot.quick_replies") {
    return (
      <QuickReplyChips
        chips={message.body.chips}
        disabled={chipsDisabled ?? false}
        onChipClick={onChipClick ?? (() => {})}
      />
    );
  }

  return null;
}
