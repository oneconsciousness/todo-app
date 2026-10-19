import { z } from "zod";

const emailMessage = "Enter an email address like name@example.com.";

/** An email and password, for both sign-in and sign-up. The email is trimmed; the password never is. */
export const credentialsSchema = z.object({
  email: z
    .string()
    .trim()
    .pipe(z.email(emailMessage).max(254, "Use an email address of 254 characters or fewer.")),
  password: z
    .string()
    .min(12, "Use at least 12 characters.")
    .max(128, "Use 128 characters or fewer."),
});

/** An email and password, typed from their schema. */
export type Credentials = z.infer<typeof credentialsSchema>;

/**
 * The signed-in user, as `GET /api/v1/auth/me` returns it. The server already validated the email with Pydantic's
 * `EmailStr`, which accepts internationalised addresses that `z.email()` would reject, so here it is any non-empty
 * string.
 */
export const userSchema = z.object({
  id: z.uuid(),
  email: z.string().min(1),
});

/** The signed-in user, typed from its schema. */
export type User = z.infer<typeof userSchema>;
