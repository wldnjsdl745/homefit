import type { QuickReplyChip } from "../../types/chat";

type QuickReplyChipsProps = {
  chips: QuickReplyChip[];
  disabled: boolean;
  onChipClick: (chipId: string) => void | Promise<void>;
};

export function QuickReplyChips({ chips, disabled, onChipClick }: QuickReplyChipsProps) {
  return (
    <div className="flex flex-wrap gap-3 pl-0 sm:pl-12">
      {chips.map((chip) => (
        <button
          key={chip.id}
          type="button"
          disabled={disabled}
          onClick={() => void onChipClick(chip.id)}
          className="btn-pixel min-h-11 border-[3px] border-ink bg-paper px-4 py-2 text-sm text-ink shadow-pixel-sm transition hover:bg-mustard focus:outline-none focus:ring-2 focus:ring-coral disabled:cursor-not-allowed disabled:opacity-50"
        >
          {chip.label}
        </button>
      ))}
    </div>
  );
}
