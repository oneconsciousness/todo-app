import { addTasks, expect, signOut, signUp, taskTitles, test } from "./fixtures.ts";

test("deletes a task after confirming and signs out", async ({ page }) => {
  await signUp(page);
  await addTasks(page, ["Book the dentist", "Return the library books"]);
  await taskTitles(page).filter({ hasText: "Book the dentist" }).click();

  await page.getByRole("button", { name: "Delete" }).click();
  const confirm = page.getByRole("group", {
    name: "Delete “Book the dentist”? This can't be undone.",
  });
  await confirm.getByRole("button", { name: "Delete task" }).click();

  await expect(page.getByRole("heading", { level: 1, name: "Tasks" })).toBeVisible();
  await expect(taskTitles(page)).toHaveText(["Return the library books"]);
  await page.reload();
  await expect(taskTitles(page)).toHaveText(["Return the library books"]);

  await signOut(page);
  await page.goto("/tasks");
  await expect(page.getByRole("heading", { level: 1, name: "Sign in" })).toBeVisible();
});
