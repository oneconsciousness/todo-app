---
paths:
  - "frontend/src/components/**"
  - "frontend/src/pages/**"
  - "frontend/src/hooks/**"
  - "frontend/src/lib/query/**"
---
# React

- Function components with hooks. Every hook is declared before any conditional `return`; hooks run in the same order every render. `react-hooks/rules-of-hooks` and `react-hooks/exhaustive-deps` are errors.
- Server state lives in TanStack Query, and only there. Each resource has one module of query keys and hooks (`useTasks`, `useUpdateTask`); components never build query keys inline. Mutations that the user should see at once (reorder, toggle, delete) are optimistic, roll back on error and show the error.
- `useState` is for local affordances only: an open menu, a draft form value. Auth state is one context. Never copy server data into local state.
- Derive, do not mirror. A value computed from props or query data is computed during render (with `useMemo` only when it is measurably costly), never stored by an effect. `useEffect` is for syncing with something outside React, not for data flow.
- Forms validate with the same Zod schema the API layer uses, and show errors next to the field.
- Responsive by default, mobile first: Tailwind utilities, layouts that work from 320px wide up, touch targets of at least 44px, reorder that works by touch and by keyboard as well as by mouse.
- Accessible by default: real buttons and links, a label on every input, visible focus, and roles and names that tests query by.
- Styling: Tailwind utilities first. Inline `style` only for values the utility layer cannot express.
