import type { ReactNode } from "react";
import { Button, type ButtonVariant } from "../src/components/ui/button.tsx";
import { Checkbox } from "../src/components/ui/checkbox.tsx";
import { DragHandleMark, dropSlotClass, liftedClass } from "../src/components/ui/sortable-list.tsx";
import { TaskRow, taskLineClass } from "../src/components/ui/task-row.tsx";
import { tasks, today } from "../src/test/fixtures.ts";
import type { ScreenState } from "./screens.tsx";
import { Scripted } from "./scripted.tsx";

const ignore = (): void => undefined;
const [landlord, maya, passport] = tasks;

const forced = (draw: () => ReactNode, marks: readonly (readonly [string, string])[]) => () => (
  <Scripted
    initial={{}}
    render={draw}
    script={async (steps) => {
      for (const [selector, attribute] of marks) await steps.force(selector, attribute);
    }}
  />
);

const Sheet = ({ children }: { readonly children: ReactNode }) => (
  <div className="@container rounded-sheet bg-sheet py-4 shadow-sheet">{children}</div>
);

const Line = ({
  task,
  mark,
  className = "",
}: {
  readonly task: (typeof tasks)[number] | undefined;
  readonly mark?: string;
  readonly className?: string;
}) =>
  task ? (
    <div data-mark={mark} className={`${taskLineClass(true)} ${className}`}>
      <TaskRow task={task} today={today} handle={<DragHandleMark />} onToggle={ignore} />
    </div>
  ) : null;

const ticks = [
  { mark: "open", label: "Open", checked: false },
  { mark: "pressed", label: "Pressed", checked: false },
  { mark: "ticked", label: "Ticked", checked: true },
  { mark: "focused", label: "Focused", checked: true },
] as const;

const buttonStates = ["Rest", "Hover", "Focus", "Disabled"] as const;

const stateProps = (state: (typeof buttonStates)[number]) =>
  ({
    Rest: {},
    Hover: { "data-hover": "" },
    Focus: { "data-focus-visible": "" },
    Disabled: { disabled: true },
  })[state];

const buttonRows: readonly { readonly variant: ButtonVariant; readonly label: string }[] = [
  { variant: "primary", label: "Add task" },
  { variant: "secondary", label: "Show all tasks" },
  { variant: "ghost", label: "Dismiss" },
  { variant: "danger", label: "Delete task" },
];

const ButtonGrid = ({
  rows,
  band = false,
}: {
  readonly rows: typeof buttonRows;
  readonly band?: boolean;
}) => (
  <div
    className={`grid grid-cols-2 gap-4 p-4 @wide:grid-cols-4 ${band ? "rounded-sheet binding" : ""}`}
  >
    {rows.flatMap(({ variant, label }) =>
      buttonStates.map((state) => (
        <div key={`${variant}-${state}`} className="flex flex-col items-start gap-1">
          <Button variant={variant} {...stateProps(state)}>
            {label}
          </Button>
          <span className={`text-caption ${band ? "" : "text-ink-muted"}`}>
            {variant} · {state.toLowerCase()}
          </span>
        </div>
      )),
    )}
  </div>
);

/** The interaction states a still screen can't show, forced on the real components. */
export const interactionStates: readonly ScreenState[] = [
  {
    id: "interaction-lines",
    title: "Lines: rest, hover, keyboard focus",
    note: "The first line at rest, the second under the pointer, the third with its title focused from the keyboard: the line shades and the gilt ring marks the link.",
    draw: forced(
      () => (
        <Sheet>
          <Line task={landlord} />
          <Line task={maya} mark="hover" />
          <Line task={passport} mark="focus" />
        </Sheet>
      ),
      [
        ['[data-mark="hover"]', "data-hover"],
        ['[data-mark="focus"] a', "data-focus-visible"],
      ],
    ),
  },
  {
    id: "interaction-reorder",
    title: "Reordering: the lifted line and its drop slot",
    note: "While a line is carried it lifts off the page on the shade token, and its place becomes a dashed slot that moves through the list to show where it will land.",
    draw: () => (
      <Sheet>
        <Line task={landlord} />
        <div className="relative">
          <Line task={maya} className={dropSlotClass} />
          <div className="absolute inset-x-0 top-6 z-10 translate-x-2">
            <Line task={maya} className={liftedClass} />
          </div>
        </div>
        <Line task={passport} />
      </Sheet>
    ),
  },
  {
    id: "interaction-tick",
    title: "Tick box: open, pressed, ticked, focused",
    note: "Pressing sinks the box a little; on release the tick draws itself on. The 44px hit area is the whole cell around the 20px box.",
    draw: forced(
      () => (
        <Sheet>
          <div className="flex flex-wrap gap-8 px-4">
            {ticks.map(({ mark, label, checked }) => (
              <div key={mark} data-mark={mark} className="flex flex-col items-center gap-1">
                <Checkbox label={label} checked={checked} onChange={ignore} />
                <span className="text-caption text-ink-muted">{label}</span>
              </div>
            ))}
          </div>
        </Sheet>
      ),
      [
        ['[data-mark="pressed"] input', "data-active"],
        ['[data-mark="focused"] input', "data-focus-visible"],
      ],
    ),
  },
  {
    id: "interaction-buttons",
    title: "Buttons: rest, hover, focus, disabled",
    note: "Five weights, each at least 44px tall. On the binding band, Sign out uses the binding weight and the focus ring turns gilt to stay visible.",
    draw: () => (
      <div className="@container flex flex-col gap-4">
        <Sheet>
          <ButtonGrid rows={buttonRows} />
        </Sheet>
        <ButtonGrid rows={[{ variant: "binding", label: "Sign out" }]} band />
      </div>
    ),
  },
];
