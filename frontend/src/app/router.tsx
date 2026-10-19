import {
  type DataRouter,
  Navigate,
  Outlet,
  type RouteObject,
  createBrowserRouter,
  useNavigate,
} from "react-router";
import { NavigationProvider } from "../components/ui/link.tsx";
import { AuthProvider } from "../lib/auth/auth-context.tsx";
import { routes, signInPath } from "../lib/routes.ts";
import { SignInPage } from "../pages/sign-in-page.tsx";
import { SignUpPage } from "../pages/sign-up-page.tsx";
import { RequireAuth } from "./require-auth.tsx";

// Every page gets the session, and every `Link` navigates through the router instead of reloading the page.
function AppRoot() {
  const navigate = useNavigate();
  return (
    <AuthProvider>
      <NavigationProvider
        navigate={(href) => {
          void navigate(href);
        }}
      >
        <Outlet />
      </NavigationProvider>
    </AuthProvider>
  );
}

/** The app's route table. */
export const appRoutes: RouteObject[] = [
  {
    element: <AppRoot />,
    children: [
      { path: "/", element: <Navigate to={routes.tasks} replace /> },
      { path: routes.signIn, element: <SignInPage /> },
      { path: routes.signUp, element: <SignUpPage /> },
      {
        element: <RequireAuth />,
        children: [{ path: routes.tasks }, { path: routes.task(":taskId") }],
      },
    ],
  },
];

/** The router the browser runs, with history in the address bar. */
export const createAppRouter = (): DataRouter => createBrowserRouter(appRoutes);

/** Send the user to sign-in from wherever they are, keeping that place to come back to; for an ended session. */
export const goToSignIn = (router: DataRouter) => (): void => {
  const { pathname, search } = router.state.location;
  void router.navigate(signInPath(pathname + search), { replace: true });
};
