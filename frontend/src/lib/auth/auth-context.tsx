import { type ReactNode, createContext, use } from "react";
import { useMe, useSignIn, useSignOut, useSignUp } from "../query/auth.ts";
import type { User } from "../schema/auth.ts";

/** Whether anyone is signed in: still checking, a visitor, or a user. */
export type Session =
  | { readonly status: "loading"; readonly user: null }
  | { readonly status: "signed-out"; readonly user: null }
  | { readonly status: "signed-in"; readonly user: User };

/** The actions that change the session. */
interface AuthActions {
  readonly signIn: ReturnType<typeof useSignIn>;
  readonly signUp: ReturnType<typeof useSignUp>;
  readonly signOut: ReturnType<typeof useSignOut>;
}

/** The session, and the actions that change it. */
export type Auth = Session & AuthActions;

const AuthContext = createContext<AuthActions | null>(null);

/** Read the session from the cached `me` answer: undefined while checking, null for a visitor. */
export const sessionFrom = (me: User | null | undefined): Session => {
  if (me === undefined) return { status: "loading", user: null };
  if (me === null) return { status: "signed-out", user: null };
  return { status: "signed-in", user: me };
};

/** Gives every page below it one sign-in, sign-up and sign-out, so their progress and errors are shared. */
export function AuthProvider({ children }: { readonly children: ReactNode }) {
  const signIn = useSignIn();
  const signUp = useSignUp();
  const signOut = useSignOut();
  return <AuthContext value={{ signIn, signUp, signOut }}>{children}</AuthContext>;
}

/**
 * The session and its actions; only valid below `AuthProvider`. The session is read from the `me` query in the
 * component that asks, while it renders, so a page never acts on a session that has already ended.
 */
export const useAuth = (): Auth => {
  const actions = use(AuthContext);
  const me = useMe();
  if (!actions) throw new Error("useAuth is used outside AuthProvider");
  return { ...sessionFrom(me.data), ...actions };
};
