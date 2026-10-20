import {
  addTasks,
  centreOf,
  dragAnnouncement,
  expect,
  moveHandle,
  signUp,
  taskList,
  taskRow,
  taskTitles,
  test,
} from "./fixtures.ts";

test("reorders by keyboard and by mouse, then finds a task by search with reorder turned off", async ({
  page,
}) => {
  await signUp(page);
  await addTasks(page, ["Water the plants", "Call the bank", "Pay the rent"]);
  await expect(taskTitles(page)).toHaveText(["Pay the rent", "Call the bank", "Water the plants"]);

  // Space picks the task up, each arrow moves it one place, and Space drops it.
  await moveHandle(page, "Pay the rent").focus();
  await page.keyboard.press("Space");
  await expect(dragAnnouncement(page, "Pay the rent")).toHaveCount(1);
  // The list drops arrow keys until it has measured the rows after the pickup, so the first move is pressed again
  // until it lands: https://playwright.dev/docs/test-assertions#expecttopass
  await expect(async () => {
    await page.keyboard.press("ArrowDown");
    await expect(dragAnnouncement(page, "Pay the rent is now at position 2 of 3.")).toHaveCount(1, {
      timeout: 1000,
    });
  }).toPass();
  await page.keyboard.press("ArrowDown");
  await expect(dragAnnouncement(page, "Pay the rent is now at position 3 of 3.")).toHaveCount(1);
  await page.keyboard.press("Space");
  await expect(taskTitles(page)).toHaveText(["Call the bank", "Water the plants", "Pay the rent"]);

  // The list only starts a mouse drag after the pointer travels a few pixels, so move in steps.
  const from = await centreOf(moveHandle(page, "Water the plants"));
  const to = await centreOf(taskRow(page, "Call the bank"));
  await page.mouse.move(from.x, from.y);
  await page.mouse.down();
  await page.mouse.move(from.x, to.y, { steps: 10 });
  await page.mouse.up();
  await expect(taskTitles(page)).toHaveText(["Water the plants", "Call the bank", "Pay the rent"]);

  await page.reload();
  await expect(taskTitles(page)).toHaveText(["Water the plants", "Call the bank", "Pay the rent"]);

  await page.getByRole("searchbox", { name: "Search tasks" }).fill("bank");
  await expect(
    page.getByText("1 match for “bank”. Reordering is off while you search."),
  ).toBeVisible();
  await expect(taskTitles(page)).toHaveText(["Call the bank"]);
  await expect(taskList(page).getByRole("button", { name: /^Move / })).toHaveCount(0);
});
