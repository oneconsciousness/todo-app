import { addTask, expect, signUp, taskTitles, test } from "./fixtures.ts";

// A date in next year, so the screen spells it with its year whatever day the suite runs.
const nextYear = new Date().getFullYear() + 1;
const dueDate = `${String(nextYear)}-03-14`;
const dueText = `Due ${new Intl.DateTimeFormat("en-US", {
  weekday: "short",
  month: "short",
  day: "numeric",
  year: "numeric",
  timeZone: "UTC",
}).format(new Date(`${dueDate}T00:00:00Z`))}`;

test("creates a task, edits every field on the detail screen and completes it", async ({
  page,
}) => {
  await signUp(page);
  await addTask(page, "Draft the talk");
  await taskTitles(page).filter({ hasText: "Draft the talk" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Draft the talk" })).toBeVisible();

  await page.getByRole("button", { name: "Edit task" }).click();
  await page.getByLabel("Title").fill("Rehearse the talk");
  await page.getByLabel("Due date").fill(dueDate);
  await page.getByLabel("Notes").fill("Twice through, once with a timer.");
  await page.getByRole("button", { name: "Save changes" }).click();

  await expect(page.getByRole("heading", { level: 1, name: "Rehearse the talk" })).toBeVisible();
  await expect(page.getByText(dueText)).toBeVisible();
  await expect(page.getByText("Twice through, once with a timer.")).toBeVisible();

  const completed = page.getByRole("checkbox", { name: "Completed: Rehearse the talk" });
  // `check()` insists the box flips during the click; the app flips it a moment later, once the update is queued.
  await completed.click();
  await expect(completed).toBeChecked();
  await expect(page.getByText("Done", { exact: true })).toBeVisible();

  await page.getByRole("link", { name: "All tasks" }).click();
  await expect(taskTitles(page)).toHaveText(["Rehearse the talk"]);
  await expect(page.getByRole("checkbox", { name: "Completed: Rehearse the talk" })).toBeChecked();
});
