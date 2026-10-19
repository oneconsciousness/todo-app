import type { z } from "zod";

/** One message per form field, for the fields that have a problem. */
export type FieldErrors<T> = { readonly [K in keyof T]?: string | undefined };

/** The first message for each field of a failed parse, so a form can show it next to the field. */
export const fieldErrors = <T>(error: z.ZodError<T>): FieldErrors<T> =>
  error.issues.reduce<FieldErrors<T>>((errors, { path: [field], message }) => {
    if (typeof field !== "string" || field in errors) return errors;
    return { ...errors, [field]: message };
  }, {});
