/** The app's paths. Views link with these, and the router matches them. */
export const routes = {
  signIn: "/sign-in",
  signUp: "/sign-up",
  tasks: "/tasks",
  task: (taskId: string): string => `/tasks/${taskId}`,
} as const;

/** The sign-in page, told to come back to `returnTo` (a path plus its query string) once the user is signed in. */
export const signInPath = (returnTo: string): string =>
  `${routes.signIn}?${new URLSearchParams({ returnTo }).toString()}`;
