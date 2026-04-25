import { type FormEvent, useState } from "react";

type ChatInputProps = {
  disabled: boolean;
  onSubmit: (value: string) => void | Promise<void>;
};

export function ChatInput({ disabled, onSubmit }: ChatInputProps) {
  const [value, setValue] = useState("");

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const nextValue = value.trim();

    if (!nextValue || disabled) {
      return;
    }

    setValue("");
    void onSubmit(nextValue);
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="sticky bottom-0 mt-4 flex gap-3 border-t border-neutral-200 bg-paper py-4"
    >
      <label className="sr-only" htmlFor="chat-input">
        채팅 입력
      </label>
      <input
        id="chat-input"
        value={value}
        disabled={disabled}
        onChange={(event) => setValue(event.target.value)}
        className="min-h-12 flex-1 border border-neutral-300 bg-paper px-4 text-[15px] text-ink outline-none transition placeholder:text-muted focus:border-ink focus:bg-[#f7f7f3] disabled:cursor-not-allowed disabled:bg-[#eeeeea]"
        placeholder="Ask me anything... 예: 200000000 또는 전세"
        autoComplete="off"
      />
      <button
        type="submit"
        disabled={disabled || value.trim().length === 0}
        className="inline-flex h-12 min-w-24 items-center justify-center border border-neutral-300 bg-paper px-4 text-[12px] font-semibold uppercase tracking-[0.14em] text-ink transition hover:border-ink hover:bg-[#f7f7f3] focus:outline-none focus:ring-2 focus:ring-ink focus:ring-offset-2 disabled:cursor-not-allowed disabled:border-neutral-200 disabled:bg-[#eeeeea] disabled:text-muted"
        aria-label="전송"
        title="전송"
      >
        Send
      </button>
    </form>
  );
}
