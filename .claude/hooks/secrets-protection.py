#!/usr/bin/env python3
"""
PreToolUse hook for Claude Code's Edit / Write / MultiEdit / NotebookEdit / Bash tools.
Blocks writes to secrets files AND blocks Bash reads-that-print secrets.

See CONTRIBUTING.md § 12 (Secrets discipline) for the full rationale.

Behavior summary:
  - Edit/Write/MultiEdit/NotebookEdit on a secrets path                 -> DENY
  - Bash command reading-and-printing a secrets path
    (cat / head / tail / less / more / nl / xxd / od / strings,
     grep without -l/-c/-q, awk on a secrets path)                       -> DENY
  - Bash commands that mutate secrets in place (sed -i, chmod, echo>>,
     scripts that the agent has explicitly verified do NOT print
     secrets to stdout)                                                  -> ALLOW
  - everything else                                                      -> ALLOW

Secret patterns (matched against the file_path basename or any path segment):
  - .env, .env.*  (any env file)
  - *.pem, *.key, *.crt, *.p12, *.pfx, *.jks  (cryptographic keys/certs)
  - credentials.*, secrets.*, task-secrets.*  (named secret stores)
  - id_rsa, id_rsa.*, id_ed25519, id_ed25519.* (SSH keys)
  - .npmrc, .pypirc, .docker/config.json, .aws/credentials, .ssh/, .gnupg/, .kube/config

Returns Claude Code's PreToolUse deny shape:
  {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                          "permissionDecision": "deny",
                          "permissionDecisionReason": "..."}}
"""
import fnmatch
import json
import os
import re
import sys

SECTION_REF = "CONTRIBUTING.md § 12 (Secrets discipline)"

# Pattern matched against the basename. Using fnmatch globs.
SECRET_BASENAME_GLOBS = (
    ".env",
    ".env.*",
    "*.pem",
    "*.key",
    "*.crt",
    "*.p12",
    "*.pfx",
    "*.jks",
    "credentials.*",
    "secrets.*",
    "task-secrets.*",
    "id_rsa",
    "id_rsa.*",
    "id_ed25519",
    "id_ed25519.*",
    ".npmrc",
    ".pypirc",
)

# Pattern matched against any path segment.
SECRET_PATH_FRAGMENTS = (
    ".docker/config.json",
    ".aws/credentials",
    ".aws/config",
    ".ssh/",
    ".gnupg/",
    ".kube/config",
)

WRITE_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}

# Bash readers that print file contents to stdout — denied if their
# argument matches a secrets path. The grep/awk cases need flag inspection.
PRINTING_READERS = (
    "cat", "head", "tail", "less", "more", "nl",
    "xxd", "od", "strings", "bat", "tac",
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


def is_secret_path(path: str) -> bool:
    if not path:
        return False
    norm = path.replace("\\", "/")
    base = os.path.basename(norm)
    if base:
        for glob in SECRET_BASENAME_GLOBS:
            if fnmatch.fnmatch(base, glob):
                return True
    for frag in SECRET_PATH_FRAGMENTS:
        if frag in norm:
            return True
    return False


def bash_command_reads_and_prints_secret(command: str) -> tuple[bool, str | None]:
    """Heuristic check: does this Bash command read a secrets file AND print
    its contents to stdout? Returns (is_violation, matched_path).

    Splits on shell connectors (;, &&, ||, |, &) and inspects each piece.
    For pipes (|), printing readers on the LEFT side feed downstream — that's
    still printing-from-secret (the data flows through the pipe and may land
    in stdout / agent context). So we treat any printing-reader on a secrets
    path as a violation.
    """
    if not command:
        return False, None
    # Split on shell separators that create independent command stages.
    # Conservative: '|' counted, since the read still happens.
    parts = re.split(r"\s*(?:\|\||&&|;|\||&)\s*", command)
    for part in parts:
        part = part.strip()
        if not part:
            continue
        tokens = part.split()
        if not tokens:
            continue
        head = tokens[0].lstrip("$").lstrip()
        # Strip leading "sudo" / env var prefixes
        if head in {"sudo", "command", "exec", "time"}:
            tokens = tokens[1:]
            if not tokens:
                continue
            head = tokens[0]
        # PRINTING_READERS check
        if head in PRINTING_READERS:
            for arg in tokens[1:]:
                if arg.startswith("-"):
                    continue
                if is_secret_path(arg):
                    return True, arg
        # grep without quiet/list-only flags is a printing reader
        if head == "grep":
            quiet = any(
                f in tokens[1:]
                for f in ("-l", "--files-with-matches",
                          "-L", "--files-without-match",
                          "-c", "--count",
                          "-q", "--quiet", "--silent")
            )
            if not quiet:
                for arg in tokens[1:]:
                    if arg.startswith("-"):
                        continue
                    if is_secret_path(arg):
                        return True, arg
        # awk default action prints; treat awk on a secrets path as violation
        if head == "awk":
            for arg in tokens[1:]:
                if arg.startswith("-"):
                    continue
                if is_secret_path(arg):
                    return True, arg
    return False, None


def main() -> None:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        allow()

    tool_name = payload.get("tool_name") or ""
    tool_input = payload.get("tool_input") or {}

    if tool_name in WRITE_TOOLS:
        path = (
            tool_input.get("file_path")
            or tool_input.get("notebook_path")
            or ""
        )
        if is_secret_path(path):
            deny(
                f"Heads up — `{tool_name}` on `{path}` is blocked because the "
                f"path matches a secrets-file pattern. Agents don't write to "
                f".env, *.pem, *.key, credentials.*, secrets.*, ssh/aws/gnupg/"
                f"kube config, etc. — these are user-managed.\n\n"
                f"What to do instead: write a script that mutates the file "
                f"in place (e.g., `sed -i 's/^API_TOKEN=.*/API_TOKEN="
                f"<new>/' .env`) AND never prints the secret contents back. "
                f"Or print the proposed change as text and ask the user to "
                f"make the edit.\n\n"
                f"See {SECTION_REF}."
            )
        allow()

    if tool_name == "Bash":
        command = (tool_input.get("command") or "").strip()
        violated, matched = bash_command_reads_and_prints_secret(command)
        if violated:
            deny(
                f"Heads up — this Bash command would read `{matched}` and "
                f"print it to stdout. The contents would land in the agent's "
                f"context, exposing secrets.\n\n"
                f"Allowed alternatives:\n"
                f"  - In-place mutation: `sed -i 's/^KEY=.*/KEY=<new>/' .env`\n"
                f"  - Existence/stat only: `ls`, `wc -l`, `stat`, `chmod`\n"
                f"  - `grep -l` / `grep -q` / `grep -c` (no content printing)\n"
                f"  - Scripts that you've verified never print secrets\n\n"
                f"See {SECTION_REF}."
            )
        allow()

    allow()


if __name__ == "__main__":
    main()
