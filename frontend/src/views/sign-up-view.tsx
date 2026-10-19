import type { ReactNode } from "react";
import { AuthLayout } from "../components/auth-layout.tsx";
import { CredentialsForm, unreachableMessage } from "../components/credentials-form.tsx";
import { Link, textLinkClass } from "../components/ui/link.tsx";
import { routes } from "../lib/routes.ts";
import type { Credentials } from "../lib/schema/auth.ts";
import type { FieldErrors } from "../lib/schema/field-errors.ts";

/** Why the last sign-up failed: a 409 for a registered email, or no answer from the server. */
export type SignUpFailure = "email-taken" | "unreachable";

/** Props for `SignUpView`. */
export interface SignUpViewProps {
  readonly submitting: boolean;
  readonly failure: SignUpFailure | null;
  /** The server's problems with the email or password sent, shown next to each field. */
  readonly fieldErrors?: FieldErrors<Credentials> | undefined;
  readonly onSubmit: (credentials: Credentials) => void;
}

const messages: Readonly<Record<SignUpFailure, ReactNode>> = {
  "email-taken": (
    <>
      An account with this email already exists.{" "}
      <Link href={routes.signIn} className={textLinkClass}>
        Sign in instead
      </Link>
    </>
  ),
  unreachable: unreachableMessage,
};

/** Create an account with an email and a password of 12 to 128 characters. */
export function SignUpView({ submitting, failure, fieldErrors, onSubmit }: SignUpViewProps) {
  return (
    <AuthLayout
      title="Create an account"
      footer={
        <>
          Already have an account?{" "}
          <Link href={routes.signIn} className={textLinkClass}>
            Sign in
          </Link>
        </>
      }
    >
      <CredentialsForm
        submitLabel="Create account"
        submittingLabel="Creating account…"
        passwordAutoComplete="new-password"
        passwordHint="At least 12 characters."
        submitting={submitting}
        failure={failure && messages[failure]}
        fieldErrors={fieldErrors}
        onSubmit={onSubmit}
      />
    </AuthLayout>
  );
}
