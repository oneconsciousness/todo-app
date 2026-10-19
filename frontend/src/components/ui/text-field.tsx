import { type ComponentProps, useId } from "react";

/** The input style every text field shares, exported so `SearchBox` uses the same one. */
export const fieldClass =
  "min-h-touch w-full rounded-control border border-rule-strong bg-sheet px-3 text-ink transition-colors placeholder:text-ink-muted hover:border-ink aria-invalid:border-alert disabled:opacity-60";

/** Props for `TextField`: a native input plus its label and an optional error. */
export interface TextFieldProps extends Omit<ComponentProps<"input">, "id"> {
  readonly label: string;
  readonly hideLabel?: boolean;
  readonly error?: string | undefined;
}

/** A labelled text input that shows its error underneath and links the two for screen readers. */
export function TextField({
  label,
  hideLabel = false,
  error,
  className = "",
  ...props
}: TextFieldProps) {
  const id = useId();
  const errorId = `${id}-error`;
  return (
    <div className={`flex flex-col gap-1 ${className}`}>
      <label htmlFor={id} className={hideLabel ? "sr-only" : "text-caption font-medium text-ink"}>
        {label}
      </label>
      <input
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? errorId : undefined}
        className={fieldClass}
        {...props}
      />
      {error && (
        <p id={errorId} className="text-caption text-alert">
          {error}
        </p>
      )}
    </div>
  );
}
