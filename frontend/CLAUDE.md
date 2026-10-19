# frontend

React 19 SPA in TypeScript (Vite 8, React Router 8, TanStack Query 5, Tailwind 4, Zod 4, dnd-kit). Views take props and render; a container per route in `src/pages/` feeds each view from TanStack Query.

## Commands

```bash
npm ci                       # Node 24
npm run dev                  # the app on Vite's dev server; `/api` goes to the stack on :8080, so start it first
npm run check                # ESLint (type-checked) + prettier --check + tsc --noEmit
npm run test                 # Vitest + coverage; fails under 85% lines, branches, functions or statements
npm run build                # tsc, then the app into dist/
npm run design:dev           # the design gallery on Vite's dev server
npm run design:build         # the gallery as one self-contained file: design/dist/artifact.html
npm run design:screenshots   # after design:build; needs `npx playwright install chromium` once
```

Every commit passes `check`, `test` and `build`.

## Layout

- `src/main.tsx`: boot. The Zod config first, then one query client, the router, and the `[app] started` line.
- `src/app/`: the route table and the ended-session redirect (`router.tsx`), the signed-in guard (`require-auth.tsx`), and the route error boundary (`route-error.tsx`).
- `src/pages/`: one container per route. Hooks in, one view out, no markup of its own.
- `src/styles/tokens.css`: every colour, size, radius, shadow and duration, as Tailwind `@theme` tokens. The default theme is cleared, so a utility off the scale (`p-5`, `bg-red-500`) does not exist.
- `src/styles/index.css`: Tailwind, fonts, the `binding` and `ruled` utilities, and the hover, focus-visible and active variants the gallery can force.
- `src/components/ui/`: primitives. `src/components/`: compositions (`AppShell`, `AuthLayout`, `CredentialsForm`).
- `src/views/`: one view per screen. Props in, JSX out: no fetching, no router hooks, every intent leaves as a callback. Only local affordances (a draft, an open confirm) live in `useState`.
- `src/lib/api/`: the fetch wrapper (`apiRequest`, `ApiError` with a closed set of codes) and one function per endpoint. Every request goes through it.
- `src/lib/query/`: query keys, the query client (the one place a 401 is handled), and the hooks for auth and tasks. Toggle, move and delete share `optimisticListUpdate`.
- `src/lib/auth/auth-context.tsx`: `useAuth`, the session and the sign-in, sign-up and sign-out actions.
- `src/lib/`: pure helpers (`tasks/order.ts`, `task-draft.ts`, `task-list.ts`, `due-date.ts`), `routes.ts` with `signInPath`, and `schema/` (Zod, shared by forms and the API layer, URL params included).
- `src/hooks/`: `useDebouncedValue`.
- `src/test/fixtures.ts`: the sample data and view props that both the tests and the gallery use.
- `src/test/server.ts`, `handlers.ts`: MSW at the `fetch` boundary, answering from the fixtures. `render-app.tsx` renders the whole app at a path, wired like `main.tsx`.
- `Dockerfile`, `nginx.conf`: the stack's front door. nginx serves `dist/`, proxies `/api/` to the API replicas, sets the security headers and the CSP, caps request bodies at 64 KB, and answers 404 on `/livez` and `/readyz`.
- `design/`: the gallery, a second Vite entry. `screens.tsx` lists every state; `Scripted` drives a view the way a user would to reach states held in local state. `screenshots/` is committed.

## Gotchas

- `light-dark()` colours are polyfilled by Tailwind's Lightning CSS pass, so a theme switches only at the root (`color-scheme` on `:root`). Light-mode focus on the green band is too faint, so anything on the band sits in the `binding` utility, which turns the ring gilt.
- Layout responds to container width (`@wide:`), not the viewport. A view needs an `@container` ancestor; `Page`, `AppShell` and `AuthLayout` provide one.
- The gallery build roots Vite at `design/`, so `index.css` names `src/` and `design/` as Tailwind sources explicitly.
- Vitest stubs CSS imports; only `tokens.css` is processed, so the token tests can read it.
- `data-hover`, `data-focus-visible` and `data-active` exist for the gallery only. Never set them in app code.
- The design build inlines everything; the app build must not inline anything (the nginx CSP is `'self'` only).
- Zod runs `jitless`, set in `src/lib/schema/zod-config.ts`. Otherwise it probes for eval when a schema is built, and the CSP reports a violation on every page load. `main.tsx` imports that file first; keep it first, before any module that builds a schema.
- The CSP for `/api/docs` allows Swagger UI's one inline script by its hash. A FastAPI upgrade can change that script; the live test on the docs CSP then fails, and the hash in `nginx.conf` needs updating.
- The dev server sends `/api` to `http://localhost:8080` with that as its `Origin`, because the API refuses writes from any other origin. When port 5173 is taken, Vite moves to the next free port, so open the URL it prints, or choose one with `npm run dev -- --port <n>`.
- A request with no MSW handler fails the test. Add one with `server.use` in the test; handlers reset after each test.
- The query cache logs only failures that mean something broke (5xx, no connection, a response that doesn't match its schema) with `console.error`; expected 4xx answers are not logged. A test that expects such a failure silences it with `vi.spyOn(console, "error")`; spies are restored after each test.
- `useAuth` reads the `me` query in the component that calls it, not from context. Context only updates when its provider renders again, so a page reading it could act on a session that has already ended.
- A query that throws to the route error boundary keeps its error cached. The boundary calls `useQueryErrorResetBoundary().reset()` before retrying, or the old error is thrown again without a fetch.
- Moves share the mutation scope `task-order`, so they reach the server in the order they were made, and the lists refetch only after the last one.
- A mutation whose `onSettled` returns a promise stays pending until it settles. Toggle does not await its refetch, so a failure shows at once. Quick add does, so the new row replaces the pending one.
- In jsdom, dnd-kit keeps the row positions it measured first. A test that makes several keyboard moves (`src/test/drag.ts`) reads where tasks landed from the screen.
- `npm ci` from the committed lockfile works with the npm that ships with Node 24. Regenerating the lockfile from scratch crashes that npm (11.5.1) in arborist ("reading 'edgesOut'"), so change dependencies with `npx npm@11.21.0 install`, then confirm a clean `npm ci` with the default npm.
- Dependencies are pinned to exact versions, each published at least two weeks before it was chosen (plan § 13). A newer version needs a reason: a fix or an advisory. TanStack Query 5.104.2 was taken early for its fix to scoped mutations pausing in a hidden tab.
