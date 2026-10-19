# frontend

React 19 SPA in TypeScript (Vite 8, Tailwind 4, Zod 4, dnd-kit). The views and the design gallery are built; the router, TanStack Query and the fetch wrapper come with the data layer.

## Commands

```bash
npm ci                       # Node 24
npm run dev                  # the app on Vite's dev server
npm run check                # ESLint (type-checked) + prettier --check + tsc --noEmit
npm run test                 # Vitest + coverage; fails under 85% lines or branches
npm run build                # tsc, then the app into dist/
npm run design:dev           # the design gallery on Vite's dev server
npm run design:build         # the gallery as one self-contained file: design/dist/artifact.html
npm run design:screenshots   # after design:build; needs `npx playwright install chromium` once
```

Every commit passes `check`, `test` and `build`.

## Layout

- `src/styles/tokens.css`: every colour, size, radius, shadow and duration, as Tailwind `@theme` tokens. The default theme is cleared, so a utility off the scale (`p-5`, `bg-red-500`) does not exist.
- `src/styles/index.css`: Tailwind, fonts, the `binding` and `ruled` utilities, and the hover, focus-visible and active variants the gallery can force.
- `src/components/ui/`: primitives. `src/components/`: compositions (`AppShell`, `AuthLayout`, `CredentialsForm`).
- `src/views/`: one view per screen. Props in, JSX out: no fetching, no router hooks, every intent leaves as a callback. Only local affordances (a draft, an open confirm) live in `useState`.
- `src/lib/`: pure helpers, `routes.ts`, and `schema/` (Zod, shared by forms and the API layer).
- `src/test/fixtures.ts`: the sample data and view props that both the tests and the gallery use.
- `design/`: the gallery, a second Vite entry. `screens.tsx` lists every state; `Scripted` drives a view the way a user would to reach states held in local state. `screenshots/` is committed.

## Gotchas

- `light-dark()` colours are polyfilled by Tailwind's Lightning CSS pass, so a theme switches only at the root (`color-scheme` on `:root`). Light-mode focus on the green band is too faint, so anything on the band sits in the `binding` utility, which turns the ring gilt.
- Layout responds to container width (`@wide:`), not the viewport. A view needs an `@container` ancestor; `Page`, `AppShell` and `AuthLayout` provide one.
- The gallery build roots Vite at `design/`, so `index.css` names `src/` and `design/` as Tailwind sources explicitly.
- Vitest stubs CSS imports; only `tokens.css` is processed, so the token tests can read it.
- `data-hover`, `data-focus-visible` and `data-active` exist for the gallery only. Never set them in app code.
- The design build inlines everything; the app build must not inline anything (the nginx CSP is `'self'` only).
