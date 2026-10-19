import { type User, userSchema } from "../lib/schema/auth.ts";
import { type Task, taskSchema } from "../lib/schema/task.ts";
import type { TaskDetailViewProps } from "../views/task-detail-view.tsx";
import type { TaskListViewProps } from "../views/task-list-view.tsx";

/** The date every fixture is relative to: Monday 19 October 2026. */
export const today = "2026-10-19";

/** The signed-in user every app test runs as. */
export const user: User = userSchema.parse({
  id: "00000000-0000-4000-8000-0000000000aa",
  email: "maya@example.com",
});

/** Build one valid task, parsed through the real schema, with any fields overridden; pass an id when several must differ. */
export const makeTask = (overrides: Partial<Task> = {}): Task =>
  taskSchema.parse({
    id: "00000000-0000-4000-8000-000000000000",
    title: "Water the plants",
    notes: "",
    completed: false,
    dueDate: null,
    rank: "a0",
    version: 1,
    createdAt: "2026-10-12T08:30:00Z",
    updatedAt: "2026-10-12T08:30:00Z",
    ...overrides,
  });

const listed = (specs: readonly Partial<Task>[]): readonly Task[] =>
  specs.map((spec, index) =>
    makeTask({
      id: `00000000-0000-4000-8000-${String(index + 1).padStart(12, "0")}`,
      rank: `a${String(index)}`,
      ...spec,
    }),
  );

/** A realistic week of tasks: overdue, due today, upcoming, undated, completed, and one long title. */
export const tasks: readonly Task[] = listed([
  {
    title: "Call the landlord about the boiler service",
    notes:
      "The annual service is due before the cold weather. Ask about the back bedroom radiator.",
    dueDate: "2026-10-19",
  },
  {
    title: "Send Maya the Q3 budget notes",
    notes: "She needs the travel line split out by team.",
    dueDate: "2026-10-16",
  },
  {
    title: "Renew passport before the Lisbon trip",
    notes: "Photos are in the desk drawer. Check the fee first.",
    dueDate: "2026-10-24",
  },
  {
    title: "Draft the agenda for the budget review",
    dueDate: "2026-10-21",
  },
  {
    title:
      "Get three quotes for repointing the brickwork on the back wall, and ask each one about scaffolding",
    dueDate: "2026-11-06",
  },
  { title: "Book a dentist check-up" },
  { title: "Return the library books", completed: true, dueDate: "2026-10-17" },
  { title: "Pick up the dry cleaning", completed: true },
]);

/** One task opened on its detail screen: several lines of notes, a due date, and edits behind it. */
export const detailTask: Task = makeTask({
  id: "00000000-0000-4000-8000-000000000003",
  title: "Renew passport before the Lisbon trip",
  notes:
    "Photos are in the desk drawer. Check the fee first.\nThe form wants the old passport number, so dig that out too.\nPost office on Elm Street is open until 5:30.",
  dueDate: "2026-10-24",
  version: 3,
  createdAt: "2026-10-12T08:30:00Z",
  updatedAt: "2026-10-18T17:05:00Z",
});

/** A search term that matches two tasks, and those matches in rank order. */
export const searchTerm = "budget";

/** The tasks that match `searchTerm`. */
export const searchMatches: readonly Task[] = tasks.filter((task) =>
  task.title.toLowerCase().includes(searchTerm),
);

/** A search term that matches nothing. */
export const unmatchedTerm = "plumber";

const ignore = (): void => undefined;

/** `TaskListView` props for the ready list with callbacks that do nothing; callers override what they need. */
export const taskListProps = (overrides: Partial<TaskListViewProps> = {}): TaskListViewProps => ({
  content: { status: "ready", tasks },
  today,
  query: "",
  searchPending: false,
  pendingCreate: null,
  failure: null,
  onQueryChange: ignore,
  onCreate: ignore,
  onToggle: ignore,
  onMove: ignore,
  onRetry: ignore,
  onDismissFailure: ignore,
  ...overrides,
});

/** `TaskDetailView` props for `detailTask` at rest, with callbacks that do nothing. */
export const taskDetailProps = (
  overrides: Partial<TaskDetailViewProps> = {},
): TaskDetailViewProps => ({
  content: { status: "ready", task: detailTask },
  today,
  saving: false,
  deleting: false,
  failure: null,
  onSave: ignore,
  onToggle: ignore,
  onDelete: ignore,
  ...overrides,
});
