import { addTask, expect, signOut, signUp, taskList, taskTitles, test } from "./fixtures.ts";

test("signs up, signs out, signs back in, and a second account sees none of the first account's tasks", async ({
  page,
}) => {
  const first = await signUp(page);
  await addTask(page, "Renew the passport");
  await signOut(page);

  await page.getByLabel("Email").fill(first.email);
  await page.getByLabel("Password").fill(first.password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(taskTitles(page)).toHaveText(["Renew the passport"]);

  await signOut(page);
  await signUp(page);
  await expect(page.getByText("No tasks yet")).toBeVisible();
  await expect(taskList(page)).toHaveCount(0);
});
