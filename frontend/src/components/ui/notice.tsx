import type { ReactNode } from "react";
import { Button } from "./button.tsx";
import { Icon } from "./icon.tsx";

/** A button a notice offers, such as "Try again". */
export interface NoticeAction {
  readonly label: string;
  readonly onAction: () => void;
}

/** Props for `Notice`. */
export interface NoticeProps {
  readonly tone: "alert" | "info";
  readonly children: ReactNode;
  readonly action?: NoticeAction | undefined;
  readonly onDismiss?: (() => void) | undefined;
}

const tones = {
  alert: { role: "alert", className: "border-alert/50 bg-alert/8", icon: "text-alert" },
  info: { role: "status", className: "border-rule bg-sheet", icon: "text-ink-muted" },
} as const;

/** An inline message about something that happened, announced to screen readers, with an optional action. */
export function Notice({ tone, children, action, onDismiss }: NoticeProps) {
  const style = tones[tone];
  return (
    <div
      role={style.role}
      className={`flex items-center gap-3 rounded-control border py-1 pr-1 pl-4 ${style.className}`}
    >
      <Icon name="alert" className={`size-5 shrink-0 ${style.icon}`} />
      <p className="min-w-0 flex-1 py-2 text-ink">{children}</p>
      {action && <Button onClick={action.onAction}>{action.label}</Button>}
      {onDismiss && (
        <Button variant="ghost" aria-label="Dismiss" onClick={onDismiss} className="px-0">
          <Icon name="close" />
        </Button>
      )}
    </div>
  );
}
