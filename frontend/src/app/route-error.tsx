import { useQueryErrorResetBoundary } from "@tanstack/react-query";
import { useEffect } from "react";
import { useLocation, useNavigate, useRouteError } from "react-router";
import { ApiError } from "../lib/api/client.ts";
import { routes } from "../lib/routes.ts";
import { ErrorView } from "../views/error-view.tsx";

/**
 * The screen for anything a page could not recover from. Both ways out reset TanStack Query's error boundary, so the
 * query that failed runs again instead of throwing its old error
 * ([resetting error boundaries](https://tanstack.com/query/v5/docs/framework/react/reference/QueryErrorResetBoundary)).
 */
export function RouteErrorPage() {
  const error = useRouteError();
  const location = useLocation();
  const navigate = useNavigate();
  const { reset } = useQueryErrorResetBoundary();

  // The console is outside React, so the error is logged once per error rather than on every render.
  useEffect(() => {
    console.error("[app] route error", error);
  }, [error]);

  return (
    <ErrorView
      message={error instanceof ApiError ? error.message : undefined}
      onRetry={() => {
        reset();
        void navigate(location, { replace: true });
      }}
      onGoToTasks={() => {
        reset();
        void navigate(routes.tasks);
      }}
    />
  );
}
