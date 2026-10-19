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
  readonly children: ReactNode;
  readonly actions?: readonly NoticeAction[] | undefined;
  readonly onDismiss?: (() => void) | undefined;
}

/** An alert about something that needs the user, announced to screen readers, with the ways to answer it. */
export function Notice({ children, actions = [], onDismiss }: NoticeProps) {
  return (
    <div
      role="alert"
      className="flex flex-col gap-1 rounded-control border border-alert/50 bg-alert/8 py-1 pr-1 pl-4 @wide:flex-row @wide:items-center @wide:gap-3"
    >
      <div className="flex min-w-0 flex-1 items-start gap-3 py-2 pr-3">
        <span className="flex h-6 shrink-0 items-center">
          <Icon name="alert" className="size-5 text-alert" />
        </span>
        <div className="min-w-0 text-ink">{children}</div>
      </div>
      {(actions.length > 0 || onDismiss) && (
        <div className="flex flex-wrap items-center justify-end gap-1">
          {actions.map(({ label, onAction }) => (
            <Button key={label} onClick={onAction}>
              {label}
            </Button>
          ))}
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
