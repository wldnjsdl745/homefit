export function Loading() {
  return (
    <span className="font-pixel text-sm text-ink">
      <span className="inline-flex items-center gap-1">
        불러오는 중
        <span className="inline-flex gap-0.5">
          <span className="size-1.5 animate-bounce bg-coral" />
          <span
            className="size-1.5 animate-bounce bg-coral"
            style={{ animationDelay: "150ms" }}
          />
          <span
            className="size-1.5 animate-bounce bg-coral"
            style={{ animationDelay: "300ms" }}
          />
        </span>
      </span>
    </span>
  );
}
