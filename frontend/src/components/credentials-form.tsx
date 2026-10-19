import { type ChangeEvent, type ReactNode, type SubmitEvent, useState } from "react";
import { type Credentials, credentialsSchema } from "../lib/schema/auth.ts";
import { type FieldErrors, fieldErrors } from "../lib/schema/field-errors.ts";
import { Button } from "./ui/button.tsx";
import { Notice } from "./ui/notice.tsx";
import { TextField } from "./ui/text-field.tsx";

/** What sign-in and sign-up both say when the server can't be reached. */
export const unreachableMessage = "Couldn't reach the server. Check your connection and try again.";

/** Props for `CredentialsForm`. */
export interface CredentialsFormProps {
  readonly submitLabel: string;
  readonly submittingLabel: string;
  readonly passwordAutoComplete: "current-password" | "new-password";
  readonly passwordHint?: string | undefined;
  readonly submitting: boolean;
  /** What went wrong on the last attempt, shown above the fields; null when nothing did. */
  readonly failure: ReactNode;
  readonly initialEmail?: string | undefined;
  readonly onSubmit: (credentials: Credentials) => void;
}

/** The email and password form behind sign-in and sign-up, validated by the same schema the API layer uses. */
export function CredentialsForm({
  submitLabel,
  submittingLabel,
  passwordAutoComplete,
  passwordHint,
  submitting,
  failure,
  initialEmail = "",
  onSubmit,
}: CredentialsFormProps) {
  const [values, setValues] = useState<Credentials>({ email: initialEmail, password: "" });
  const [errors, setErrors] = useState<FieldErrors<Credentials>>({});

  const edit = (field: keyof Credentials) => (event: ChangeEvent<HTMLInputElement>) => {
    setValues((current) => ({ ...current, [field]: event.target.value }));
    setErrors((current) => ({ ...current, [field]: undefined }));
  };

  const handleSubmit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    const result = credentialsSchema.safeParse(values);
    if (result.success) onSubmit(result.data);
    else setErrors(fieldErrors(result.error));
  };

  return (
    <form noValidate onSubmit={handleSubmit} className="flex flex-col gap-6">
      {failure && <Notice tone="alert">{failure}</Notice>}
      <fieldset disabled={submitting} className="flex min-w-0 flex-col gap-4">
        <TextField
          label="Email"
          type="email"
          autoComplete="email"
          value={values.email}
          error={errors.email}
          onChange={edit("email")}
        />
        <TextField
          label="Password"
          type="password"
          autoComplete={passwordAutoComplete}
          hint={passwordHint}
          value={values.password}
          error={errors.password}
          onChange={edit("password")}
        />
      </fieldset>
      <Button type="submit" variant="primary" disabled={submitting} className="w-full">
        {submitting ? submittingLabel : submitLabel}
      </Button>
    </form>
  );
}
