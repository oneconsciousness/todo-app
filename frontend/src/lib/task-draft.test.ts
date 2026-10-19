import { describe, expect, it } from "vitest";
import { makeTask } from "../test/fixtures.ts";
import { taskDraftSchema } from "./schema/task.ts";
import { changedFieldNames, changesFrom, draftFrom } from "./task-draft.ts";

const task = makeTask({
  title: "Renew passport",
  notes: "Photos in the drawer.",
  dueDate: "2026-10-24",
});

describe("taskDraftSchema", () => {
  it("reads an empty due date as no due date", () => {
    expect(
      taskDraftSchema.parse({ title: "Renew passport", notes: "", dueDate: "" }).dueDate,
    ).toBeNull();
  });

  it("rejects a due date that is not a calendar date", () => {
    expect(
      taskDraftSchema.safeParse({ title: "Renew passport", notes: "", dueDate: "2026-02-30" }).error
        ?.issues[0]?.message,
    ).toBe("Pick a date from the calendar.");
  });
});

describe("draftFrom", () => {
  it("starts the form from the task, with an empty field for no due date", () => {
    expect(draftFrom({ ...task, dueDate: null })).toEqual({
      title: "Renew passport",
      notes: "Photos in the drawer.",
      dueDate: "",
    });
  });
});

describe("changesFrom", () => {
  it("keeps only the fields the edit changed", () => {
    const edit = { title: "Renew passport", notes: "Photos in the drawer.", dueDate: null };
    expect(changesFrom(task, edit)).toEqual({ dueDate: null });
  });

  it("finds nothing to send when nothing changed", () => {
    expect(
      changesFrom(task, { title: task.title, notes: task.notes, dueDate: task.dueDate }),
    ).toEqual({});
  });
});

describe("changedFieldNames", () => {
  it("names, in plain words, what changed between two versions", () => {
    const newer = { ...task, title: "Renew both passports", dueDate: "2026-10-23", version: 2 };
    expect(changedFieldNames(task, newer)).toEqual(["title", "due date"]);
  });
});
