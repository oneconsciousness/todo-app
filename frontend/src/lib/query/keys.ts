/**
 * Cache keys for tasks. They nest, so invalidating `lists()` reaches every cached search at once
 * ([query keys](https://tanstack.com/query/v5/docs/framework/react/guides/query-keys)).
 */
export const taskKeys = {
  all: ["tasks"] as const,
  lists: () => [...taskKeys.all, "list"] as const,
  list: (q: string) => [...taskKeys.lists(), { q }] as const,
  details: () => [...taskKeys.all, "detail"] as const,
  detail: (id: string) => [...taskKeys.details(), id] as const,
  mutations: {
    toggle: ["tasks", "toggle"],
    move: ["tasks", "move"],
    remove: ["tasks", "remove"],
    update: ["tasks", "update"],
    create: ["tasks", "create"],
  },
} as const;

/** Cache keys for the signed-in user. */
export const authKeys = { me: ["auth", "me"] as const };
