import { Navigate, useSearchParams } from "react-router";
import { ApiErrorCode, type ApiError } from "../lib/api/client.ts";
import { useAuth } from "../lib/auth/auth-context.tsx";
import { serverFieldErrors } from "../lib/schema/field-errors.ts";
import { returnToSchema } from "../lib/schema/route.ts";
import { type SignUpFailure, SignUpView } from "../views/sign-up-view.tsx";

const credentialFields = ["email", "password"] as const;

// A field problem shows next to its field; any failure other than a taken email means the server couldn't help.
const failureOf = (error: ApiError | null): SignUpFailure | null => {
  if (error === null || error.code === ApiErrorCode.ValidationFailed) return null;
  return error.code === ApiErrorCode.EmailTaken ? "email-taken" : "unreachable";
};

/** The sign-up route: creates the account, which signs the user in, then goes where sign-in would have. */
export function SignUpPage() {
  const { status, signUp } = useAuth();
  const [searchParams] = useSearchParams();
  const returnTo = returnToSchema.parse(searchParams.get("returnTo"));

  if (status === "signed-in") return <Navigate to={returnTo} replace />;
  return (
    <SignUpView
      submitting={signUp.isPending}
      failure={failureOf(signUp.error)}
      fieldErrors={
        signUp.error?.code === ApiErrorCode.ValidationFailed
          ? serverFieldErrors(signUp.error.details, credentialFields)
          : undefined
      }
      onSubmit={(credentials) => {
        signUp.mutate(credentials);
      }}
    />
  );
}
