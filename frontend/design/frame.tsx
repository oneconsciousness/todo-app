import { type ReactNode, type RefObject, useLayoutEffect, useRef, useState } from "react";

/** The two device widths every screen is shown at: a phone and a desktop. */
export const frameWidths = { phone: 390, desktop: 1280 } as const;

const fallbackScale = 0.6;

/** Track an element's content width as the page resizes. */
const useWidth = (): [RefObject<HTMLElement | null>, number] => {
  const ref = useRef<HTMLElement>(null);
  const [width, setWidth] = useState(0);
  useLayoutEffect(() => {
    const element = ref.current;
    if (!element) return undefined;
    const observer = new ResizeObserver(([entry]) => {
      setWidth(entry?.contentRect.width ?? 0);
    });
    observer.observe(element);
    return () => {
      observer.disconnect();
    };
  }, []);
  return [ref, width];
};

/** Props for `Frame`. */
export interface FrameProps {
  readonly device: keyof typeof frameWidths;
  readonly children: ReactNode;
}

/**
 * A fixed-width stage for one view. The view lays out by its container's width, so the frame's width is the width
 * it sees. A phone frame is drawn at full size (narrower only when the page is); a desktop frame is laid out at
 * 1280px and scaled to fit its column, so nothing is clipped at any page width.
 */
export function Frame({ device, children }: FrameProps) {
  const [ref, available] = useWidth();
  const width = frameWidths[device];
  const desktop = device === "desktop";
  const scale = available > 0 ? Math.min(1, available / width) : fallbackScale;
  return (
    <figure
      ref={ref}
      className="flex min-w-0 flex-col gap-2"
      style={desktop ? { flex: "1 1 20rem" } : { width, maxWidth: "100%" }}
    >
      <figcaption className="text-caption text-ink-muted tabular-nums">
        {desktop
          ? `Desktop · ${String(width)}px, shown at ${String(Math.round(scale * 100))}%`
          : `Phone · ${String(width)}px`}
      </figcaption>
      <div className="overflow-hidden rounded-sheet border border-rule-strong bg-canvas">
        <div style={desktop ? { width, zoom: scale } : undefined}>{children}</div>
      </div>
    </figure>
  );
}
