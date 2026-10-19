import { Navigate, Outlet, useLocation, useNavigate } from "react-router";
import { AppShell } from "../components/app-shell.tsx";
import { useAuth } from "../lib/auth/auth-context.tsx";
import { routes, signInPath } from "../lib/routes.ts";

/** The signed-in layout: the shell around the page while signed in, sign-in (with the way back) otherwise. */
export function RequireAuth() {
  const auth = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  switch (auth.status) {
    case "loading":
      return <AppShell account={null}>{null}</AppShell>;
    case "signed-out":
      return <Navigate to={signInPath(location.pathname + location.search)} replace />;
    case "signed-in":
      return (
        <AppShell
          account={{
            email: auth.user.email,
            signingOut: auth.signOut.isPending,
            onSignOut: () => {
              auth.signOut.mutate(undefined, {
                onSuccess: () => {
                  void navigate(routes.signIn, { replace: true });
                },
              });
            },
          }}
        >
          <Outlet />
        </AppShell>
      );
    default: {
      const unreachable: never = auth;
      return unreachable;
    }
  }
}
