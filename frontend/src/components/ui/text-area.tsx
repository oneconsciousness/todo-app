import type { ComponentProps } from "react";
import { Field, fieldClass } from "./field.tsx";

/** Props for `TextArea`: a native textarea plus its label, hint and error. */
export interface TextAreaProps extends Omit<ComponentProps<"textarea">, "id" | "className"> {
  readonly label: string;
  readonly hint?: string | undefined;
  readonly error?: string | undefined;
  readonly className?: string;
}

/** A labelled multi-line field, ruled like the ledger page so long notes keep their lines. */
export function TextArea({ label, hint, error, className, ...props }: TextAreaProps) {
  return (
    <Field label={label} hint={hint} error={error} className={className}>
      {(control) => <textarea {...control} className={`${fieldClass} resize-y ruled`} {...props} />}
    </Field>
  );
}
