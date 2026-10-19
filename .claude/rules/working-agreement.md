# Working agreement

How this team works with Claude Code. Applies to every session in this repo.

- Write in plain English: chat, docs, commit messages, PR text, code comments. Short sentences. If a simpler word carries the same meaning, use it.
- Lead with the answer or the outcome. Supporting detail comes after; leave out steps that do not change what the reader does next. Bullets for parallel items.
- Plan, align, execute. For anything beyond a small change, state the approach in a few lines and get a yes before building. Ask when different readings of the task would lead to different work. Do not ask about routine choices.
- Estimate in agent-pair time, not human-solo time. A well-aligned agent and human pair finishes in roughly a twentieth of the solo-human time. Give estimates as bounded work ("4 file edits, 1 migration, 1 PR" or "within a session"), never as human days. Name external waits (CI, deploys, reviews) separately.
- At the start of a session, run `/repo-sync` before writing code. Never switch or pull a repo that has uncommitted work without saying so.
- Stay in scope. Change only what the task names. Unrelated problems become a one-line follow-up note, not an inline fix.
- When a written plan or spec and the situation disagree, stop and ask. Never deviate silently, even when the deviation looks like an improvement. The spec for this repo is `docs/kickoff.md`, then the plan docs in `docs/plans/`.
- Report outcomes as they are. Failing tests are reported as failing, with output. Skipped steps are named. "Done" means `/verify` passed.
- The session transcript is shared with the reviewers as the record of how AI was used. Do the work inside the session: run the red test, then the green one, where the transcript shows both. Keep the human's decisions and the agent's work easy to tell apart.
- Keep the Claude Code files true to the code. Before a PR, `/claude-docs-check` reads the branch diff against `.claude/skills/claude-docs-check/map.json` and updates CLAUDE.md or the mapped rule on Opus, or records why not. A hook blocks `gh pr create` until that decision is on the branch.
- Before opening a PR, run `/raise-pr` and wait for a yes. One PR per branch.
