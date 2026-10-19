import type { ComponentProps } from "react";
import { Field, fieldClass } from "./field.tsx";

/** Props for `TextField`: a native input plus its label, hint and error. */
export interface TextFieldProps extends Omit<ComponentProps<"input">, "id" | "className"> {
  readonly label: string;
  readonly hideLabel?: boolean;
  readonly hint?: string | undefined;
  readonly error?: string | undefined;
  readonly className?: string;
}

/** A labelled single-line input that shows its hint and error underneath. */
export function TextField({ label, hideLabel, hint, error, className, ...props }: TextFieldProps) {
  return (
    <Field label={label} hideLabel={hideLabel} hint={hint} error={error} className={className}>
      {(control) => <input {...control} className={fieldClass} {...props} />}
    </Field>
  );
}
