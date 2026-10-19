import { Navigate, useSearchParams } from "react-router";
import { ApiErrorCode, type ApiError } from "../lib/api/client.ts";
import { useAuth } from "../lib/auth/auth-context.tsx";
import { serverFieldErrors } from "../lib/schema/field-errors.ts";
import { returnToSchema } from "../lib/schema/route.ts";
import { type SignInFailure, SignInView } from "../views/sign-in-view.tsx";

const credentialFields = ["email", "password"] as const;

// A field problem shows next to its field; any failure other than a wrong password means the server couldn't help.
const failureOf = (error: ApiError | null): SignInFailure | null => {
  if (error === null || error.code === ApiErrorCode.ValidationFailed) return null;
  return error.code === ApiErrorCode.InvalidCredentials ? "wrong-credentials" : "unreachable";
};

/** The sign-in route: signs in, then goes back to the page that sent the user here. */
export function SignInPage() {
  const { status, signIn } = useAuth();
  const [searchParams] = useSearchParams();
  const returnTo = returnToSchema.parse(searchParams.get("returnTo"));

  if (status === "signed-in") return <Navigate to={returnTo} replace />;
  return (
    <SignInView
      submitting={signIn.isPending}
      failure={failureOf(signIn.error)}
      fieldErrors={
        signIn.error?.code === ApiErrorCode.ValidationFailed
          ? serverFieldErrors(signIn.error.details, credentialFields)
          : undefined
      }
      onSubmit={(credentials) => {
        signIn.mutate(credentials);
      }}
    />
  );
}
