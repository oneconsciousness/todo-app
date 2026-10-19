import { MutationCache, QueryCache, QueryClient, type QueryKey } from "@tanstack/react-query";
import { type ApiError, ApiErrorCode } from "../api/client.ts";

// Every hook's `error` is an ApiError, since every request goes through the fetch wrapper
// (https://tanstack.com/query/v5/docs/framework/react/typescript#registering-a-global-error).
declare module "@tanstack/react-query" {
  interface Register {
    defaultError: ApiError;
  }
}

/** What the app does when the server says the session has ended. */
export interface QueryClientOptions {
  readonly onUnauthenticated: () => void;
}

const retryable: ReadonlySet<ApiErrorCode> = new Set([
  ApiErrorCode.NetworkError,
  ApiErrorCode.ServiceUnavailable,
]);

const maxRetries = 2;

// A wrong password, a taken email, a 404 or a 412 are answers the screens handle; only these mean something broke.
const isIncident = (error: ApiError): boolean =>
  error.status >= 500 ||
  error.code === ApiErrorCode.NetworkError ||
  error.code === ApiErrorCode.InvalidResponse;

// Only the first part of a key is logged: the rest can hold a search term.
const resourceOf = (key: QueryKey | undefined): string => {
  const [resource] = key ?? [];
  return typeof resource === "string" ? resource : "unknown";
};

/**
 * The app's one query client. Data refetches whenever the window regains focus, only a lost connection or a busy
 * server is retried, an ended session clears every cached answer before `onUnauthenticated` runs, and only failures
 * that mean something broke are logged.
 */
export const createQueryClient = ({ onUnauthenticated }: QueryClientOptions): QueryClient => {
  const handleError = (error: ApiError, key: QueryKey | undefined): void => {
    if (error.code === ApiErrorCode.NotAuthenticated) {
      client.clear();
      onUnauthenticated();
      return;
    }
    if (!isIncident(error)) return;
    console.error("[query] failed", {
      key: resourceOf(key),
      status: error.status,
      code: error.code,
    });
  };

  const client = new QueryClient({
    queryCache: new QueryCache({
      onError: (error, query) => {
        handleError(error, query.queryKey);
      },
    }),
    mutationCache: new MutationCache({
      onError: (error, _variables, _onMutateResult, mutation) => {
        handleError(error, mutation.options.mutationKey);
      },
    }),
    defaultOptions: {
      queries: {
        staleTime: 0,
        refetchOnWindowFocus: true,
        refetchOnReconnect: true,
        retry: (failureCount, error) => failureCount < maxRetries && retryable.has(error.code),
      },
      mutations: { retry: 0 },
    },
  });
  return client;
};
