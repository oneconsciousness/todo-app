---
paths:
  - "frontend/src/**/*.ts"
  - "frontend/src/**/*.tsx"
---
# TypeScript

- `strict` is on in `tsconfig.json`. No `any`, no `as unknown as`, no `@ts-ignore`, no non-null `!` to silence a real `undefined`. Named exports. Function components with hooks; no classes, except `Error` subclasses (`ApiError`), which `instanceof` narrowing and TanStack Query's typed errors need.
- Every boundary is a Zod schema under `src/lib/schema/`: API responses, form data, storage, URL params. `parse`, or `safeParse` with a typed error path, right after reading; field access on the parsed value. Types come from the schema with `z.infer`, never written twice.
- Every API call goes through the one fetch wrapper in `src/lib/api/`, which sends the session cookie (same origin), parses the body and turns error bodies into a typed `ApiError`. No bare `fetch` in components or hooks.
- Domain types live in `src/types/` or next to their schema, reachable from any layer. Never define a cross-cutting type inside `components/`.
- Enums are `as const` objects, not `enum`. Use the typed constant, never the string literal.
- Discriminated unions are closed. Switch on the discriminant, and make the switch exhaustive with a `never` check.
- Environment values are read through one module, never raw `import.meta.env` in components. Build-time values are public; a secret never goes there.
- JSDoc: a summary line on every exported function, component and type. `@param` and `@returns` only when they say something the signature does not.
- Logic lives in exported pure helpers a test can reach (filtering, ordering, formatting), not inline in markup.
- Filenames are kebab-case. Tests sit next to the code they test as `<name>.test.ts(x)`.
- `npm run check` (ESLint, Prettier check, `tsc --noEmit`) is the gate.
