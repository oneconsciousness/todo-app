import { describe, expect, it } from "vitest";
import { credentialsSchema, userSchema } from "./auth.ts";

const valid = { email: "maya@example.com", password: "correct horse battery" };

const firstMessage = (input: unknown): string | undefined =>
  credentialsSchema.safeParse(input).error?.issues[0]?.message;

describe("credentialsSchema", () => {
  it("trims the email", () => {
    expect(credentialsSchema.parse({ ...valid, email: "  maya@example.com " }).email).toBe(
      "maya@example.com",
    );
  });

  it("asks for an email address it can use", () => {
    expect(firstMessage({ ...valid, email: "maya@" })).toBe(
      "Enter an email address like name@example.com.",
    );
  });

  it("rejects an email longer than 254 characters", () => {
    expect(
      credentialsSchema.safeParse({ ...valid, email: `${"m".repeat(250)}@x.io` }).success,
    ).toBe(false);
  });

  it("asks for at least 12 characters of password", () => {
    expect(firstMessage({ ...valid, password: "x".repeat(11) })).toBe(
      "Use at least 12 characters.",
    );
  });

  it("caps the password at 128 characters", () => {
    expect(firstMessage({ ...valid, password: "x".repeat(129) })).toBe(
      "Use 128 characters or fewer.",
    );
  });

  it("keeps spaces in a password, because they are part of it", () => {
    expect(credentialsSchema.parse({ ...valid, password: "  twelve chars  " }).password).toBe(
      "  twelve chars  ",
    );
  });
});

describe("userSchema", () => {
  it("parses the signed-in user", () => {
    const user = { id: "3f0c6f7e-8a51-4f7a-9d64-2f0b9c1e5a10", email: "maya@example.com" };
    expect(userSchema.parse(user)).toEqual(user);
  });
});
