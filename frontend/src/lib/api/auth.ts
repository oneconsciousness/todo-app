import { type Credentials, type User, userSchema } from "../schema/auth.ts";
import { ApiError, ApiErrorCode, apiRequest, apiRequestNoContent } from "./client.ts";

/** Create an account; the server signs the new user in. */
export const register = (credentials: Credentials): Promise<User> =>
  apiRequest("/auth/register", { method: "POST", body: credentials, schema: userSchema });

/** Sign in with an email and password. */
export const login = (credentials: Credentials): Promise<User> =>
  apiRequest("/auth/login", { method: "POST", body: credentials, schema: userSchema });

/** Sign out: the server clears the session cookie. */
export const logout = (): Promise<void> => apiRequestNoContent("/auth/logout", { method: "POST" });

/** The signed-in user, or null when nobody is signed in, so a visitor is never treated as an expired session. */
export const me = (signal?: AbortSignal): Promise<User | null> =>
  apiRequest("/auth/me", { schema: userSchema, signal }).catch((error: unknown) => {
    if (error instanceof ApiError && error.code === ApiErrorCode.NotAuthenticated) return null;
    throw error;
  });
