import type { ReactNode } from "react";

/** The two device widths every screen is shown at (spec D20). */
export const frameWidths = { phone: 390, desktop: 1280 } as const;

const desktopScale = 0.625;

/** Props for `Frame`. */
export interface FrameProps {
  readonly device: keyof typeof frameWidths;
  readonly children: ReactNode;
}

/**
 * A fixed-width stage for one view. The view lays out by its container width, so the frame's width is the
 * width it sees. The desktop frame is drawn at 62.5% so a phone and a desktop frame sit side by side.
 */
export function Frame({ device, children }: FrameProps) {
  const width = frameWidths[device];
  const scaled = device === "desktop";
  return (
    <figure
      className="flex min-w-0 flex-col gap-2"
      style={{ width: scaled ? width * desktopScale : width, maxWidth: "100%" }}
    >
      <figcaption className="text-caption text-ink-muted tabular-nums">
        {scaled
          ? `Desktop · ${String(width)}px, shown at ${String(desktopScale * 100)}%`
          : `Phone · ${String(width)}px`}
      </figcaption>
      <div className="overflow-x-auto rounded-sheet border border-rule-strong">
        <div className="bg-canvas" style={scaled ? { width, zoom: desktopScale } : undefined}>
          {children}
        </div>
      </div>
    </figure>
  );
}
