import type { LetteringObject } from "@/services/layout-api";
import { cn } from "@/lib/utils";

const FONT_CLASS: Record<LetteringObject["font_size"], string> = {
  sm: "text-[11px] leading-snug",
  md: "text-[13px] leading-snug",
  lg: "text-[15px] leading-snug",
};

const TAIL_CLASS: Record<Exclude<LetteringObject["tail"], "none">, string> = {
  bottom_left: "left-[28%] -bottom-[9px] border-r-2 border-b-2",
  bottom_right: "right-[28%] -bottom-[9px] border-r-2 border-b-2",
  top_left: "left-[28%] -top-[9px] border-l-2 border-t-2",
  top_right: "right-[28%] -top-[9px] border-l-2 border-t-2",
};

/** Draft dialogue placeholder when a panel has no Lettering yet (LETTER-03). */
export function DialogueFallbackBubble({
  text,
  alignRight,
}: {
  text: string;
  alignRight?: boolean;
}) {
  if (!text.trim()) return null;
  return (
    <div
      className={cn(
        "absolute top-[5%] max-w-[62%] rounded-[1.25rem] border-2 border-dashed border-neutral-500/80 bg-white/90 px-3 py-1.5 text-center text-[13px] leading-snug font-bold text-neutral-800 shadow-sm",
        alignRight ? "right-[4%]" : "left-[4%]",
      )}
      title="分镜对白占位 · 未落成字效"
    >
      <span className="mb-0.5 block text-[10px] font-medium tracking-wide text-neutral-500">
        未落成字效
      </span>
      <span className="line-clamp-3">{text}</span>
    </div>
  );
}

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
        const tail = item.tail !== "none" ? TAIL_CLASS[item.tail] : null;
        return (
          <div
            key={item.id}
            className={cn(
              "absolute box-border px-3 py-1.5 font-bold text-neutral-900 shadow-md",
              FONT_CLASS[item.font_size],
              bubble
                ? "rounded-[1.25rem] border-2 border-neutral-900 bg-white text-center"
                : "rounded-sm border border-neutral-800/80 bg-white/95 font-semibold",
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
            {bubble && tail ? (
              <span
                aria-hidden
                className={cn(
                  "absolute size-4 rotate-45 border-neutral-900 bg-white",
                  tail,
                )}
              />
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
