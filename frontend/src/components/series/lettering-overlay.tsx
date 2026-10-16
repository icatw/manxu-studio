import type { LetteringObject } from "@/services/layout-api";
import { cn } from "@/lib/utils";

const FONT_CLASS: Record<LetteringObject["font_size"], string> = {
  sm: "text-[11px] leading-snug",
  md: "text-[13px] leading-snug",
  lg: "text-[15px] leading-snug",
};

export function LetteringOverlay({
  items,
  interactive,
  selectedId,
  onSelect,
}: {
  items: LetteringObject[];
  interactive?: boolean;
  selectedId?: string | null;
  onSelect?: (id: string) => void;
}) {
  if (items.length === 0) return null;
  return (
    <div className="pointer-events-none absolute inset-0">
      {items.map((item) => {
        const selected = selectedId === item.id;
        const bubble = item.kind === "speech_bubble";
        return (
          <div
            key={item.id}
            className={cn(
              "absolute box-border px-2 py-1.5 text-neutral-900 shadow-sm",
              FONT_CLASS[item.font_size],
              bubble
                ? "rounded-2xl border-[2.5px] border-neutral-900 bg-white"
                : "rounded-sm border border-neutral-800/80 bg-white/95",
              interactive && "pointer-events-auto cursor-pointer",
              selected && "ring-2 ring-primary ring-offset-1",
            )}
            style={{
              left: `${item.x_pct}%`,
              top: `${item.y_pct}%`,
              width: `${item.width_pct}%`,
            }}
            onClick={
              interactive && onSelect
                ? (event) => {
                    event.stopPropagation();
                    onSelect(item.id);
                  }
                : undefined
            }
          >
            <p className="whitespace-pre-wrap break-words">{item.text}</p>
          </div>
        );
      })}
    </div>
  );
}
