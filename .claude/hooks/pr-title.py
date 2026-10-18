#!/usr/bin/env python3
"""PreToolUse hook for Bash. Blocks `gh pr create` / `gh pr edit --title` when the title is not Conventional Commits.

Format: type(scope): subject. Scope is optional and free-form. Subject starts lowercase and has no trailing period.
The CI check (if any) stays the real gate; this hook saves a round trip.
"""
import json
import re
import shlex
import sys

# --- config ---------------------------------------------------------------
ALLOWED_TYPES = ("feat", "fix", "chore", "docs", "refactor", "perf", "test", "ci", "build", "revert", "release")
# --------------------------------------------------------------------------
SUBJECT_RE = re.compile(r"^[a-z].+[^.]$")
TITLE_RE = re.compile(r"^(?P<type>[a-z]+)(?:\((?P<scope>[a-z0-9][a-z0-9-]*)\))?:\s+(?P<subject>.+)$")
GH_PR_RE = re.compile(r"\bgh\s+pr\s+(?:create|edit)\b")


def deny(reason: str) -> None:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": reason}}))
    sys.exit(0)


def extract_title(command: str) -> str | None:
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        return None
    for i, tok in enumerate(tokens):
        if tok in ("--title", "-t") and i + 1 < len(tokens):
            return tokens[i + 1]
        if tok.startswith("--title="):
            return tok[len("--title="):]
    return None


def validate(title: str) -> str | None:
    m = TITLE_RE.match(title)
    if not m:
        return f"Expected `type(scope): subject`, got {title!r}. Scope is optional; the space after the colon is not."
    if m.group("type") not in ALLOWED_TYPES:
        return f"Type {m.group('type')!r} is not one of: {', '.join(ALLOWED_TYPES)}."
    subject = m.group("subject")
    if not SUBJECT_RE.match(subject):
        if subject.endswith("."):
            return "Subject must not end with a period."
        return "Subject must start with a lowercase letter. If it starts with a name, put a verb first: `add`, `wire`, `port`."
    return None


def main() -> None:
    try:
        payload = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        sys.exit(0)
    command = ((payload.get("tool_input") or {}).get("command") or "").strip()
    if not command or not GH_PR_RE.search(command):
        sys.exit(0)
    title = extract_title(command)
    if title is None:
        sys.exit(0)
    err = validate(title)
    if err:
        deny(f"PR title blocked before `gh` ran: {err} Fix the --title value and run it again.")
    sys.exit(0)


if __name__ == "__main__":
    main()
