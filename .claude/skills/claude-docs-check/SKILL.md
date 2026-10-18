---
name: claude-docs-check
description: Check whether the branch's changes need updates to CLAUDE.md, the rules or the skills, and make them on Opus. Runs before every PR to the base branch.
---
# Claude docs check

1. Base branch is `main` unless told otherwise. Changed files: `git diff --name-only origin/main...HEAD`.
2. Match them against `map.json` in this folder. Each entry maps code paths to the instruction files that describe them. No match: say "no docs triggers on this branch" and stop; the PR hook will not block.
3. On a match, run the `docs-keeper` agent with the base branch, the changed files and the matched entries. It runs on Opus and either edits the mapped files or explains, per artifact, why nothing needs to change.
4. Read its edits back against the code, not against the commit messages. Fix anything wrong.
5. Commit its decision. With edits: commit the docs files with the trailer `Claude-Docs: updated (<files>)`. Without edits: an empty commit whose message is `chore(claude): docs check, no change needed` with the trailer `Claude-Docs: no change: <reason>`. The PR hook reads that trailer.
6. Report what changed and why, in one paragraph.
