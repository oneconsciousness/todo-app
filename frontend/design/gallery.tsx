import type { ReactNode } from "react";
import { Frame } from "./frame.tsx";
import { interactionStates } from "./interaction.tsx";
import { type ScreenState, screens } from "./screens.tsx";
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
      "Light is the open page on a green desk blotter; dark is the closed binding, where the main action turns to gilt. Red appears only as the margin rule and as alert ink, so an overdue date is the one thing that shouts.",
  },
  {
    term: "Type",
    detail:
      "Besley, a Clarendon revival from the age of bound ledgers, for headings and the gilt title only. Libre Franklin, a revival of Franklin Gothic from the same era's printed forms, for everything read at length.",
  },
  {
    term: "Feel",
    detail:
      "A page lying on a desk under a binding band. Every row sits on a ruled line right of the red margin, with due dates in their own ruled column on wide screens. Near-square corners, two shadows by role, short calm motion.",
  },
] as const;

const gutter = "px-4 @wide:px-12";

/** The design gallery: the direction, the token sheet, interaction states, then every screen in every state. */
export function Gallery() {
  return (
    <div className="@container">
      <main className="flex flex-col gap-16 py-12">
        <header data-section="overview" className={`flex flex-col gap-3 ${gutter}`}>
          <p className="text-caption font-medium tracking-caps text-ink-muted uppercase">
            todo-app · Design gallery · Round 1
          </p>
          <h1 className="max-w-measure font-display text-display font-medium text-balance">
            The ledger
          </h1>
          <p className="max-w-measure text-lead text-ink-muted">
            One vintage source for every colour, face and rule. Everything below is drawn by the
            components that ship, fed by the fixtures the tests use.
          </p>
          <nav aria-label="Sections" className="flex flex-wrap gap-x-4 gap-y-1 pt-2 text-caption">
            {["direction", "tokens", "interaction", ...screens.map((screen) => screen.id)].map(
              (id) => (
                <a
                  key={id}
                  href={`#${id}`}
                  className="font-medium text-ink underline decoration-rule-strong underline-offset-4"
                >
                  {id.replace("-", " ")}
                </a>
              ),
            )}
          </nav>
        </header>

        <GallerySection id="direction" title="Direction">
          <dl
            className={`grid max-w-measure gap-x-6 gap-y-4 @wide:grid-cols-[auto_minmax(0,1fr)] ${gutter}`}
          >
            {direction.map(({ term, detail }) => (
              <div key={term} className="contents">
                <dt className="font-semibold">{term}</dt>
                <dd className="text-ink-muted">{detail}</dd>
              </div>
            ))}
          </dl>
        </GallerySection>

        <GallerySection id="tokens" title="Tokens">
          <div className={`flex flex-col gap-12 ${gutter}`}>
            <TokenSheet />
          </div>
        </GallerySection>

        <GallerySection
          id="interaction"
          title="Interaction"
          lead="States a still frame can't catch, forced on the real components with data attributes the app never sets."
        >
          {interactionStates.map((state) => (
            <StateArticle key={state.id} state={state}>
              <div className="max-w-measure">{state.draw()}</div>
            </StateArticle>
          ))}
        </GallerySection>

        {screens.map((screen) => (
          <GallerySection
            key={screen.id}
            id={screen.id}
            title={screen.title}
            lead={screen.lead}
            whole={false}
          >
            {screen.states.map((state) => (
              <StateArticle key={state.id} state={state}>
                <div className="flex flex-wrap items-start gap-6">
                  <Frame device="phone">{state.draw()}</Frame>
                  <Frame device="desktop">{state.draw()}</Frame>
                </div>
              </StateArticle>
            ))}
          </GallerySection>
        ))}
      </main>
    </div>
  );
}

function GallerySection({
  id,
  title,
  lead,
  whole = true,
  children,
}: {
  readonly id: string;
  readonly title: string;
  readonly lead?: string;
  /** False for a screen, whose states are each shot on their own rather than as one long page. */
  readonly whole?: boolean;
  readonly children: ReactNode;
}) {
  return (
    <section
      id={id}
      data-section={whole ? id : undefined}
      className="flex flex-col gap-12 border-t-3 border-double border-rule-strong pt-8"
    >
      <div className={`flex max-w-measure flex-col gap-2 ${gutter}`}>
        <h2 className="font-display text-title font-medium">{title}</h2>
        {lead && <p className="text-ink-muted">{lead}</p>}
      </div>
      {children}
    </section>
  );
}

function StateArticle({
  state,
  children,
}: {
  readonly state: ScreenState;
  readonly children: ReactNode;
}) {
  return (
    <article id={state.id} data-state={state.id} className={`flex flex-col gap-4 py-2 ${gutter}`}>
      <div className="flex max-w-measure flex-col gap-1">
        <h3 className="text-lead font-semibold">{state.title}</h3>
        <p className="text-ink-muted">{state.note}</p>
      </div>
      {children}
    </article>
  );
}
