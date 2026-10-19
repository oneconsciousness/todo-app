/** The app's paths, from the spec's Screens table. Views link with these; the router will match them. */
export const routes = {
  signIn: "/sign-in",
  signUp: "/sign-up",
  tasks: "/tasks",
  task: (taskId: string): string => `/tasks/${taskId}`,
} as const;
