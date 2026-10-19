import { focusManager } from "@tanstack/react-query";
import { act, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, delay, http } from "msw";
import { afterEach, describe, expect, it, vi } from "vitest";
import { routes } from "../lib/routes.ts";
import { detailTask, tasks } from "../test/fixtures.ts";
import { errorReply } from "../test/handlers.ts";
import { renderApp } from "../test/render-app.tsx";
import { server } from "../test/server.ts";

const taskUrl = `/api/v1/tasks/${detailTask.id}`;
const newer = { ...detailTask, title: "Renew both passports", version: detailTask.version + 1 };

const titleField = () => screen.getByRole("textbox", { name: "Title" });

const openAndEdit = async (title: string) => {
  const app = renderApp(routes.task(detailTask.id));
  await userEvent.click(await screen.findByRole("button", { name: "Edit task" }));
  await userEvent.clear(titleField());
  await userEvent.type(titleField(), title);
  return app;
};

const save = () => userEvent.click(screen.getByRole("button", { name: "Save changes" }));

const confirmDelete = async () => {
  await userEvent.click(await screen.findByRole("button", { name: "Delete" }));
  await userEvent.click(screen.getByRole("button", { name: "Delete task" }));
};

// After a refused save, the next read of the task returns the version someone else saved.
const refusedAs = (reply: () => Response) => {
  const state = { refused: false };
  server.use(
    http.patch(taskUrl, () => {
      state.refused = true;
      return reply();
    }),
    http.get(taskUrl, () => HttpResponse.json(state.refused ? newer : detailTask)),
  );
};

describe("TaskDetailPage", () => {
  afterEach(() => {
    focusManager.setFocused(undefined);
  });

  it("sends If-Match with the draft's base version", async () => {
    const ifMatch = vi.fn<(value: string | null) => void>();
    server.use(
      http.patch(taskUrl, ({ request }) => {
        ifMatch(request.headers.get("If-Match"));
        return HttpResponse.json({ ...detailTask, title: "My title", version: 4 });
      }),
    );
    await openAndEdit("My title");

    await save();

    expect(ifMatch).toHaveBeenCalledWith(`"${String(detailTask.version)}"`);
    expect(await screen.findByRole("heading", { level: 1, name: "My title" })).toBeVisible();
  });

  it("shows changed elsewhere when a newer version arrives under a draft", async () => {
    await openAndEdit("My title");
    server.use(http.get(taskUrl, () => HttpResponse.json(newer)));

    act(() => {
      focusManager.setFocused(false);
      focusManager.setFocused(true);
    });

    expect(await screen.findByRole("alert")).toHaveTextContent("Changed elsewhere");
    expect(titleField()).toHaveValue("My title");
  });

  it("keeps the draft when a reload in the background fails", async () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    const reloads = vi.fn<() => void>();
    await openAndEdit("My title");
    server.use(
      http.get(taskUrl, () => {
        reloads();
        return errorReply(500, "internal_error");
      }),
    );

    act(() => {
      focusManager.setFocused(false);
      focusManager.setFocused(true);
    });
    await waitFor(() => {
      expect(reloads).toHaveBeenCalled();
    });
    await delay(50);

    expect(screen.queryByRole("heading", { name: "Something went wrong" })).not.toBeInTheDocument();
    expect(titleField()).toHaveValue("My title");
  });

  it("shows changed elsewhere after a 412", async () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    refusedAs(() => errorReply(412, "version_mismatch"));
    await openAndEdit("My title");

    await save();

    expect(await screen.findByRole("alert")).toHaveTextContent("Changed elsewhere");
  });

  it("use the latest discards the draft", async () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    refusedAs(() => errorReply(412, "version_mismatch"));
    await openAndEdit("My title");
    await save();

    await userEvent.click(
      within(await screen.findByRole("alert")).getByRole("button", { name: "Use the latest" }),
    );

    expect(titleField()).toHaveValue(newer.title);
  });

  it("shows server field errors next to the field", async () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    server.use(
      http.patch(taskUrl, () =>
        errorReply(400, "validation_failed", [
          { field: "title", message: "That title is already in use." },
        ]),
      ),
    );
    await openAndEdit("My title");

    await save();

    expect(await screen.findByText("That title is already in use.")).toBeVisible();
    expect(titleField()).toHaveAccessibleDescription("That title is already in use.");
  });

  it("deletes optimistically and returns to the list", async () => {
    const state = { deleted: false };
    server.use(
      http.delete(taskUrl, async () => {
        await delay(300);
        state.deleted = true;
        return new HttpResponse(null, { status: 204 });
      }),
      http.get("/api/v1/tasks", () =>
        HttpResponse.json({
          items: state.deleted ? tasks.filter((task) => task.id !== detailTask.id) : tasks,
        }),
      ),
    );
    const { router } = renderApp(routes.task(detailTask.id));

    await confirmDelete();

    expect(await screen.findByRole("list", { name: "Tasks" })).toBeVisible();
    expect(router.state.location.pathname).toBe(routes.tasks);
    expect(state.deleted).toBe(false);
    expect(screen.queryByRole("link", { name: detailTask.title })).not.toBeInTheDocument();
  });

  it("restores the task when delete fails", async () => {
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    server.use(
      http.delete(taskUrl, async () => {
        await delay(50);
        return errorReply(500, "internal_error");
      }),
    );
    renderApp(routes.task(detailTask.id));

    await confirmDelete();

    expect(await screen.findByRole("alert")).toHaveTextContent("Couldn't delete the task");
    expect(screen.getByRole("link", { name: detailTask.title })).toBeVisible();
  });
});
