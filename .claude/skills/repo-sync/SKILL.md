---
name: repo-sync
description: Sync this repo (and any sibling repos it is coupled to) to the latest base branch at the start of a session, and report state.
---
# Repo sync

Run this before writing code and before raising a PR.

1. This repo: `git fetch --all --prune --tags`, then `git rev-list --left-right --count origin/main...HEAD`. Left is behind, right is ahead. Behind above zero on a feature branch means rebase first. Report the numbers; "already current" is information too.
2. Siblings, if this repo shares a contract with others: for each sibling (`../<repo>`, base `<branch>`), fetch, then report current branch, dirty count, behind/ahead of its base. If a sibling is pinned by a ref file here, confirm the sibling's checkout matches the pin before trusting a local test run. No siblings: say so and skip this step.
3. A clean sibling that is only behind may be fast-forwarded. Never switch a sibling's branch without saying so, and put it back afterwards. Never pull or stash a dirty sibling; report it and let the human decide.
4. If `.git/index.lock` exists and no git process is running, it is a stale lock from a crashed process. Say so, then remove it.

Report one line per repo: branch, head, behind/ahead, dirty count.
