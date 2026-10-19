import { useEffect, useId, useRef } from "react";
import { Button } from "./button.tsx";

/** Props for `InlineConfirm`. */
export interface InlineConfirmProps {
  readonly message: string;
  readonly confirmLabel: string;
  readonly busyLabel: string;
  readonly cancelLabel: string;
  readonly busy: boolean;
  readonly onConfirm: () => void;
  readonly onCancel: () => void;
}

/**
 * A confirm step built into the page, since the artifact viewer and good manners both rule out `confirm()`.
 * Focus lands on the safe choice, so a stray Enter backs out.
 */
export function InlineConfirm({
  message,
  confirmLabel,
  busyLabel,
  cancelLabel,
  busy,
  onConfirm,
  onCancel,
}: InlineConfirmProps) {
  const messageId = useId();
  const cancel = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    cancel.current?.focus();
  }, []);
  return (
    <div
      role="group"
      aria-labelledby={messageId}
      className="flex w-full flex-col gap-3 rounded-control border border-alert/50 bg-alert/8 p-4 @wide:flex-row @wide:items-center"
    >
      <p id={messageId} className="flex-1 text-ink">
        {message}
      </p>
      <div className="flex flex-wrap gap-2">
        <Button variant="danger" disabled={busy} onClick={onConfirm}>
          {busy ? busyLabel : confirmLabel}
        </Button>
        <Button ref={cancel} disabled={busy} onClick={onCancel}>
          {cancelLabel}
        </Button>
      </div>
    </div>
  );
}
