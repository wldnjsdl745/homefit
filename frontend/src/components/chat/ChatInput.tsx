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
      className="sticky bottom-0 mt-4 flex gap-3 border-t-[3px] border-ink bg-cream py-4"
    >
      <label className="sr-only" htmlFor="chat-input">
        채팅 입력
      </label>
      <input
        id="chat-input"
        value={value}
        disabled={disabled}
        onChange={(event) => setValue(event.target.value)}
        className="min-h-12 flex-1 border-[3px] border-ink bg-paper px-4 text-[15px] text-ink shadow-pixel-sm outline-none transition placeholder:text-muted focus:bg-cream focus:shadow-pixel disabled:cursor-not-allowed disabled:bg-sand"
        placeholder="예: 200000000 또는 전세"
        autoComplete="off"
      />
      <button
        type="submit"
        disabled={disabled || value.trim().length === 0}
        className="btn-pixel inline-flex size-12 items-center justify-center border-[3px] border-ink bg-coral text-cream shadow-pixel-sm transition hover:bg-mustard hover:text-ink focus:outline-none focus:ring-2 focus:ring-mustard disabled:cursor-not-allowed disabled:bg-sand disabled:text-muted"
        aria-label="전송"
        title="전송"
      >
        ▶
      </button>
    </form>
  );
}
