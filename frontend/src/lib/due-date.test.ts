import { describe, expect, it } from "vitest";
import { dueLabel, formatDay, longDate } from "./due-date.ts";

const today = "2026-10-19";

describe("longDate", () => {
  it("spells out the weekday and date, the way a ledger page is headed", () => {
    expect(longDate(today)).toBe("Monday, October 19");
  });
});

describe("formatDay", () => {
  it("gives the weekday and date of a timestamp, as a ledger dates an entry", () => {
    expect(formatDay("2026-10-12T08:30:00Z", today)).toBe("Mon, Oct 12");
  });
});

describe("dueLabel", () => {
  it("flags an open task whose date has passed", () => {
    expect(dueLabel("2026-10-16", today, false)).toEqual({
      text: "Overdue · Fri, Oct 16",
      tone: "alert",
    });
  });

  it("calls out a task due today", () => {
    expect(dueLabel("2026-10-19", today, false)).toEqual({ text: "Due today", tone: "emphasis" });
  });

  it("names tomorrow", () => {
    expect(dueLabel("2026-10-20", today, false)).toEqual({ text: "Due tomorrow", tone: "quiet" });
  });

  it("gives the weekday and date for a later day this year", () => {
    expect(dueLabel("2026-10-24", today, false)).toEqual({
      text: "Due Sat, Oct 24",
      tone: "quiet",
    });
  });

  it("adds the year when the date falls in another year", () => {
    expect(dueLabel("2027-01-08", today, false).text).toBe("Due Fri, Jan 8, 2027");
  });

  it("never marks a completed task as overdue", () => {
    expect(dueLabel("2026-10-16", today, true)).toEqual({
      text: "Due Fri, Oct 16",
      tone: "quiet",
    });
  });
});
