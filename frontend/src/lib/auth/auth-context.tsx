import { type ReactNode, createContext, use } from "react";
import { useMe, useSignIn, useSignOut, useSignUp } from "../query/auth.ts";
import type { User } from "../schema/auth.ts";

/** Whether anyone is signed in: still checking, a visitor, or a user. */
export type Session =
  | { readonly status: "loading"; readonly user: null }
  | { readonly status: "signed-out"; readonly user: null }
  | { readonly status: "signed-in"; readonly user: User };

/** The session, and the actions that change it. */
export type Auth = Session & {
  readonly signIn: ReturnType<typeof useSignIn>;
  readonly signUp: ReturnType<typeof useSignUp>;
  readonly signOut: ReturnType<typeof useSignOut>;
};

const AuthContext = createContext<Auth | null>(null);

/** Read the session from the cached `me` answer: undefined while checking, null for a visitor. */
export const sessionFrom = (me: User | null | undefined): Session => {
  if (me === undefined) return { status: "loading", user: null };
  if (me === null) return { status: "signed-out", user: null };
  return { status: "signed-in", user: me };
};

/** Gives every page below it the session, worked out from the server's answer on each render rather than copied. */
export function AuthProvider({ children }: { readonly children: ReactNode }) {
  const me = useMe();
  const signIn = useSignIn();
  const signUp = useSignUp();
  const signOut = useSignOut();
  return (
    <AuthContext value={{ ...sessionFrom(me.data), signIn, signUp, signOut }}>
      {children}
    </AuthContext>
  );
}

/** The session and its actions; only valid below `AuthProvider`. */
export const useAuth = (): Auth => {
  const auth = use(AuthContext);
  if (!auth) throw new Error("useAuth is used outside AuthProvider");
  return auth;
};
