import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { user } from "./fixtures.ts";

/** A password that passes the form's rules. */
export const password = "correct horse battery";

/** Fill the email and password fields as a user would, then press the form's submit button. */
export const submitCredentials = async (submitLabel: string, email = user.email): Promise<void> => {
  await userEvent.type(screen.getByRole("textbox", { name: "Email" }), email);
  await userEvent.type(screen.getByLabelText("Password"), password);
  await userEvent.click(screen.getByRole("button", { name: submitLabel }));
};
