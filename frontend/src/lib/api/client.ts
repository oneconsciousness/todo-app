import type { z } from "zod";
import { type FieldError, ServerErrorCode, errorEnvelopeSchema } from "../schema/error.ts";

/** Every reason an API call can fail: the API's own codes, plus the ones the app works out when there is no envelope. */
export const ApiErrorCode = {
  ...ServerErrorCode,
  NetworkError: "network_error",
  InvalidResponse: "invalid_response",
  PayloadTooLarge: "payload_too_large",
  Unexpected: "unexpected",
} as const;

/** One of the `ApiErrorCode` values. */
export type ApiErrorCode = (typeof ApiErrorCode)[keyof typeof ApiErrorCode];

/** What an `ApiError` is built from. */
export interface ApiErrorInit {
  /** The HTTP status, or 0 when no response came back. */
  readonly status: number;
  readonly code: ApiErrorCode;
  readonly message: string;
  readonly details?: readonly FieldError[];
}

/** A failed API call, with a code the app can switch on and a message that is safe to show. */
export class ApiError extends Error {
  override readonly name = "ApiError";
  /** The HTTP status, or 0 when no response came back. */
  readonly status: number;
  readonly code: ApiErrorCode;
  readonly details: readonly FieldError[];

  constructor({ status, code, message, details = [] }: ApiErrorInit) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

/** The methods the API uses. */
export type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

/** How to send one request. `ifMatch` is the task version the write expects to find. */
export interface RequestOptions {
  readonly method?: HttpMethod;
  readonly body?: unknown;
  readonly signal?: AbortSignal | undefined;
  readonly ifMatch?: number | undefined;
}

const derivedMessages = {
  [ApiErrorCode.NetworkError]: "Couldn't reach the server. Check your connection and try again.",
  [ApiErrorCode.ServiceUnavailable]: "The server is busy. Try again in a moment.",
  [ApiErrorCode.PayloadTooLarge]: "That is too much to send in one go.",
  [ApiErrorCode.InvalidResponse]: "The server sent an answer the app couldn't read.",
  [ApiErrorCode.Unexpected]: "Something went wrong on the server.",
} as const;

type DerivedCode = keyof typeof derivedMessages;

const derivedError = (status: number, code: DerivedCode): ApiError =>
  new ApiError({ status, code, message: derivedMessages[code] });

// A proxy or an overloaded server can answer without the API's envelope, so the status is all there is to go on.
const codeForStatus = (status: number): DerivedCode => {
  if (status === 502 || status === 503 || status === 504) return ApiErrorCode.ServiceUnavailable;
  if (status === 413) return ApiErrorCode.PayloadTooLarge;
  return ApiErrorCode.Unexpected;
};

const headersFor = ({ body, ifMatch }: RequestOptions): Record<string, string> => ({
  Accept: "application/json",
  ...(body === undefined ? {} : { "Content-Type": "application/json" }),
  ...(ifMatch === undefined ? {} : { "If-Match": `"${String(ifMatch)}"` }),
});

const readJson = (response: Response): Promise<unknown> =>
  response.json().then(
    (body: unknown) => body,
    () => undefined,
  );

// The query string can hold a search term, which never goes into a log.
const withoutQuery = (path: string): string => path.replace(/\?.*$/, "");

// fetch rejects with a TypeError when no response arrives; an abort is left alone so TanStack Query sees a cancel.
const send = async (path: string, options: RequestOptions): Promise<Response> => {
  try {
    return await fetch(`/api/v1${path}`, {
      method: options.method ?? "GET",
      credentials: "same-origin",
      headers: headersFor(options),
      body: options.body === undefined ? null : JSON.stringify(options.body),
      signal: options.signal ?? null,
    });
  } catch (error) {
    if (error instanceof TypeError) throw derivedError(0, ApiErrorCode.NetworkError);
    throw error;
  }
};

const errorFrom = async (response: Response): Promise<ApiError> => {
  const envelope = errorEnvelopeSchema.safeParse(await readJson(response));
  if (!envelope.success) return derivedError(response.status, codeForStatus(response.status));
  return new ApiError({ status: response.status, ...envelope.data.error });
};

const ensureOk = async (response: Response): Promise<Response> => {
  if (response.ok) return response;
  throw await errorFrom(response);
};

/** Call the API at `path` (relative to `/api/v1`) and parse the answer with `schema`; any failure is an `ApiError`. */
export const apiRequest = async <S extends z.ZodType>(
  path: string,
  options: RequestOptions & { readonly schema: S },
): Promise<z.infer<S>> => {
  const response = await ensureOk(await send(path, options));
  const parsed = options.schema.safeParse(await readJson(response));
  if (parsed.success) return parsed.data;
  console.error("[api] response did not match schema", {
    path: withoutQuery(path),
    issues: parsed.error.issues,
  });
  throw derivedError(response.status, ApiErrorCode.InvalidResponse);
};

/** Call an endpoint that answers 204 with no body; any failure is an `ApiError`. */
export const apiRequestNoContent = async (path: string, options: RequestOptions): Promise<void> => {
  await ensureOk(await send(path, options));
};
