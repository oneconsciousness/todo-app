import { type QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { createQueryClient } from "../lib/query/client.ts";

/** A fresh app query client and a wrapper that provides it, for testing hooks on their own. */
export const queryWrapper = (): {
  readonly client: QueryClient;
  readonly wrapper: (props: { readonly children: ReactNode }) => ReactNode;
} => {
  const client = createQueryClient({ onUnauthenticated: () => undefined });
  const wrapper = ({ children }: { readonly children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  );
  return { client, wrapper };
};
