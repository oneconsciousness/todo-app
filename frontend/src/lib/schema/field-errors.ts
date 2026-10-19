import type { z } from "zod";
import type { FieldError } from "./error.ts";

/** One message per form field, for the fields that have a problem. */
export type FieldErrors<T> = { readonly [K in keyof T]?: string | undefined };

/** The first message for each field of a failed parse, so a form can show it next to the field. */
export const fieldErrors = <T>(error: z.ZodError<T>): FieldErrors<T> =>
  error.issues.reduce<FieldErrors<T>>((errors, { path: [field], message }) => {
    if (typeof field !== "string" || field in errors) return errors;
    return { ...errors, [field]: message };
  }, {});

/** The server's first message for each of the form's `fields`, from an error's `details`; other entries are dropped. */
export const serverFieldErrors = <K extends string>(
  details: readonly FieldError[],
  fields: readonly K[],
): FieldErrors<Record<K, string>> =>
  details.reduce<FieldErrors<Record<K, string>>>((errors, { field, message }) => {
    const known = fields.find((name) => name === field);
    if (known === undefined || known in errors) return errors;
    return { ...errors, [known]: message };
  }, {});
