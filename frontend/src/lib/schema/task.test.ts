import { describe, expect, it } from "vitest";
import { taskListSchema, taskSchema, titleSchema } from "./task.ts";

const wireTask = {
  id: "3f0c6f7e-8a51-4f7a-9d64-2f0b9c1e5a10",
  title: "Renew passport",
  notes: "",
  completed: false,
  dueDate: "2026-10-24",
  rank: "a0",
  version: 1,
  createdAt: "2026-10-18T09:12:00Z",
  updatedAt: "2026-10-18T09:12:00Z",
};

describe("taskSchema", () => {
  it("parses a task as the API sends it", () => {
    expect(taskSchema.parse(wireTask)).toEqual(wireTask);
  });

  it("accepts a task without a due date", () => {
    expect(taskSchema.parse({ ...wireTask, dueDate: null }).dueDate).toBeNull();
  });

  it("rejects notes longer than 5,000 characters", () => {
    expect(taskSchema.safeParse({ ...wireTask, notes: "x".repeat(5001) }).success).toBe(false);
  });

  it("rejects a due date that is not a calendar date", () => {
    expect(taskSchema.safeParse({ ...wireTask, dueDate: "24/10/2026" }).success).toBe(false);
  });
});

describe("titleSchema", () => {
  it("trims the title", () => {
    expect(titleSchema.parse("  Renew passport  ")).toBe("Renew passport");
  });

  it("asks for a title when only spaces are given", () => {
    expect(titleSchema.safeParse("   ").error?.issues[0]?.message).toBe("Add a title.");
  });

  it("rejects a title longer than 200 characters", () => {
    expect(titleSchema.safeParse("x".repeat(201)).error?.issues[0]?.message).toBe(
      "Keep the title to 200 characters.",
    );
  });
});

describe("taskListSchema", () => {
  it("reads the items envelope", () => {
    expect(taskListSchema.parse({ items: [wireTask] }).items).toHaveLength(1);
  });
});
