import type { Page } from "@playwright/test";
import {
  type Point,
  addTasks,
  centreOf,
  dragAnnouncement,
  expect,
  moveHandle,
  scrollsSideways,
  signUp,
  taskRow,
  taskTitles,
  test,
} from "./fixtures.ts";

test.use({ viewport: { width: 375, height: 812 }, hasTouch: true });

// Playwright's touchscreen only taps, so a press-and-drag goes through Chromium's own input events:
// https://chromedevtools.github.io/devtools-protocol/tot/Input/#method-dispatchTouchEvent
const dragByTouch = async (page: Page, title: string, from: Point, to: Point): Promise<void> => {
  const cdp = await page.context().newCDPSession(page);
  await cdp.send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [from] });
  // The list picks a task up only after a short press, and announces it to screen readers when it does.
  await expect(dragAnnouncement(page, title)).toHaveCount(1);
  const steps = 10;
  for (let step = 1; step <= steps; step += 1) {
    const share = step / steps;
    await cdp.send("Input.dispatchTouchEvent", {
      type: "touchMove",
      touchPoints: [{ x: from.x + (to.x - from.x) * share, y: from.y + (to.y - from.y) * share }],
    });
  }
  await cdp.send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
  await cdp.detach();
};

test("runs create, reorder by touch and delete at 375 px with no horizontal scroll", async ({
  page,
}) => {
  await signUp(page);
  await addTasks(page, ["Buy stamps", "Post the parcel"]);
  await expect(taskTitles(page)).toHaveText(["Post the parcel", "Buy stamps"]);
  expect(await scrollsSideways(page)).toBe(false);

  await dragByTouch(
    page,
    "Buy stamps",
    await centreOf(moveHandle(page, "Buy stamps")),
    await centreOf(taskRow(page, "Post the parcel")),
  );
  await expect(taskTitles(page)).toHaveText(["Buy stamps", "Post the parcel"]);
  await page.reload();
  await expect(taskTitles(page)).toHaveText(["Buy stamps", "Post the parcel"]);

  await taskTitles(page).filter({ hasText: "Post the parcel" }).tap();
  await expect(page.getByRole("heading", { level: 1, name: "Post the parcel" })).toBeVisible();
  expect(await scrollsSideways(page)).toBe(false);
  await page.getByRole("button", { name: "Delete" }).tap();
  await page.getByRole("button", { name: "Delete task" }).tap();

  await expect(taskTitles(page)).toHaveText(["Buy stamps"]);
  expect(await scrollsSideways(page)).toBe(false);
});
