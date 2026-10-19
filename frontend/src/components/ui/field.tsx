import { type ReactNode, useId } from "react";

/** The look every text control shares: inputs, the search box and text areas. */
export const fieldClass =
  "min-h-touch w-full rounded-control border border-rule-strong bg-sheet px-3 text-ink transition-colors placeholder:text-ink-muted hover:border-ink aria-invalid:border-alert disabled:opacity-60";

/** What `Field` hands its control so the label, hint and error are wired to it. */
export interface FieldControlProps {
  readonly id: string;
  readonly "aria-invalid": true | undefined;
  readonly "aria-describedby": string | undefined;
}

/** Props for `Field`. */
export interface FieldProps {
  readonly label: string;
  readonly hideLabel?: boolean | undefined;
  readonly hint?: string | undefined;
  readonly error?: string | undefined;
  readonly className?: string | undefined;
  readonly children: (control: FieldControlProps) => ReactNode;
}

/** A label, a control, a hint and an error, linked so a screen reader reads them together. */
export function Field({
  label,
  hideLabel = false,
  hint,
  error,
  className = "",
  children,
}: FieldProps) {
  const id = useId();
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [hintId, errorId].filter(Boolean).join(" ") || undefined;
  return (
    <div className={`flex flex-col gap-1 ${className}`}>
      <label htmlFor={id} className={hideLabel ? "sr-only" : "text-caption font-medium text-ink"}>
        {label}
      </label>
      {children({ id, "aria-invalid": error ? true : undefined, "aria-describedby": describedBy })}
      {hint && (
        <p id={hintId} className="text-caption text-ink-muted">
          {hint}
        </p>
      )}
      {error && (
        <p id={errorId} className="text-caption text-alert">
          {error}
        </p>
      )}
    </div>
  );
}
