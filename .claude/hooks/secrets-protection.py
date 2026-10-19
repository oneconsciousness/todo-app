#!/usr/bin/env python3
"""
PreToolUse hook for Claude Code's Read / Grep / Edit / Write / MultiEdit / NotebookEdit / Bash tools.
Blocks reads and writes of secrets files AND blocks Bash reads-that-print secrets.

See CONTRIBUTING.md § 12 (Secrets discipline) for the full rationale.

Behavior summary:
  - Read/Edit/Write/MultiEdit/NotebookEdit on a secrets path            -> DENY
  - Grep on a secrets path, or with a glob aimed at env dotfiles        -> DENY
  - `.env.example` (exact name, any case) is not a secrets path, unless
    it is a symlink whose target is one                                  -> ALLOW
  - Bash command whose program prints files (cat, head, sed without -i,
    base64, grep without -l/-c/-q, awk, ...) given a secrets path, with
    the command read the way the shell reads it (quotes removed, any
    directory on the program name ignored)                               -> DENY
  - Bash commands that only inspect or mutate a key file in place
    (ls, wc, chmod, sed -i)                                              -> ALLOW
  - an unreadable payload or a crash in this hook                        -> DENY
  - everything else                                                      -> ALLOW

Env files get stricter treatment in env-protection.py: no agent command
may touch them at all, except `.env.example`.

Secret patterns (matched case-insensitively against the basename, or against any path segment):
  - .env, .env.*  (any env file)
  - *.pem, *.key, *.crt, *.p12, *.pfx, *.jks  (cryptographic keys/certs)
  - credentials.<data ext>, secrets.<data ext>
    (named secret stores; source files such as credentials.py are not)
  - id_rsa, id_rsa.*, id_ed25519, id_ed25519.* (SSH keys)
  - .npmrc, .pypirc, .docker/config.json, .aws/credentials, .ssh/, .gnupg/, .kube/config

Returns Claude Code's PreToolUse deny shape:
  {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                          "permissionDecision": "deny",
                          "permissionDecisionReason": "..."}}
"""
from __future__ import annotations

import fnmatch
import json
import os
import sys
from typing import NoReturn

SECTION_REF = "CONTRIBUTING.md § 12 (Secrets discipline)"
ALLOWED_ENV_FILES = frozenset({".env.example"})  # the committed template; exact basenames only
ENV_DOTFILE_PROBES = (".env", ".env.local", ".env.production")
DATA_EXTENSIONS = ("json", "yaml", "yml", "toml", "env", "ini", "cfg", "conf", "txt", "xml", "csv", "properties")

# Pattern matched against the basename. Using fnmatch globs.
SECRET_BASENAME_GLOBS = (
    ".env", ".env.*", "*.pem", "*.key", "*.crt", "*.p12", "*.pfx", "*.jks",
    "id_rsa", "id_rsa.*", "id_ed25519", "id_ed25519.*", ".npmrc", ".pypirc",
    *(f"{name}.{ext}" for name in ("credentials", "secrets") for ext in DATA_EXTENSIONS),
)

# Pattern matched against any path segment.
SECRET_PATH_FRAGMENTS = (".docker/config.json", ".aws/credentials", ".aws/config", ".ssh/", ".gnupg/", ".kube/config")

WRITE_TOOLS = frozenset({"Edit", "Write", "MultiEdit", "NotebookEdit"})
# Programs that print the files they are given. grep and sed need their flags read first.
PRINTING_READERS = frozenset({
    "cat", "head", "tail", "less", "more", "nl", "xxd", "od", "strings", "bat", "tac", "awk", "base64", "cut", "sort",
    "uniq", "diff", "jq", "hexdump", "rev", "fold", "cp", "rg", "egrep", "fgrep", "ugrep", "ug", "paste", "openssl", "dd",
    "perl", "python", "python3", "node", "ruby", "ln", "tee", "column", "comm", "join", "split", "zcat", "gzip", "zip",
})
GIT_PRINTING = frozenset({"diff", "show", "blame", "cat-file", "grep", "log", "format-patch"})
GREP_LIKE = frozenset({"grep", "egrep", "fgrep", "rg", "ugrep", "ug"})
GREP_QUIET = frozenset({"-l", "--files-with-matches", "-L", "--files-without-match", "-c", "--count", "-q", "--quiet", "--silent"})


def deny(reason: str) -> NoReturn:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(0)


def allow() -> NoReturn:
    sys.exit(0)


try:
    from shell_words import commands, program
except Exception as exc:  # fail closed: without its reader the hook cannot check Bash commands
    deny(f"Blocked: secrets-protection could not load shell_words.py ({exc}), so the call could not be checked.")


def is_secret_path(path: str) -> bool:
    """True when the path names a secrets file; `.env.example` only when it resolves to another file."""
    if not path:
        return False
    norm = path.replace("\\", "/")
    base = os.path.basename(norm.rstrip("/")).lower()
    if base in ALLOWED_ENV_FILES:
        real = os.path.realpath(norm)
        return os.path.basename(real).lower() not in ALLOWED_ENV_FILES or any(frag in real for frag in SECRET_PATH_FRAGMENTS)
    return any(fnmatch.fnmatchcase(base, glob) for glob in SECRET_BASENAME_GLOBS) or any(frag in norm for frag in SECRET_PATH_FRAGMENTS)


def targets_env_dotfiles(glob: str) -> bool:
    """True when a search glob names or could expand to an env dotfile other than `.env.example`."""
    pattern = os.path.basename(glob.replace("\\", "/").rstrip("/")).lower()
    if not pattern or pattern in ALLOWED_ENV_FILES:
        return False
    return (pattern.startswith(".") or "env" in pattern) and any(fnmatch.fnmatchcase(p, pattern) for p in ENV_DOTFILE_PROBES)


def prints_its_files(name: str, args: list[str]) -> bool:
    """True when this program, with these flags, prints the content of the files it is given."""
    if name in GREP_LIKE:
        return not (GREP_QUIET & set(args))
    if name == "sed":
        return not any(a == "-i" or a.startswith(("-i", "--in-place")) for a in args)
    return name in PRINTING_READERS


def file_operands(name: str, args: list[str]) -> list[str]:
    """Return the arguments that name files, including values after `=` (`if=key`, `--in=key`); for grep-like programs the first word is the pattern, unless -e or -f gives it."""
    positional = [a for a in args if not a.startswith("-")]
    values = [a.split("=", 1)[1] for a in args if "=" in a]
    pattern_given = any(a in ("-e", "-f", "--regexp", "--file") or a.startswith(("--regexp=", "--file=")) for a in args)
    return (positional[1:] if name in GREP_LIKE and not pattern_given else positional) + values


def redirected_secret(words: tuple[str, ...]) -> str | None:
    """Return a secrets path the command reads through input redirection (`< key`), or None."""
    return next((words[i + 1] for i, w in enumerate(words[:-1]) if w in ("<", "<<<", "<>") and is_secret_path(words[i + 1])), None)


def printed_secret(command: str) -> str | None:
    """Return the first secrets path the command would print or copy, or None."""
    for cmd in commands(command):
        name, args = program(cmd.words)
        redirected = redirected_secret(cmd.words)
        if redirected:
            return redirected
        if name == "git":
            sub = next((a for a in args if not a.startswith("-")), "")
            secret = next((a for a in args if sub in GIT_PRINTING and is_secret_path(a)), None)
        elif prints_its_files(name, args):
            secret = next((a for a in file_operands(name, args) if is_secret_path(a)), None)
        else:
            secret = None
        if secret:
            return secret
    return None


def decide(tool_name: str, tool_input: dict[str, str]) -> None:
    """Deny the tool call when it would read, print or write a secrets file."""
    if tool_name == "Read":
        path = tool_input.get("file_path") or ""
        if is_secret_path(path):
            deny(
                f"Heads up — `Read` on `{path}` is blocked because the path "
                f"matches a secrets-file pattern. Its contents would land in "
                f"the agent's context. Only `.env.example` is open to agents. "
                f"Ask the human for the value you need.\n\nSee {SECTION_REF}."
            )
    elif tool_name == "Grep":
        path = tool_input.get("path") or ""
        glob = tool_input.get("glob") or ""
        if is_secret_path(path) or targets_env_dotfiles(glob):
            deny(
                f"Heads up — this `Grep` would search `{path or glob}`, which "
                f"matches a secrets-file pattern, and print matching lines. "
                f"Only `.env.example` is open to agents.\n\nSee {SECTION_REF}."
            )
    elif tool_name in WRITE_TOOLS:
        path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
        if is_secret_path(path):
            deny(
                f"Heads up — `{tool_name}` on `{path}` is blocked because the "
                f"path matches a secrets-file pattern. Env files, key material "
                f"and credential stores are human-managed; only `.env.example` "
                f"is open to agents.\n\n"
                f"What to do instead: add the setting to `.env.example` with a "
                f"safe local value, or post the exact change in chat and ask "
                f"the human to make it.\n\nSee {SECTION_REF}."
            )
    elif tool_name == "Bash":
        matched = printed_secret(tool_input.get("command") or "")
        if matched:
            deny(
                f"Heads up — this Bash command would read `{matched}` and "
                f"print it to stdout. The contents would land in the agent's "
                f"context, exposing secrets.\n\n"
                f"Allowed alternatives for key material (never for env files):\n"
                f"  - Existence and metadata only: `ls`, `wc -l`, `stat`, `chmod`\n"
                f"  - `grep -l` / `grep -q` / `grep -c` (no content printed)\n"
                f"  - In-place change that prints nothing: `sed -i`\n"
                f"For a value you need, ask the human.\n\nSee {SECTION_REF}."
            )


def main() -> None:
    try:
        payload = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        deny("Blocked: the hook payload could not be read, so the call could not be checked for secrets.")
    decide(payload.get("tool_name") or "", payload.get("tool_input") or {})
    allow()


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # fail closed: a crash must never let a call through unchecked
        deny(f"Blocked: secrets-protection failed ({type(exc).__name__}: {exc}), so the call could not be checked.")
