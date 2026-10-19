# Contributing to `todo-app`

This file is the canonical reference for *how* we work in this repo. The *why* (requirements, architecture, design decisions) lives in `docs/`: start with `docs/kickoff.md`.

> **TL;DR for first-time contributors:** branch off the current round branch (`round/<n>-<name>`), use Conventional Commits, run the tests before opening a PR into the round branch, get the human lead's review. The round reaches `main` in one parent PR once it is done and tested.

---

## 1. Branches and merges

Work is organised in rounds (round 1: containers, round 2: local k3d, round 3: AKS). Each round has one integration branch and one parent PR.

```
feature/<name>              ←  you work here, branched off the round branch
       │
       │  GATE — every suite passes on this branch (§ 5)
       ▼
  child PR  →  round/<n>-<name>   ←  reviewed by the human lead, then squash-merged
       │                             (one commit per child PR, titled by the PR)
       │  GATE — the round is done: exit criteria met, every suite green
       ▼
 parent PR  →  main              ←  open (as a draft) for the whole round;
       │                             rebase-merged once tested (one commit per child on main)
       ▼
   vX.Y.Z tag                    ←  a release is a tag on main; a tag is never moved or deleted
```

- **The parent PR** is opened as a draft as soon as the round branch has its first merged child, and is titled for the round (`feat(round-1): run the to do app in containers`). It is the round's checklist: each child PR is linked from it. It leaves draft only when the round's exit criteria are met, and it merges only after the human lead's final review.
- **`main` only ever receives finished, tested rounds.** Rebase-merging the parent lays the round's child commits onto `main` in order, so `main` stays linear with one commit per child PR. Each child's test-first commits stay visible in its merged PR on GitHub.
- **Child PRs** target the round branch and are squash-merged, so the PR title becomes the commit subject (the PR-title hook and CI keep it Conventional). Every commit on the PR branch is still green, and the test-first order stays in the PR. A child that depends on an unmerged child targets that child's branch until it merges, then is rebased onto the round branch (`git rebase --onto origin/round/<n>-<name> <old tip of the merged child>`) and retargeted.
- **After the parent PR is rebase-merged,** `main` holds the round's commits under new IDs, so the round branch is deleted and the next round's branch is created from `main`.
- **The round branch is protected like `main`:** no direct commits or pushes, only merged PRs. It is created once from `main` by the human (`git push origin main:refs/heads/round/<n>-<name>`), because the hook refuses that push from an agent.

**Never push directly to `main` or a round branch.** Always go through a PR. A wrong tag is fixed by cutting the next version, never by moving the existing one.

Deployment moves through three stages, each proven before the next starts: containers with `docker compose`, then a local k3d cluster, then AKS through GitHub Actions. `.claude/rules/deployment.md` holds the details. Rollback on Kubernetes is `kubectl rollout undo deployment/<name>`, run by a human (§ 11).

## 2. Branch naming and PR labels

- Lowercase with hyphens. No spaces, no underscores, no camelCase, no personal names.
- Prefix with type. Short and descriptive: what the branch *does*, not who is doing it.

✓ Good: `feature/task-reorder` · `fix/token-expiry-401` · `docs/readme-deploy`
✗ Bad:  `my-branch` · `Fix-Login-Alex` · `main-2` · `feature/everything`

Every PR carries exactly one label, taken from its branch prefix:

| Branch prefix | Label |
|---|---|
| `feature/` | `enhancement` |
| `fix/` | `bug` |
| `docs/` | `documentation` |
| `chore/` | `chore` |
| `refactor/` | `refactor` |
| `perf/` | `performance` |
| `test/` | `test` |
| `ci/` | `ci` |
| `round/` | `round` (the parent PR) |

A prefix that is not in this table is a gap: add a row in the same PR, after asking.

## 3. Commit messages — Conventional Commits

```
type(scope): short description in imperative mood, ≤ 72 chars

Optional body wrapped at 72, explaining *why* not *what*.

Refs: #123 — link the issue, discussion or plan doc when there is one
Co-Authored-By: <the agent's attribution line, when an agent wrote it>
```

Types: `feat` · `fix` · `refactor` · `perf` · `chore` · `docs` · `test` · `ci` · `build` · `revert` · `release`

Example: `feat(search): add hybrid ranking for short queries`

## 4. Pull requests

Use the template:

```markdown
## What
One paragraph: what does this PR do?

## Why
Link the issue, discussion or plan doc when there is one.

## How to test
Step-by-step. Reviewer should be able to verify in < 5 min.

## Risks / rollback
What could break? How to revert?

## Screenshots / logs
Inline if helpful.
```

- The human lead reviews every PR, child and parent alike.
- CI must be green before merge.
- **Child PRs are squash-merged** into the round branch: one commit per child, its subject the PR title. **The parent PR is rebase-merged into `main`**, so `main` gains the round's child commits in order, with no merge commits.

## 5. Test gates

**Before every commit and before opening a PR**, from the repo root, for each part the change touched:

```bash
python3 scripts/check_hygiene.py                                     # no task markers, debuggers, focused tests or debug-only logs
cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest
cd frontend && npm run check && npm run test && npm run build         # ESLint + Prettier + tsc, Vitest, Vite build
```

Changes to the running stack also run the live-server e2e and Playwright suites against it. `.claude/rules/testing.md` says which layer owns which behaviour.

If a gate is red, fix it on the branch. Do not commit and do not open the PR.

## 6. Stashing work-in-progress safely

```bash
git stash push -u -m "wip on hybrid search, schema half-done"
#                ↑  -u = also stash *untracked* files (new files you haven't `git add`-ed)
git stash list
git stash apply stash@{0}        # safer than `pop` if you're uncertain
```

Three rules: always include `-m`, always include `-u`, pop on the same branch you stashed from.

## 7. Working with Claude Code

This repo is set up to be paired with Claude Code. `CLAUDE.md` is what the agent reads first; `.claude/rules/` carries the topic rules; `.claude/skills/` carries the workflows.

The session shape:

1. `/repo-sync` before writing code.
2. Plan, align, execute. For anything beyond a small change the agent states the approach and waits for a yes.
3. `/verify` before saying done.
4. `/claude-docs-check`, then `/raise-pr`, which shows a card and waits for a yes.

Useful prompts:

- `"Create a new branch off the round branch called feature/<name> and switch to it."`
- `"Stage and commit my changes with a Conventional Commits message. Type is fix, scope is api, refs issue #42."`
- `"Sync my branch with the round branch, rebase, resolve conflicts conservatively and ask before discarding anything."`
- `"Before doing anything that touches main, follow CONTRIBUTING.md § 8 (the kind-stop protocol)."`

## 8. The kind-stop protocol — when you're about to break a rule

We expect **every coding agent** working in this repo (Claude Code, Cursor, Copilot, custom agents, future agents we haven't named yet) to follow this protocol when a human or another agent asks for something that would violate the rules in this file.

The goal is **not** to block the work. The goal is to **catch the deviation early**, explain it without condescension, and offer a path that gets the same outcome through the right channel. Everyone is at a different point on the git learning curve. We assume good faith in every request and we keep the warnings short, kind, and useful.

For Claude Code specifically, mechanical enforcement runs via the hooks in `.claude/hooks/` — see § 8.4.

### 8.1 What counts as a stop-and-warn event

Any of these in a single session:

1. Committing directly on `main` or a round branch (no feature branch)
2. Pushing directly to `main` or a round branch (no PR)
3. Force-pushing to a shared branch (`main`, anything someone else might be on)
4. Using a personal-name or vague branch name (`<name>-fix`, `claude-update`, `tmp`, `wip`, `update`, `fix`)
5. Skipping the test gate before opening a PR
6. Using `--no-verify` to bypass a git hook
7. Squashing the commits on a PR branch before merge (squash happens *on merge*; the PR keeps the test-first history)
8. Moving, deleting or re-creating a release tag
9. Editing files in any folder marked "generated" or "source — do not modify"
10. A commit message that isn't Conventional Commits format
11. Opening a PR without the standard template (What / Why / How to test / Risks)
12. Deleting a branch that has unpushed commits or an open PR
13. Running `git reset --hard` or `git clean -fd` on a branch with uncommitted work the user might still want

If the agent is uncertain whether something is a violation, **treat it as one and ask**. A 30-second pause is cheaper than an irreversible mistake.

### 8.2 The pre-approved warning format

When an agent detects a stop-and-warn event, it pauses and outputs a message in **exactly this shape**. No deviation from the structure; predictability is what makes it useful.

```
⚠️  Heads up — this would deviate from CONTRIBUTING.md

What you asked for:
  <one sentence, neutral, no judgment>

Why I'm pausing:
  This would <specific rule violated> — see CONTRIBUTING.md § <number>.
  <One sentence on why the rule exists, in plain language.>

What I'd suggest instead:
  1. <concrete next step>
  2. <concrete next step>
  3. <concrete next step>
  (This gets you the same outcome through the right channel.)

If you still want to proceed as originally asked:
  Reply "proceed anyway" and I'll do it. I'll note the deviation in the
  commit/PR description so the team has a record. No judgment — sometimes
  there's a reason the rule doesn't fit. Just want to make sure it's a
  conscious choice, not a slip.
```

### 8.3 Tone rules for the agent

- **Lead with the request, not the rule.** Restate what was asked in neutral words first, so the human knows they were heard.
- **No "you violated."** Use "this would deviate from" or "this is outside our usual flow." We're flagging the action, not the person.
- **No lectures.** One sentence on why the rule exists. If the human wants more, they'll ask.
- **Always offer a path forward.** A warning without an alternative is just an obstacle. The alternative steps must be concrete enough to copy-paste.
- **Always offer the override.** Rules exist for the 95% case. A new contributor on day one and a senior engineer mid-incident both deserve the same respect: flag it, then trust them to choose. Record the choice; don't argue it.
- **One warning per deviation.** Don't re-warn on the same deviation in the same session if the user has already chosen "proceed anyway." Re-warning becomes nagging, which kills trust in the warning system.
- **Soft language is fine. Vague language is not.** "This is a bit outside our usual flow" is friendly. "Hmm, maybe consider..." is unhelpful. Be kind *and* specific.

### 8.4 Mechanical enforcement (Claude Code hooks)

For Claude Code users, the rules above are enforced by hooks wired in `.claude/settings.json`:

| Hook | Event | Blocks |
|---|---|---|
| `branch-protection.py` | Bash | commits and pushes on `main` and round branches in any spelling (`HEAD:main`, quoted, `refs/heads/`, `+`, `--all`, `--mirror`), force pushes, `--no-verify` (also `-n` in a cluster), chained `git checkout main && git commit`, moving or deleting a `vX.Y.Z` tag |
| `env-protection.py` | Bash | any command that names, globs or brace-expands to a `.env*` path other than exactly `.env.example`; bulk reads that would sweep `.env` up (`find -exec cat`, `xargs cat`, recursive `grep`, `git grep --no-index`, `rg` on hidden or ignored files); the `docker` commands that print resolved secrets |
| `secrets-protection.py` | Bash, Read, Grep, Edit, Write, NotebookEdit | reads and writes of env files (except `.env.example`), key material and credential files, and Bash commands that print them (`cat`, `grep` without `-l/-c/-q`, `awk`, ...) |
| `pr-title.py` | Bash | `gh pr create` / `gh pr edit` with a title that is not Conventional Commits |
| `docs-check.py` | Bash | `gh pr create` when the branch touched a path in `.claude/skills/claude-docs-check/map.json` and carries no docs decision |
| `lint.py` | after Edit, Write | nothing; it reports lint findings on the changed lines back to the agent |
| `transcript-backup.py` | PreCompact, PostCompact, SessionEnd | compaction, when the transcript snapshot fails; it copies the session transcript to `.ai-transcripts/` and reports a rewritten transcript |

The guard hooks fail closed: an unreadable payload or a crash in the hook denies the call. They run on Python 3.9 and later, so the `python3` that ships with macOS is enough; CI runs their tests on 3.9 and 3.13.

They do **not** catch:
- Anyone running git outside Claude Code (terminal, IDE git pane, GitHub Desktop)
- Other agents (Cursor, Copilot, Codex, Aider); each has its own hook system or none
- Edits to `.github/workflows/*.yml` (those need code review)

That's why this protocol stays in CONTRIBUTING.md: the hooks are the safety net for the Claude Code path; this section is the universal contract.

**Per-user override** for emergencies: set `"disableAllHooks": true` in `.claude/settings.local.json` (gitignored). Hook lists merge across settings files, so an empty `"hooks": {}` does not turn them off. This is a deliberate escape hatch, auditable in your local config, never committed.

### 8.5 When the agent should refuse outright (no override)

These are not negotiable, even with "proceed anyway":

- Pushing to `main` without a PR (it deploys)
- Force-pushing `main` (rewrites deployed history)
- Deleting `main`
- Committing files matching `.env*`, `*.pem`, `*.key`, `*credentials*`, `*secrets*`, anything that smells like a secret. If the human insists, the agent should ask them to add the file to `.gitignore` first and stage only the non-secret parts.
- Running `rm -rf` on anything outside the repo, or on `.git/` itself

For these, the response is:

```
⛔  I can't do this one, even with "proceed anyway."

  <one-sentence reason — what specifically breaks>

  If you have an authorized exception (incident response, security rotation,
  approved by the team), please do this manually with full awareness of the
  blast radius. I'm not the right tool for this action.
```

### 8.6 How to invoke it

Humans don't need to invoke it; it's the default behavior. If you ever notice an agent *not* using this format on a deviation, that's a bug; flag it in the PR review and we'll fix the instructions.

If you're reviewing a PR and the description mentions `Deviation noted: <X>`, that means the contributor hit the warning, chose "proceed anyway," and the agent recorded it. Treat it as a normal review signal, not a flag, just context.

---

## 9. Working from a written plan — for agents (and humans pairing with them)

When an agent is implementing from a plan doc (the kind that lives in `docs/plans/`), three rules govern how it takes direction.

### 9.1 The three rules

1. **Plan contradictions = STOP and ask.** If a plan's main body says one thing and an open-question section recommends another, the agent must surface the contradiction and let the human lock the answer before coding. Open questions are open until a human locks them. A line labeled `Recommendation: ...` inside an unlocked Q&A section is *not* a default to silently follow; it's a candidate for the human's review.
2. **Default to replacement, not addition.** When a plan describes swapping element X for element Y, the agent ships a swap. *"Keep X as fallback alongside Y, gated by a flag"* is dual-path complexity sold as safety: it bloats the code, and creates branches that future readers and agents must reason about. Additive patterns require a **named, real failure mode** that justifies them, not a hypothetical "safety rail."
3. **Rollout ramps live in deploy config, not in the artifact.** Gradual rollout is an ops concern (env var, feature flag at the deploy boundary, canary release). It is not a reason to keep two parallel implementations inside one module. The artifact ships the new behavior as the only behavior; ops decides which version is live.

### 9.2 The warning format for plan contradictions (extends § 8.2)

```
⚠️  Heads up — this plan has a contradiction (or asks for an additive pattern)

What the plan says:
  Body §<N>: <quote>
  Open Q-<N>: <quote>

Why I'm pausing:
  These two recommendations point in different directions. CONTRIBUTING.md §9.1
  says open questions stay open until a human locks them, and that I should ask
  before silently picking a side.

What I'd suggest:
  1. Lock the open question now (drop X / keep X as fallback / replace X with Y)
  2. Update the plan doc to reflect the lock
  3. Then I'll implement against the locked spec

If you'd like me to proceed with one option without locking the plan first:
  Reply "proceed with <option>" — I'll note the deviation in the PR description.
```

---

## 10. Merge discipline — who can merge what to `main`

### 10.1 The merger's responsibility

Whoever clicks the merge button must, before clicking:

1. **Have written or read the code thoroughly.** File-by-file, line-by-line for the diff, not just the PR description. If the diff is too large to read in one sitting, ask the contributor to split it.
2. **Have tested it locally.** Pulled the branch, run it, exercised the changed paths. CI green is necessary but not sufficient.
3. **Confirm the test gate passed for real.** If a contributor said "tests pass" but the merger can't verify, the merger runs them again.

If any of the three is false, the PR doesn't merge yet.

### 10.2 Only stable tested code goes to `main`

- **Don't merge to "see if it works there."** That's what your local environment is for.
- **Don't merge to "unblock another PR."** Stack the branches instead.
- **Don't merge because "it's mostly done."** Mostly done isn't done.

### 10.3 If issues are found *after* merge, raise a NEW PR

Do not reopen the merged PR, force-push over the merged commit, amend it, or revert and recommit on the same branch. Raise a fresh `fix/...` branch off the round branch, fix the issue, open a new child PR, get it reviewed, merge. Once a round has reached `main`, the fix belongs to the next round's branch.

The one exception is a critical regression that breaks `main` for everyone: there, a `git revert` PR (a NEW commit that undoes the merged one) is the right tool. Even then, the *fix* lands as a separate, reviewed PR after the revert.

---

## 11. Operational scripts and deployments — the human-runs-it rule

Operational scripts that touch live infrastructure (reindex, deploy, secret rotation, schema migration against a shared database, bucket sync) **run from a human's terminal, not from inside an agent session.** Agents prepare and document; humans execute.

The handoff an agent produces has five parts: what the script does, what it touches, the exact command, how to verify it worked, and how to roll it back. Put a "STOP — read before running" block at the top of each ops folder's README and each script's docstring; that is the in-flight trigger that fires when an agent reads the file before acting. Hooks cannot tell "mutates prod" from "reads prod"; this rule is the contract.

Every deployment artifact (Dockerfile, compose file, Kubernetes manifest, overlay, workflow) is reviewed by the human before it is applied or merged. The agent never applies anything to AKS or another shared cloud resource.

---

## 12. Secrets discipline — agents do not write or expose `.env` and friends

Secrets files (`.env`, `.env.*`, `*.pem`, `*.key`, `*.crt`, `*.p12`, `credentials.*`, `secrets.*`, `~/.ssh/*`, `~/.aws/credentials`, `.docker/config.json`, `.kube/config`, etc.) are **user-managed**, not agent-managed.

### 12.1 The three rules

1. **Agents never write, edit or append to secrets files via `Edit` / `Write` / `MultiEdit` / `NotebookEdit`.** Even when the agent has the new value (a freshly minted token), the *write* belongs to the user. The agent prints the proposed change as text; the user pastes it.
2. **Agents never read-and-print secrets files via Bash.** `cat .env`, `head .env`, `grep <pattern> .env`, `awk ... .env`, `xxd key.pem`, all blocked. The contents would land in the agent's context window and become exposable through transcript replay or compaction.
3. **Agents never touch env files other than `.env.example`, not even through a script.** For key material and credential stores, an agent may write a script that changes the file in place (a `sed -i`), with one binding constraint: the script must not print secrets to stdout.

### 12.2 `.env.example` is the one env file agents may touch

`.env.example` is the committed template: it lists every setting with a safe local value and never holds a real secret. Agents create and edit it, by that exact name only, so it stays in step with the settings class. Everything else in the family stays closed: `.env`, `.env.local`, `.env.example.bak`, a glob like `.env.example*`, a command that names `.env` alongside the example (`cp .env.example .env` is the human's to run), and a `.env.example` that is a symlink to a real secret. The tests in `.claude/hooks/tests/test_secret_guards.py` pin each of these.

A real secret never goes into `.env.example`. If one ever lands there, treat it as leaked: rotate it.

### 12.3 Allowed patterns the hook still blocks

These don't expose contents, but `env-protection.py` blocks every Bash command that names a `.env*` path, and an allow rule cannot override a hook. They are the human's to run:

- `ls -la .env`, `wc -l .env`, `chmod 600 .env`
- `grep -l`, `grep -q`, `grep -c` on `.env`
- `sed -i 's/^KEY=.*/KEY=<new>/' .env`
- `echo "NEW_KEY=value" >> .env` (append; the agent must not have read the existing contents)

For the wider set (`*.pem`, `credentials.json`, ...) `secrets-protection.py` blocks only the programs that print files, so `ls`, `wc`, `chmod`, `grep -l/-q/-c` and `sed -i` pass.

A commit message that mentions an env file trips `env-protection.py` when passed with `-m`. Write the message to a file and commit with `git commit -F <file>`.

### 12.4 What to do when the agent needs to update a secret

1. **For a new setting,** add it to `.env.example` with a safe local value and tell the human which real value to set in `.env`.
2. **For a value that changes,** print the proposed change as text in chat: *"set `API_TOKEN` to …"*. The human makes the edit.
3. **For key material,** a `sed -i` that changes it in place without reading the existing value back, or an external script the human runs.

### 12.5 The warning format

Use the § 8.2 shape with the rule reference `CONTRIBUTING.md § 12 (Secrets discipline)` and the specific action ("write to .env" / "read-and-print key.pem") in the "Why I'm pausing" line.

### 12.6 Mechanical enforcement, and what it cannot see

**What the guards are for.** They stop an agent from *accidentally* reading, printing, committing or pushing what it should not: a stray `cat .env`, a recursive search that sweeps up a key, a push to a protected branch. They are not a sandbox against a determined adversary, and they say so here rather than overclaim.

- `.claude/settings.json` denies `Read` and `Edit` (which covers Write, MultiEdit and NotebookEdit) on `.env`, `*.pem`, `*.key`, and `credentials` and `secrets` files with the common data extensions (`.json`, `.yaml`, `.yml`, `.toml`). `secrets-protection.py` covers the full extension list. Source files such as `credentials.py` stay readable. Permission rules cannot express "every `.env.*` except one", so the other `.env.*` names are enforced by the hooks.
- The three Bash guards read a command through `shell_words.py`, the way the shell would: quotes removed, `{a,b}` and `{a..c}` expanded, zsh `(a|b)` groups, backticks and `$( … )` split out, and wrappers (`sudo -u x`, `env`, `command`, `timeout`, `if … then`, `{ … }`) peeled off. Long options are matched by any abbreviation git and grep accept (`--recur`, `--no-verif`).
- `env-protection.py` blocks any command whose `.env…` words are not exactly `.env.example`, dotfile globs that reach `.env`, and bulk reads that could sweep it up. `find -exec` and `xargs` may only run programs that print no file contents (or a quiet grep, or `sed -i`), unless xargs is fed by a gitignore-aware lister (`git ls-files`, `rg -l`). Also blocked: recursive grep or ugrep, `git grep --no-index`, `rg`/`ug` on hidden or ignored files, `git add --force`, `git stash --all`, `tar` to stdout, and the docker commands that print resolved secrets.
- `secrets-protection.py` blocks Read, Grep, Edit, Write, MultiEdit and NotebookEdit on the full pattern list, Grep globs aimed at env dotfiles, a `.env.example` that resolves to another file, and Bash commands that print one of those files: by program (`cat`, `sed` without `-i`, `base64`, `openssl`, `dd if=`, `perl`, `ln`, …), by input redirection (`< key`), and through git (`git diff --no-index`, `git show`).
- `branch-protection.py` follows `cd` and `git -C` to the repo each git command runs in, so a commit into a worktree on `main` is caught. It refuses `git -c` keys that could redirect a push or skip hooks (`remote.*`, `alias.*`, `core.hooksPath`), wildcard refspecs that reach a protected branch, and `git update-ref` on protected refs.
- Every guard fails closed: an unreadable payload, a crash, or a missing `shell_words.py` denies the call.

**What string matching cannot see,** and what covers it instead:

| Gap | Example | Backstop |
|---|---|---|
| A path built at run time | `cat "$(printf '\x2eenv')"` | The agent rules (§ 12.1) and the transcript, which is reviewed |
| File names fed through a loop or a substitution | `find . -type f \| while read f; do cat "$f"; done`, `cat $(find .)` | `find`, `grep` and loops are not on the no-prompt allow list, so they need permission |
| A script the agent writes, then runs | `python3 dump.py` | Rule 12.1.3: a script never prints a secret; the human reviews every PR |
| Anything a git hook would catch | `--no-verify` variants the parser misses | `git push` always asks, and every change reaches `main` only through a reviewed PR |

**What makes a leak cheap if one happens:** in round 1, `.env` holds only local development values (the same kind `.env.example` documents). Real secrets for rounds 2 and 3 live in Kubernetes Secrets and Azure Key Vault, never in a file in the repo.

The hook tests (`.claude/hooks/tests/`) pin every bypass a review has found, as a deny case, and every false positive, as an allow case. A new bypass becomes a new test first.

---

## 13. Screenshot and log review — review several before reporting back

When a test run, a UI walkthrough or a log capture produces artifacts the agent must review before reporting status:

- **Review at least three** from different test rows before declaring a run successful. If the run produced ten or more, sample at least one from each category. If it produced fewer than three, review them all.
- **"Review" means open the actual artifact** and check it: did the action submit, did the response complete, is anything visibly broken, did the right branch fire for that row's category.
- Aggregate findings before responding. "10/10 captured" without a per-row issue list is a violation of this rule. Captured is not correct.

## 14. Server restart verification — confirm the new PID is the one on the port

A "restart" can fail to bind the port because the old process still holds it; the new one exits silently and the test runs against stale code with the confidence of fresh evidence. Before any test that depends on a local server:

1. Kill the old process.
2. Confirm the port is free: `lsof -ti:<port>` returns nothing.
3. Start the new process.
4. Confirm the listener PID is the new one: `lsof -iTCP:<port> -sTCP:LISTEN -P -n`.
5. Confirm the uptime matches your restart: `ps -o etime -p <new-pid>` shows seconds, not hours.
6. Confirm the application is serving: the startup line in the log, or a known endpoint.

"Port is up" is not enough. The same PID being there after a restart is the bug.

## Appendix A. Lesson cards

A lesson card records the mistake that produced a rule, so the rule stays understood. One per rule birth. Shape:

> **YYYY-MM-DD (context).** What happened, in two or three sentences. What the agent or human should have done instead, in one sentence. Which section this produced or changed.

> **2026-10-19 (round 1, S1 review).** The hooks used `str | None` in signatures, which Python evaluates when the function is defined. Under the `python3` that ships with macOS (3.9) every hook crashed on import, Claude Code treats a crashed hook as "allow", and so every guard was silently off on a reviewer's Mac. CI only ran 3.13, so nothing caught it. Hooks and scripts now start with `from __future__ import annotations`, the guards fail closed on any crash, and CI runs the hook tests on 3.9 as well. Produced the fail-closed note in § 8.4.

> **2026-10-18 (repo skeleton).** The first hygiene gate was a bash script using `declare -n` and `git grep -P`. macOS ships bash 3.2 and Apple git may lack PCRE, so it would not have run on a reviewer's Mac. Repo scripts are Python 3 standard library, like the hooks. Produced `scripts/check_hygiene.py`.
