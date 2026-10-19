import { type QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { type DataRouter, createMemoryRouter } from "react-router";
import { RouterProvider } from "react-router/dom";
import { appRoutes, goToSignIn } from "../app/router.tsx";
import { createQueryClient } from "../lib/query/client.ts";

/** What a test gets back from `renderApp`: the router, to read the location, and the query client. */
export interface RenderedApp {
  readonly router: DataRouter;
  readonly client: QueryClient;
}

/** Render the whole app at `path`, wired the way `main.tsx` wires it, with history kept in memory. */
export const renderApp = (path: string): RenderedApp => {
  const router = createMemoryRouter(appRoutes, { initialEntries: [path] });
  const client = createQueryClient({ onUnauthenticated: goToSignIn(router) });
  render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  return { router, client };
};
