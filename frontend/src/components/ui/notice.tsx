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
      className={`flex flex-col gap-1 rounded-control border py-1 pr-1 pl-4 @wide:flex-row @wide:items-center @wide:gap-3 ${style.className}`}
    >
      <div className="flex min-w-0 flex-1 items-start gap-3 py-2 pr-3">
        <span className="flex h-6 shrink-0 items-center">
          <Icon name="alert" className={`size-5 ${style.icon}`} />
        </span>
        <p className="min-w-0 text-ink">{children}</p>
      </div>
      {(action ?? onDismiss) && (
        <div className="flex items-center justify-end gap-1">
          {action && <Button onClick={action.onAction}>{action.label}</Button>}
          {onDismiss && (
            <Button variant="ghost" aria-label="Dismiss" onClick={onDismiss} className="px-0">
              <Icon name="close" />
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
