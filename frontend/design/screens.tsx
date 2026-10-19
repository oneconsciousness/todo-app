import type { ReactNode } from "react";
import { AppShell } from "../src/components/app-shell.tsx";
import {
  detailTask,
  searchMatches,
  searchTerm,
  taskDetailProps,
  taskListProps,
  unmatchedTerm,
} from "../src/test/fixtures.ts";
import { ErrorView } from "../src/views/error-view.tsx";
import { NotFoundView } from "../src/views/not-found-view.tsx";
import { SignInView, type SignInViewProps } from "../src/views/sign-in-view.tsx";
import { SignUpView, type SignUpViewProps } from "../src/views/sign-up-view.tsx";
import { TaskDetailView, type TaskDetailViewProps } from "../src/views/task-detail-view.tsx";
import { TaskListView, type TaskListViewProps } from "../src/views/task-list-view.tsx";
import { Scripted, type Steps } from "./scripted.tsx";

/** One state of a screen: a name, what it shows, and how to draw it (once per frame). */
export interface ScreenState {
  readonly id: string;
  readonly title: string;
  readonly note: string;
  readonly draw: () => ReactNode;
}

/** A screen of the app with every state the spec implies. */
export interface Screen {
  readonly id: string;
  readonly title: string;
  readonly lead: string;
  readonly states: readonly ScreenState[];
}

const ignore = (): void => undefined;

const signedIn = (view: ReactNode) => (
  <AppShell account={{ email: "maya@example.com", signingOut: false, onSignOut: ignore }}>
    {view}
  </AppShell>
);

const list = (props: TaskListViewProps) => () => signedIn(<TaskListView {...props} />);

const detail = (props: TaskDetailViewProps) => () => signedIn(<TaskDetailView {...props} />);

const scriptedDetail = (script: (steps: Steps<TaskDetailViewProps>) => Promise<void>) => () =>
  signedIn(
    <Scripted
      initial={taskDetailProps()}
      render={(props) => <TaskDetailView {...props} />}
      script={script}
    />,
  );

const editTitle = async (steps: Steps<TaskDetailViewProps>, title: string) => {
  await steps.press("Edit task");
  await steps.fill("Title", title);
};

const signIn =
  (initial: SignInViewProps, script?: (steps: Steps<SignInViewProps>) => Promise<void>) => () => (
    <Scripted
      initial={initial}
      render={(props) => <SignInView {...props} />}
      script={script ?? (() => Promise.resolve())}
    />
  );

const signUp =
  (initial: SignUpViewProps, script?: (steps: Steps<SignUpViewProps>) => Promise<void>) => () => (
    <Scripted
      initial={initial}
      render={(props) => <SignUpView {...props} />}
      script={script ?? (() => Promise.resolve())}
    />
  );

const signInIdle: SignInViewProps = { submitting: false, failure: null, onSubmit: ignore };
const signUpIdle: SignUpViewProps = { submitting: false, failure: null, onSubmit: ignore };

const fillCredentials = async (steps: Steps<SignInViewProps> | Steps<SignUpViewProps>) => {
  await steps.fill("Email", "maya@example.com");
  await steps.fill("Password", "correct horse battery");
};

/** Every screen in every state, built from the shared fixtures and drawn by the real views. */
export const screens: readonly Screen[] = [
  {
    id: "sign-in",
    title: "Sign in",
    lead: "The landing page, and the first thing a reviewer sees: the ledger opened at its title page.",
    states: [
      {
        id: "sign-in-idle",
        title: "Idle",
        note: "The cloth cover with the title tooled in gilt, and the first page holding the form.",
        draw: signIn(signInIdle),
      },
      {
        id: "sign-in-submitting",
        title: "Submitting",
        note: "The form holds while the server checks the password; the button says what is happening.",
        draw: signIn(signInIdle, async (steps) => {
          await fillCredentials(steps);
          await steps.update({ submitting: true });
        }),
      },
      {
        id: "sign-in-field-errors",
        title: "Field errors",
        note: "Checked by credentialsSchema, the schema the API layer uses, and shown next to each field.",
        draw: signIn(signInIdle, async (steps) => {
          await steps.fill("Email", "maya@");
          await steps.fill("Password", "short");
          await steps.press("Sign in");
        }),
      },
      {
        id: "sign-in-wrong-credentials",
        title: "Wrong email or password (401)",
        note: "The email stays filled in; the message doesn't say which of the two was wrong.",
        draw: signIn({
          ...signInIdle,
          initialEmail: "maya@example.com",
          failure: "wrong-credentials",
        }),
      },
    ],
  },
  {
    id: "sign-up",
    title: "Create an account",
    lead: "The same title page, asking for a new password of 12 to 128 characters.",
    states: [
      {
        id: "sign-up-idle",
        title: "Idle",
        note: "The password hint is read out with the field.",
        draw: signUp(signUpIdle),
      },
      {
        id: "sign-up-submitting",
        title: "Submitting",
        note: "The form holds while the account is created.",
        draw: signUp(signUpIdle, async (steps) => {
          await fillCredentials(steps);
          await steps.update({ submitting: true });
        }),
      },
      {
        id: "sign-up-field-errors",
        title: "Field errors",
        note: "A short password is caught before anything is sent.",
        draw: signUp(signUpIdle, async (steps) => {
          await steps.fill("Email", "maya@example.com");
          await steps.fill("Password", "lisbon2026");
          await steps.press("Create account");
        }),
      },
      {
        id: "sign-up-email-taken",
        title: "Email already registered (409)",
        note: "Offers to sign in instead, right where the problem is reported.",
        draw: signUp(signUpIdle, async (steps) => {
          await fillCredentials(steps);
          await steps.update({ failure: "email-taken" });
        }),
      },
    ],
  },
  {
    id: "task-list",
    title: "Task list",
    lead: "One ledger page on the desk, under the binding band: search, quick add, and the ruled list.",
    states: [
      {
        id: "task-list-ready",
        title: "Ready",
        note: "Open and completed tasks, with due dates read against Monday, October 19. Drag a handle to reorder, or focus it and press Space.",
        draw: list(taskListProps()),
      },
      {
        id: "task-list-adding",
        title: "Adding a task",
        note: "The new task shows at the top while the server saves it. Add task waits until it is done.",
        draw: list(taskListProps({ pendingCreate: "Order a new bike lock" })),
      },
      {
        id: "task-list-search-matches",
        title: "Searching, with matches",
        note: "Matches keep their list order. The handles are gone, because reordering is off while a search is active (D6).",
        draw: list(
          taskListProps({ query: searchTerm, content: { status: "ready", tasks: searchMatches } }),
        ),
      },
      {
        id: "task-list-search-loading",
        title: "Searching, results loading",
        note: "The previous results stay on screen while the next ones load (D7). The glass in the search box breathes.",
        draw: list(taskListProps({ query: searchTerm, searchPending: true })),
      },
      {
        id: "task-list-search-empty",
        title: "Searching, no matches",
        note: "Says what was searched and where, and offers the whole list back.",
        draw: list(
          taskListProps({ query: unmatchedTerm, content: { status: "ready", tasks: [] } }),
        ),
      },
      {
        id: "task-list-action-failed",
        title: "An action failed",
        note: "A move failed and the list went back to how it was. The notice says what failed and offers a retry.",
        draw: list(
          taskListProps({
            failure: {
              message: "Couldn't move “Book a dentist check-up”. The list is back as it was.",
              onRetry: ignore,
            },
          }),
        ),
      },
      {
        id: "task-list-loading",
        title: "Loading",
        note: "Ruled placeholder lines hold the shape of the list until the tasks arrive.",
        draw: list(taskListProps({ content: { status: "loading" } })),
      },
      {
        id: "task-list-empty",
        title: "Empty",
        note: "A new account. The quick add above is the way in.",
        draw: list(taskListProps({ content: { status: "ready", tasks: [] } })),
      },
      {
        id: "task-list-load-error",
        title: "Couldn't load",
        note: "The list could not load. Try again refetches.",
        draw: list(
          taskListProps({
            content: {
              status: "error",
              message: "The server didn't answer. Check your connection.",
            },
          }),
        ),
      },
    ],
  },
  {
    id: "task-detail",
    title: "Task detail",
    lead: "One entry on its own page: read it, tick it off, edit it, or delete it after a confirm step.",
    states: [
      {
        id: "task-detail-viewing",
        title: "Viewing",
        note: "Status, entered and changed dates on the ruling; notes on ruled lines.",
        draw: detail(taskDetailProps()),
      },
      {
        id: "task-detail-done",
        title: "Viewing a completed task",
        note: "Ticked off: the title is struck through in faded ink.",
        draw: detail(
          taskDetailProps({
            content: { status: "ready", task: { ...detailTask, completed: true } },
          }),
        ),
      },
      {
        id: "task-detail-editing",
        title: "Editing",
        note: "Every field in one form, validated by taskDraftSchema. The notes field is ruled like the page.",
        draw: scriptedDetail(async (steps) => {
          await steps.press("Edit task");
        }),
      },
      {
        id: "task-detail-field-errors",
        title: "Field errors",
        note: "An empty title is caught before anything is sent.",
        draw: scriptedDetail(async (steps) => {
          await editTitle(steps, "");
          await steps.press("Save changes");
        }),
      },
      {
        id: "task-detail-saving",
        title: "Saving",
        note: "Edits wait for the server and say so (spec, Screens). Only the changed fields are sent, with If-Match.",
        draw: scriptedDetail(async (steps) => {
          await editTitle(steps, "Renew passport and book the Lisbon flights");
          await steps.press("Save changes");
          await steps.update({ saving: true });
        }),
      },
      {
        id: "task-detail-changed-elsewhere",
        title: "Changed elsewhere (D17)",
        note: "Another tab saved a newer version while this one had unsaved edits. The notice names what changed.",
        draw: scriptedDetail(async (steps) => {
          await editTitle(steps, "Renew passport and book the Lisbon flights");
          await steps.update({
            content: {
              status: "ready",
              task: {
                ...detailTask,
                dueDate: "2026-10-23",
                version: detailTask.version + 1,
                updatedAt: "2026-10-19T09:41:00Z",
              },
            },
          });
        }),
      },
      {
        id: "task-detail-save-failed",
        title: "Save failed",
        note: "The draft stays, so nothing typed is lost; the notice says what to do.",
        draw: scriptedDetail(async (steps) => {
          await editTitle(steps, "Renew passport and book the Lisbon flights");
          await steps.press("Save changes");
          await steps.update({
            failure: "Couldn't save your changes. Check your connection and try again.",
          });
        }),
      },
      {
        id: "task-detail-delete-confirm",
        title: "Delete, confirming",
        note: "The confirm step is built into the page. Focus lands on Keep it, so a stray Enter backs out.",
        draw: scriptedDetail(async (steps) => {
          await steps.press("Delete");
        }),
      },
      {
        id: "task-detail-loading",
        title: "Loading",
        note: "Placeholder lines while the task loads.",
        draw: detail(taskDetailProps({ content: { status: "loading" } })),
      },
      {
        id: "task-detail-not-found",
        title: "Not found",
        note: "The same answer for a deleted task and for someone else's, so no other user's id is ever confirmed.",
        draw: detail(taskDetailProps({ content: { status: "not-found" } })),
      },
    ],
  },
  {
    id: "not-found",
    title: "Not found",
    lead: "Any address the app doesn't know.",
    states: [
      {
        id: "not-found-page",
        title: "Unknown page",
        note: "Stamped like a ledger line that was never posted, with the way back.",
        draw: () => signedIn(<NotFoundView subject="page" />),
      },
    ],
  },
  {
    id: "error",
    title: "Error",
    lead: "What the route error boundary shows when a screen fails to render.",
    states: [
      {
        id: "error-boundary",
        title: "Something went wrong",
        note: "Says the tasks are safe, and offers to try again or go to the tasks.",
        draw: () => signedIn(<ErrorView onRetry={ignore} onGoToTasks={ignore} />),
      },
    ],
  },
];
