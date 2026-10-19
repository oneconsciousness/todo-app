import { type ReactNode, useEffect, useRef, useState } from "react";

/** What a gallery script can do to the view it drives: the same things a user does, plus new props. */
export interface Steps<P> {
  /** Press the button whose name (text or aria-label) is given. */
  readonly press: (name: string) => Promise<void>;
  /** Replace the value of the field with the given label, as typing would. */
  readonly fill: (label: string, value: string) => Promise<void>;
  /** Put a state attribute (data-hover, data-focus-visible, data-active) on matching elements. */
  readonly force: (selector: string, attribute: string) => Promise<void>;
  /** Change the view's props, as the container would when the server answers. */
  readonly update: (next: Partial<P>) => Promise<void>;
}

/** Props for `Scripted`. */
export interface ScriptedProps<P> {
  readonly initial: P;
  readonly render: (props: P) => ReactNode;
  readonly script: (steps: Steps<P>) => Promise<void>;
}

const settle = () =>
  new Promise<void>((resolve) => {
    setTimeout(resolve, 0);
  });

const nameOf = (element: Element): string =>
  (element.getAttribute("aria-label") ?? element.textContent).trim();

/**
 * Renders a real view and then drives it once, the way a user would, so a state that lives in the view's local
 * state (editing, a field error, an open confirm) is shown through the same code path as everything else.
 */
export function Scripted<P extends object>({ initial, render, script }: ScriptedProps<P>) {
  const [props, setProps] = useState(initial);
  const root = useRef<HTMLDivElement>(null);
  const ran = useRef(false);

  useEffect(() => {
    const element = root.current;
    if (!element || ran.current) return;
    ran.current = true;
    const steps: Steps<P> = {
      press: async (name) => {
        const button = [...element.querySelectorAll("button")].find((b) => nameOf(b) === name);
        button?.click();
        await settle();
      },
      fill: async (label, value) => {
        const target = [...element.querySelectorAll("label")].find((l) => nameOf(l) === label);
        const field = target ? element.querySelector(`[id="${target.htmlFor}"]`) : null;
        if (field instanceof HTMLInputElement || field instanceof HTMLTextAreaElement) {
          Object.getOwnPropertyDescriptor(Object.getPrototypeOf(field), "value")?.set?.call(
            field,
            value,
          );
          field.dispatchEvent(new Event("input", { bubbles: true }));
        }
        await settle();
      },
      force: async (selector, attribute) => {
        element.querySelectorAll(selector).forEach((match) => {
          match.setAttribute(attribute, "");
        });
        await settle();
      },
      update: async (next) => {
        setProps((current) => ({ ...current, ...next }));
        await settle();
      },
    };
    void script(steps);
  }, [script]);

  return <div ref={root}>{render(props)}</div>;
}
