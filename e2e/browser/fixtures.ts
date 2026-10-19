import { randomUUID } from "node:crypto";
import {
  type ConsoleMessage,
  type Locator,
  type Page,
  test as base,
  expect,
} from "@playwright/test";

declare global {
  interface Window {
    /** Set by the fixture through `page.exposeFunction`; reports a blocked resource back to the test. */
    reportCspViolation?: (report: string) => Promise<void>;
  }
}

/** An account a test signed up, so it can sign back in. */
export interface Account {
  readonly email: string;
  readonly password: string;
}

// Chromium logs each failed response itself; a 401 from the API is an answer the app expects (a visitor), not a fault.
const isExpectedApiAnswer = (message: ConsoleMessage): boolean =>
  message.text().startsWith("Failed to load resource: the server responded with a status of 401") &&
  new URL(message.location().url, "http://localhost").pathname.startsWith("/api/");

/**
 * Playwright's test, with a page that fails the test on any `console.error`, uncaught exception or CSP violation.
 * Those are what only a real browser against the real stack shows, such as the nginx CSP blocking an inline style.
 */
export const test = base.extend({
  page: async ({ page }, use) => {
    const problems: string[] = [];
    page.on("console", (message) => {
      if (message.type() === "error" && !isExpectedApiAnswer(message))
        problems.push(`console.error: ${message.text()}`);
    });
    page.on("pageerror", (error) => {
      problems.push(`uncaught: ${error.message}`);
    });
    // Init scripts and exposed functions run outside the page's CSP: https://playwright.dev/docs/api/class-page#page-add-init-script
    await page.exposeFunction("reportCspViolation", (report: string) => {
      problems.push(`CSP violation: ${report}`);
    });
    await page.addInitScript(() => {
      document.addEventListener("securitypolicyviolation", (event) => {
        void window.reportCspViolation?.(
          `${event.effectiveDirective} blocked ${event.blockedURI || "inline"} in ${event.sourceFile}:${String(event.lineNumber)}`,
        );
      });
    });
    await use(page);
    expect(problems, "the browser reported errors").toEqual([]);
  },
});

export { expect };

/** A fresh account for one test: a unique address on the reserved example.com domain. */
export const newAccount = (): Account => ({
  email: `e2e-${randomUUID()}@example.com`,
  password: "browser-journey-password",
});

/** Create an account through the sign-up screen and wait for the task list it lands on. */
export const signUp = async (page: Page, account: Account = newAccount()): Promise<Account> => {
  await page.goto("/sign-up");
  await page.getByLabel("Email").fill(account.email);
  await page.getByLabel("Password").fill(account.password);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Tasks" })).toBeVisible();
  return account;
};

/** Sign out from the masthead and wait for the sign-in screen. */
export const signOut = async (page: Page): Promise<void> => {
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Sign in" })).toBeVisible();
};

/** The ruled list of tasks on the task list screen. */
export const taskList = (page: Page): Locator => page.getByRole("list", { name: "Tasks" });

/** Each task's title link in the list, top to bottom: what the user reads as the order. */
export const taskTitles = (page: Page): Locator => taskList(page).getByRole("link");

/** Add a task with the quick-add form and wait until the server's row replaces the pending one. */
export const addTask = async (page: Page, title: string): Promise<void> => {
  await page.getByRole("textbox", { name: "New task" }).fill(title);
  await page.getByRole("button", { name: "Add task" }).click();
  await expect(taskTitles(page).filter({ hasText: title })).toBeVisible();
  await expect(page.getByRole("button", { name: "Add task" })).toBeEnabled();
};

/** Add tasks in order. New tasks go to the top, so the list shows them in reverse. */
export const addTasks = async (page: Page, titles: readonly string[]): Promise<void> => {
  for (const title of titles) await addTask(page, title);
};

/** The handle that reorders a task by keyboard, mouse or touch. */
export const moveHandle = (page: Page, title: string): Locator =>
  page.getByRole("button", { name: `Move ${title}` });

/** The list row that holds a task. */
export const taskRow = (page: Page, title: string): Locator =>
  taskList(page).getByRole("listitem").filter({ hasText: title });

/** A point on the screen, in CSS pixels from the viewport's top left. */
export interface Point {
  readonly x: number;
  readonly y: number;
}

/** The centre of an element on screen; fails the test when the element has no box. */
export const centreOf = async (locator: Locator): Promise<Point> => {
  const box = await locator.boundingBox();
  if (box === null) throw new Error(`${locator.toString()} is not on screen`);
  return { x: box.x + box.width / 2, y: box.y + box.height / 2 };
};

/**
 * What the list last told screen readers about a carried task. Before anything is picked up, no announcement names a
 * task, so a match means the drag has started.
 */
export const dragAnnouncement = (page: Page, text: string): Locator =>
  page.getByRole("status").filter({ hasText: text });

/** True when the page is wider than the viewport, which would make the user scroll sideways. */
export const scrollsSideways = (page: Page): Promise<boolean> =>
  page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
