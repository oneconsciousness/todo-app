import { z } from "zod";

/** Every `code` the API puts in its error envelope. */
export const ServerErrorCode = {
  ValidationFailed: "validation_failed",
  InvalidIfMatch: "invalid_if_match",
  InvalidPosition: "invalid_position",
  NotAuthenticated: "not_authenticated",
  InvalidCredentials: "invalid_credentials",
  ForbiddenOrigin: "forbidden_origin",
  NotFound: "not_found",
  MethodNotAllowed: "method_not_allowed",
  EmailTaken: "email_taken",
  VersionMismatch: "version_mismatch",
  ServiceUnavailable: "service_unavailable",
  InternalError: "internal_error",
} as const;

/** One problem with one field of a request; `field` is null when the problem is with the request as a whole. */
export const fieldErrorSchema = z.object({
  field: z.string().nullable(),
  message: z.string(),
});

/** One problem with one field of a request, typed from its schema. */
export type FieldError = z.infer<typeof fieldErrorSchema>;

/** The one error body every API error carries: `{"error": {"code", "message", "details"}}`. */
export const errorEnvelopeSchema = z.object({
  error: z.object({
    code: z.enum(ServerErrorCode),
    message: z.string(),
    details: z.array(fieldErrorSchema),
  }),
});
