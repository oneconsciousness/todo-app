// First, so Zod is configured before any schema module is evaluated.
import "./lib/schema/zod-config.ts";
import { QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { RouterProvider } from "react-router/dom";
import { createAppRouter, goToSignIn } from "./app/router.tsx";
import { createQueryClient } from "./lib/query/client.ts";
import "./styles/index.css";

const container = document.getElementById("root");
if (!container) throw new Error("index.html is missing the #root element");

const router = createAppRouter();
const queryClient = createQueryClient({ onUnauthenticated: goToSignIn(router) });

createRoot(container).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </StrictMode>,
);
console.info("[app] started", { mode: import.meta.env.MODE });
