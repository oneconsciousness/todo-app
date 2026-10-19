import { searchMatches, searchTerm, taskListProps, unmatchedTerm } from "../src/test/fixtures.ts";
import type { TaskListViewProps } from "../src/views/task-list-view.tsx";

/** One state of a screen, as the gallery shows it. */
export interface ScreenState<Props> {
  readonly id: string;
  readonly title: string;
  readonly note: string;
  readonly props: Props;
}

/** Every state of the task list the spec implies, built from the shared fixtures. */
export const taskListStates: readonly ScreenState<TaskListViewProps>[] = [
  {
    id: "ready",
    title: "Ready",
    note: "Open and completed tasks, with due dates read against Monday, October 19. Drag a handle to reorder, or focus it and press Space.",
    props: taskListProps(),
  },
  {
    id: "adding",
    title: "Adding a task",
    note: "The new task shows at the top while the server saves it. Add task waits until it is done.",
    props: taskListProps({ pendingCreate: "Order a new bike lock" }),
  },
  {
    id: "search-matches",
    title: "Searching, with matches",
    note: "Matches keep their list order. The handles are gone, because reordering is off while a search is active (D6).",
    props: taskListProps({
      query: searchTerm,
      content: { status: "ready", tasks: searchMatches },
    }),
  },
  {
    id: "search-loading",
    title: "Searching, results loading",
    note: "The previous results stay on screen while the next ones load (D7). The glass in the search box breathes.",
    props: taskListProps({ query: searchTerm, searchPending: true }),
  },
  {
    id: "search-empty",
    title: "Searching, no matches",
    note: "Says what was searched and where, and offers the whole list back.",
    props: taskListProps({ query: unmatchedTerm, content: { status: "ready", tasks: [] } }),
  },
  {
    id: "action-failed",
    title: "An action failed",
    note: "A move failed and the list went back to how it was. The notice says what failed and offers a retry.",
    props: taskListProps({
      failure: {
        message: "Couldn't move “Book a dentist check-up”. The list is back as it was.",
        onRetry: () => undefined,
      },
    }),
  },
  {
    id: "loading",
    title: "Loading",
    note: "Ruled placeholder lines hold the shape of the list until the tasks arrive.",
    props: taskListProps({ content: { status: "loading" } }),
  },
  {
    id: "empty",
    title: "Empty",
    note: "A new account. The quick add above is the way in.",
    props: taskListProps({ content: { status: "ready", tasks: [] } }),
  },
  {
    id: "load-error",
    title: "Couldn't load",
    note: "The list could not load. The message comes from the error; Try again refetches.",
    props: taskListProps({
      content: { status: "error", message: "The server didn't answer. Check your connection." },
    }),
  },
];
