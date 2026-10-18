---
name: raise-pr
description: Show the pre-raise card for a pull request and open it only after the human says yes.
disable-model-invocation: true
---
# Raise a PR

Do these steps in order. Stop after step 4 and wait.

1. Sync: `git fetch --all --prune`, then report behind/ahead against the base branch. Rebase if behind. With no remote yet, say so and skip.
2. Check the branch: every commit is on a branch off `main`, the tree is clean, and `/verify` has passed. Run `/claude-docs-check`; the PR hook blocks `gh pr create` until its decision is on the branch.
3. Build the card:
   - Title: `type(scope): subject`. Types: feat, fix, chore, docs, refactor, perf, test, ci, build, revert, release. Subject starts lowercase, no trailing period.
   - Branch and base (usually `main`).
   - Assignee: the GitHub login of the human whose git identity is on the commits. `git log -1 --format=%an` gives the name; `gh api user --jq .login` confirms the login.
   - Label: one, from the branch prefix through `CONTRIBUTING.md` § 2. If the label does not exist on the repo yet (`gh label list`), say so on the card; creating it is part of the yes.
   - Summary: one to three lines. The problem and the chosen approach.
   - Description with the sections What, Why, How to test, Risks and rollback. Link sources rather than restating them. End with the attribution footer the session gives you.
4. Show the card and the description in chat. Ask for a go. Do not push or create anything yet.
5. On a yes: create the label if the card said it was missing, `git push -u origin <branch>`, then `gh pr create --base <base> --head <branch> --title "<title>" --body-file <file> --assignee <login> --label <label>`. The commands prompt for permission; that is expected.
6. Report the PR URL, then `gh pr checks <n> --watch` and report the result.

Never add reviewers unless the human names them. Never open a second PR for the same branch.
