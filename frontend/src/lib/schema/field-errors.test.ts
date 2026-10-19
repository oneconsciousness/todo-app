import { describe, expect, it } from "vitest";
import { z } from "zod";
import { fieldErrors, serverFieldErrors } from "./field-errors.ts";

const schema = z.object({
  name: z
    .string()
    .min(2, "Too short.")
    .regex(/^[a-z]+$/, "Lowercase only."),
  age: z.int("Whole years."),
});

describe("fieldErrors", () => {
  it("keeps the first message for each field that failed", () => {
    const result = schema.safeParse({ name: "A", age: 1.5 });
    expect(result.success).toBe(false);
    expect(result.error && fieldErrors(result.error)).toEqual({
      name: "Too short.",
      age: "Whole years.",
    });
  });
});

describe("serverFieldErrors", () => {
  it("keeps the server's first message for each field the form has", () => {
    const details = [
      { field: "email", message: "Reserved domain." },
      { field: "email", message: "Too long." },
      { field: "nickname", message: "Unknown field." },
      { field: null, message: "Bad request." },
    ];
    expect(serverFieldErrors(details, ["email", "password"])).toEqual({
      email: "Reserved domain.",
    });
  });
});
