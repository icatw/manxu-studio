import { useEffect, useRef, useState } from "react";
import type { LetteringObject } from "@/services/layout-api";
import { clampLetteringPosition, clientDeltaToPct } from "@/lib/lettering-geometry";
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

type DragState = {
  id: string;
  originX: number;
  originY: number;
  startClientX: number;
  startClientY: number;
  widthPct: number;
  currentX: number;
  currentY: number;
  moved: boolean;
};

/** Draft dialogue placeholder when a panel has no Lettering yet (LETTER-03). */
export function DialogueFallbackBubble({
  text,
  alignRight,
}: {
  text: string;
  alignRight?: boolean;
}) {
  const trimmed = text.trim();
  // Don't surface shell placeholders as "draft dialogue" on canvas/preview.
  if (!trimmed || trimmed === "无对白" || trimmed === "无对白。" || trimmed === "无旁白" || trimmed === "无旁白。") {
    return null;
  }
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
      <span className="line-clamp-3">{trimmed}</span>
    </div>
  );
}

export function LetteringOverlay({
  items,
  interactive,
  draggable,
  selectedId,
  onSelect,
  onPositionCommit,
}: {
  items: LetteringObject[];
  interactive?: boolean;
  /** Desktop pointer drag to change x_pct/y_pct (LETTER-06). Requires interactive. */
  draggable?: boolean;
  selectedId?: string | null;
  onSelect?: (id: string) => void;
  onPositionCommit?: (id: string, position: { x_pct: number; y_pct: number }) => void;
}) {
  const layerRef = useRef<HTMLDivElement>(null);
  const dragRef = useRef<DragState | null>(null);
  const [livePositions, setLivePositions] = useState<
    Record<string, { x_pct: number; y_pct: number }>
  >({});

  useEffect(() => {
    setLivePositions((prev) => {
      let changed = false;
      const next = { ...prev };
      for (const item of items) {
        const live = next[item.id];
        if (!live) continue;
        if (
          Math.abs(live.x_pct - item.x_pct) < 0.25 &&
          Math.abs(live.y_pct - item.y_pct) < 0.25
        ) {
          delete next[item.id];
          changed = true;
        }
      }
      for (const id of Object.keys(next)) {
        if (!items.some((item) => item.id === id)) {
          delete next[id];
          changed = true;
        }
      }
      return changed ? next : prev;
    });
  }, [items]);

  if (items.length === 0) return null;

  const canDrag = Boolean(interactive && draggable && onPositionCommit);

  return (
    <div ref={layerRef} className="pointer-events-none absolute inset-0">
      {items.map((item) => {
        const selected = selectedId === item.id;
        const bubble = item.kind === "speech_bubble";
        const tail = item.tail !== "none" ? TAIL_CLASS[item.tail] : null;
        const live = livePositions[item.id];
        const xPct = live?.x_pct ?? item.x_pct;
        const yPct = live?.y_pct ?? item.y_pct;
        return (
          <div
            key={item.id}
            role={interactive ? "button" : undefined}
            tabIndex={interactive ? 0 : undefined}
            aria-label={
              interactive
                ? `${bubble ? "气泡" : "旁白"}：${item.text.slice(0, 24)}${canDrag ? "（可拖动）" : ""}`
                : undefined
            }
            className={cn(
              "absolute box-border px-3 py-1.5 font-bold text-neutral-900 shadow-md",
              FONT_CLASS[item.font_size],
              bubble
                ? "rounded-[1.25rem] border-2 border-neutral-900 bg-white text-center"
                : "rounded-sm border border-neutral-800/80 bg-white/95 font-semibold",
              interactive && "pointer-events-auto cursor-pointer",
              canDrag && "cursor-grab touch-none active:cursor-grabbing",
              selected && "ring-2 ring-primary ring-offset-1",
            )}
            style={{
              left: `${xPct}%`,
              top: `${yPct}%`,
              width: `${item.width_pct}%`,
            }}
            onClick={
              interactive && onSelect
                ? (event) => {
                    event.stopPropagation();
                    if (dragRef.current?.moved) return;
                    onSelect(item.id);
                  }
                : undefined
            }
            onPointerDown={
              canDrag
                ? (event) => {
                    if (event.button !== 0) return;
                    event.stopPropagation();
                    event.currentTarget.setPointerCapture(event.pointerId);
                    onSelect?.(item.id);
                    dragRef.current = {
                      id: item.id,
                      originX: xPct,
                      originY: yPct,
                      startClientX: event.clientX,
                      startClientY: event.clientY,
                      widthPct: item.width_pct,
                      currentX: xPct,
                      currentY: yPct,
                      moved: false,
                    };
                  }
                : undefined
            }
            onPointerMove={
              canDrag
                ? (event) => {
                    const drag = dragRef.current;
                    if (!drag || drag.id !== item.id) return;
                    const rect = layerRef.current?.getBoundingClientRect();
                    if (!rect) return;
                    const { dx, dy } = clientDeltaToPct(
                      event.clientX - drag.startClientX,
                      event.clientY - drag.startClientY,
                      rect.width,
                      rect.height,
                    );
                    if (Math.abs(dx) + Math.abs(dy) > 0.4) drag.moved = true;
                    const next = clampLetteringPosition(
                      drag.originX + dx,
                      drag.originY + dy,
                      drag.widthPct,
                    );
                    drag.currentX = next.x_pct;
                    drag.currentY = next.y_pct;
                    setLivePositions((prev) => ({ ...prev, [item.id]: next }));
                  }
                : undefined
            }
            onPointerUp={
              canDrag
                ? (event) => {
                    const drag = dragRef.current;
                    dragRef.current = null;
                    try {
                      event.currentTarget.releasePointerCapture(event.pointerId);
                    } catch {
                      /* already released */
                    }
                    if (!drag || drag.id !== item.id || !drag.moved) {
                      setLivePositions((prev) => {
                        if (!(item.id in prev)) return prev;
                        const { [item.id]: _, ...rest } = prev;
                        return rest;
                      });
                      return;
                    }
                    const next = clampLetteringPosition(
                      drag.currentX,
                      drag.currentY,
                      drag.widthPct,
                    );
                    if (
                      Math.abs(next.x_pct - item.x_pct) < 0.15 &&
                      Math.abs(next.y_pct - item.y_pct) < 0.15
                    ) {
                      setLivePositions((prev) => {
                        const { [item.id]: _, ...rest } = prev;
                        return rest;
                      });
                      return;
                    }
                    setLivePositions((prev) => ({ ...prev, [item.id]: next }));
                    onPositionCommit?.(item.id, next);
                  }
                : undefined
            }
            onPointerCancel={
              canDrag
                ? () => {
                    dragRef.current = null;
                    setLivePositions((prev) => {
                      const { [item.id]: _, ...rest } = prev;
                      return rest;
                    });
                  }
                : undefined
            }
          >
            <p className="whitespace-pre-wrap break-keep [overflow-wrap:anywhere]">{item.text}</p>
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
