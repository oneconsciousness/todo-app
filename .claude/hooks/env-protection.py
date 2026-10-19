#!/usr/bin/env python3
"""
PreToolUse hook for Claude Code's Bash tool.
Blocks any Bash command that could read, copy, print or source a `.env*` file, except `.env.example`.

`.env*` files hold runtime secrets (API keys, OAuth client secrets,
DB credentials) that must never enter an LLM context, an agent
transcript, or git history. `.env.example` is the one exception: it is
the committed template, holds no real secrets, and agents keep it in
sync with the settings. Its access is exact: `.env.example.bak`,
`.env.example*` or a command that also names `.env` stays blocked.

Checks, each fail-closed:
  - every `.env…` token in the command, raw and after shell unquoting,
    must be exactly `.env.example` (case-insensitive, since macOS file
    systems are)
  - no glob that the shell would expand to a dotfile like `.env`
    (`.e*`, `.[e]nv`, `.*`)
  - no recursive grep, which reads hidden files; use `rg` (skips hidden
    and gitignored files) or `git grep` (tracked files only)
  - no `rg --hidden` / `-uu`, which would reach `.env`
  - no `docker compose config` without `--no-interpolate`, `docker
    inspect`, or `env` / `printenv` inside a container, which print the
    values compose read from `.env`

String matching cannot see a path built at run time (`printf '\\x2eenv'`,
a script that opens it). CONTRIBUTING.md § 12.1 rule 3 is the contract for
that case.

Returns Claude Code's PreToolUse deny shape:
  {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                          "permissionDecision": "deny",
                          "permissionDecisionReason": "..."}}

No allow rule in any settings file can override a hook deny.
"""
import fnmatch
import json
import posixpath
import re
import shlex
import sys

# --- config ---------------------------------------------------------------
ALLOWED_ENV_FILES = frozenset({".env.example"})  # exact basenames agents may touch
# --------------------------------------------------------------------------

ENV_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9_\-])(\.env[^\s'\"`;|&<>()]*)", re.IGNORECASE)
GLOB_CHARS = frozenset("*?[")
DOTFILE_PROBES = (".env", ".env.local", ".env.production")
RECURSIVE_GREP_RE = re.compile(r"(?:^|[\s;|&(])(?:e|f)?grep\s+(?:[^|;&]*\s)?(?:-[A-Za-z]*[rR][A-Za-z]*|--recursive|--dereference-recursive)(?=\s|$)")
RG_HIDDEN_RE = re.compile(r"(?:^|[\s;|&(])rg\s+(?:[^|;&]*\s)?(?:--hidden|--no-ignore\S*|-[A-Za-z]*uu[A-Za-z]*|-\.)(?=\s|$)")
DOCKER_LEAK_RES = (
    (re.compile(r"\bdocker[\s-]+compose\b(?![^|;&]*--no-interpolate)[^|;&]*\sconfig\b"), "`docker compose config` prints the values compose read from `.env`; add `--no-interpolate`"),
    (re.compile(r"\bdocker\s+(?:container\s+)?inspect\b"), "`docker inspect` prints a container's environment"),
    (re.compile(r"\bdocker[\s-]+(?:compose\s+)?(?:exec|run)\b[^|;&]*\s(?:env|printenv)\b"), "`env` or `printenv` in a container prints its secrets"),
)


def deny(reason: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(0)


def allow() -> None:
    sys.exit(0)


def shell_words(command: str) -> list[str]:
    """Split like the shell would, so quote splicing (`.e""nv`) is undone; fall back to whitespace."""
    try:
        return shlex.split(command, posix=True)
    except ValueError:
        return command.split()


def forbidden_env_token(command: str, words: list[str]) -> str | None:
    """Return the first `.env…` token that is not exactly an allowed file."""
    tokens = ENV_TOKEN_RE.findall(command) + [t for w in words for t in ENV_TOKEN_RE.findall(w)]
    return next((t for t in tokens if t.lower() not in ALLOWED_ENV_FILES), None)


def dotfile_glob(words: list[str]) -> str | None:
    """Return the first glob the shell would expand to an env dotfile."""
    def reaches_env(word: str) -> bool:
        base = posixpath.basename(word.rstrip("/")).lower()
        return base.startswith(".") and any(fnmatch.fnmatchcase(p, base) for p in DOTFILE_PROBES)
    return next((w for w in words if GLOB_CHARS & set(w) and reaches_env(w)), None)


def leak_reason(command: str) -> str | None:
    """Return why a command would read env files indirectly, or None."""
    if RECURSIVE_GREP_RE.search(command):
        return "recursive grep reads hidden files such as `.env`; use `rg` (skips hidden and gitignored files) or `git grep`"
    if RG_HIDDEN_RE.search(command):
        return "`rg` with hidden or ignored files enabled would read `.env`"
    return next((why for pattern, why in DOCKER_LEAK_RES if pattern.search(command)), None)


def main() -> None:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        allow()

    tool_input = payload.get("tool_input") or {}
    command = (tool_input.get("command") or "")
    if not command:
        allow()

    words = shell_words(command)
    target = forbidden_env_token(command, words) or dotfile_glob(words)
    if target:
        deny(
            f"Reading or modifying `{target}` from Claude Code is blocked. "
            f"`.env*` files hold runtime secrets (API keys, tokens, DB "
            f"credentials) that must never reach an LLM context, transcript, "
            f"or git history. Only `.env.example` is open to agents, by its "
            f"exact name. If you need a value, ask the human directly; to "
            f"create `.env` from the example, ask the human to run the copy."
        )

    reason = leak_reason(command)
    if reason:
        deny(f"Blocked: {reason}. See CONTRIBUTING.md § 12 (Secrets discipline).")

    allow()


if __name__ == "__main__":
    main()
