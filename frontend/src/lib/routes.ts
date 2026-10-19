/** The app's paths. Views link with these, and the router matches them. */
export const routes = {
  signIn: "/sign-in",
  signUp: "/sign-up",
  tasks: "/tasks",
  task: (taskId: string): string => `/tasks/${taskId}`,
} as const;
