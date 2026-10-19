import type { ReactNode } from "react";
import { TaskListView } from "../src/views/task-list-view.tsx";
import { Frame } from "./frame.tsx";
import { taskListStates } from "./task-list-states.ts";
import { TokenSheet } from "./token-sheet.tsx";

const direction = [
  {
    term: "Source",
    detail:
      "The bookkeeper's ledger: mid-century American account books and columnar pads, with pale green eye-ease paper, feint blue ruling, a red double rule down the margin, blue-black ink, and a bottle-green cloth binding stamped in gilt.",
  },
  {
    term: "Palette",
    detail:
      "Light is the open page; dark is the closed binding, where the main action turns to gilt. Red appears only as the margin rule and as alert ink, so an overdue date is the one thing that shouts.",
  },
  {
    term: "Type",
    detail:
      "Besley, a Clarendon revival from the age of bound ledgers, for headings only. Libre Franklin, a revival of Franklin Gothic from the same era's printed forms, for everything read at length.",
  },
  {
    term: "Feel",
    detail:
      "Quiet, ruled and exact. Every row sits on a ledger line, right of the red margin, with due dates in their own column on wide screens. Near-square corners, two shadows, short calm motion.",
  },
] as const;

/** The design gallery: the direction, the token sheet, then every screen in every state at phone and desktop width. */
export function Gallery() {
  return (
    <main className="@container flex flex-col gap-16 px-4 py-12 @wide:px-8">
      <header data-section="overview" className="flex max-w-measure flex-col gap-3">
        <p className="text-caption font-medium tracking-caps text-ink-muted uppercase">
          todo-app · Design gallery · Round 1
        </p>
        <h1 className="font-display text-display font-medium text-balance">The ledger</h1>
        <p className="text-lead text-ink-muted">
          One vintage source for every colour, face and rule. Everything below is drawn by the
          components that ship, fed by the fixtures the tests use.
        </p>
      </header>

      <GallerySection title="Direction">
        <dl className="grid max-w-measure gap-x-6 gap-y-4 @wide:grid-cols-[auto_minmax(0,1fr)]">
          {direction.map(({ term, detail }) => (
            <div key={term} className="contents">
              <dt className="font-semibold">{term}</dt>
              <dd className="text-ink-muted">{detail}</dd>
            </div>
          ))}
        </dl>
      </GallerySection>

      <GallerySection title="Tokens">
        <TokenSheet />
      </GallerySection>

      <GallerySection title="Task list">
        {taskListStates.map((state) => (
          <article
            key={state.id}
            id={state.id}
            data-state={state.id}
            className="flex flex-col gap-4"
          >
            <div className="flex max-w-measure flex-col gap-1">
              <h3 className="text-lead font-semibold">{state.title}</h3>
              <p className="text-ink-muted">{state.note}</p>
            </div>
            <div className="flex flex-wrap items-start gap-6">
              <Frame device="phone">
                <TaskListView {...state.props} />
              </Frame>
              <Frame device="desktop">
                <TaskListView {...state.props} />
              </Frame>
            </div>
          </article>
        ))}
      </GallerySection>
    </main>
  );
}

function GallerySection({
  title,
  children,
}: {
  readonly title: string;
  readonly children: ReactNode;
}) {
  return (
    <section
      data-section={title}
      className="flex flex-col gap-12 border-t-3 border-double border-rule-strong pt-8"
    >
      <h2 className="font-display text-title font-medium">{title}</h2>
      {children}
    </section>
  );
}
