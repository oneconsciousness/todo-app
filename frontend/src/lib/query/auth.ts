import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { login, logout, me, register } from "../api/auth.ts";
import type { User } from "../schema/auth.ts";
import { authKeys } from "./keys.ts";

/**
 * Who is signed in: a user, null for a visitor, or undefined while the first check runs. It changes only through the
 * sign-in, sign-up and sign-out hooks below, so it never goes stale. A failed check goes to the route error boundary.
 */
export const useMe = () =>
  useQuery({
    queryKey: authKeys.me,
    queryFn: ({ signal }) => me(signal),
    staleTime: Infinity,
    throwOnError: true,
  });

/** Sign in, then remember the user without asking the server again. */
export const useSignIn = () => {
  const client = useQueryClient();
  return useMutation({
    mutationKey: authKeys.mutations.signIn,
    mutationFn: login,
    onSuccess: (user: User) => {
      client.setQueryData(authKeys.me, user);
    },
  });
};

/** Create an account, which also signs the new user in. */
export const useSignUp = () => {
  const client = useQueryClient();
  return useMutation({
    mutationKey: authKeys.mutations.signUp,
    mutationFn: register,
    onSuccess: (user: User) => {
      client.setQueryData(authKeys.me, user);
    },
  });
};

/** Sign out and forget every cached answer, so the next person on this browser sees none of them. */
export const useSignOut = () => {
  const client = useQueryClient();
  return useMutation({
    mutationKey: authKeys.mutations.signOut,
    mutationFn: logout,
    onSuccess: () => {
      client.clear();
    },
  });
};
