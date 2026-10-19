import { AuthLayout } from "../components/auth-layout.tsx";
import { CredentialsForm, unreachableMessage } from "../components/credentials-form.tsx";
import { Link, textLinkClass } from "../components/ui/link.tsx";
import { routes } from "../lib/routes.ts";
import type { Credentials } from "../lib/schema/auth.ts";

/** Why the last sign-in failed: a 401, or no answer from the server. */
export type SignInFailure = "wrong-credentials" | "unreachable";

/** Props for `SignInView`. */
export interface SignInViewProps {
  readonly submitting: boolean;
  readonly failure: SignInFailure | null;
  readonly initialEmail?: string | undefined;
  readonly onSubmit: (credentials: Credentials) => void;
}

const messages: Readonly<Record<SignInFailure, string>> = {
  "wrong-credentials": "That email and password don't match an account. Check both and try again.",
  unreachable: unreachableMessage,
};

/** The landing page: sign in, or go and create an account. */
export function SignInView({ submitting, failure, initialEmail, onSubmit }: SignInViewProps) {
  return (
    <AuthLayout
      title="Sign in"
      footer={
        <>
          New here?{" "}
          <Link href={routes.signUp} className={textLinkClass}>
            Create an account
          </Link>
        </>
      }
    >
      <CredentialsForm
        submitLabel="Sign in"
        submittingLabel="Signing in…"
        passwordAutoComplete="current-password"
        submitting={submitting}
        failure={failure && messages[failure]}
        initialEmail={initialEmail}
        onSubmit={onSubmit}
      />
    </AuthLayout>
  );
}
