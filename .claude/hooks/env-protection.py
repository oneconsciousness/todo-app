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

The command is read the way the shell reads it: split into words and
commands, quotes removed, braces expanded. Each check fails closed:
  - every `.env…` word must be exactly `.env.example` (case-insensitive,
    since macOS file systems are)
  - no glob the shell would expand to a dotfile like `.env`
    (`.e*`, `.[e]nv`, `.*`)
  - no bulk read that would sweep `.env` up: `find -exec <reader>`,
    `xargs <reader>`, recursive grep (`-r`, `-d recurse`), `git grep
    --no-index`, or `rg` searching hidden or ignored files
  - no `docker compose config` without `--no-interpolate`, `docker
    inspect`, or `env` / `printenv` inside a container, which print the
    values compose read from `.env`
  - an unreadable payload or a crash in this hook denies the command

String matching cannot see a path built at run time (`printf '\\x2eenv'`,
a script that opens it). CONTRIBUTING.md § 12.1 rule 3 is the contract for
that case.

Returns Claude Code's PreToolUse deny shape:
  {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                          "permissionDecision": "deny",
                          "permissionDecisionReason": "..."}}

No allow rule in any settings file can override a hook deny.
"""
from __future__ import annotations

import fnmatch
import json
import posixpath
import re
import shlex
import sys
from typing import Iterable, NoReturn

# --- config ---------------------------------------------------------------
ALLOWED_ENV_FILES = frozenset({".env.example"})  # exact basenames agents may touch
# --------------------------------------------------------------------------

ENV_TOKEN_RE = re.compile(r"(?<![A-Za-z0-9_\-\\])(\.env[^\s'\"`;|&<>()]*)", re.IGNORECASE)
GLOB_CHARS = frozenset("*?[")
DOTFILE_PROBES = (".env", ".env.local", ".env.production")
SEPARATORS = frozenset({";", "&&", "||", "|", "&", "(", ")", ";;", "|&"})
COMMAND_PREFIXES = frozenset({"sudo", "command", "exec", "time", "nice", "nohup"})
READERS = frozenset({
    "cat", "head", "tail", "less", "more", "nl", "xxd", "od", "strings", "bat", "tac", "grep", "egrep", "fgrep",
    "rg", "awk", "sed", "base64", "cut", "sort", "uniq", "diff", "jq", "hexdump", "python", "python3", "node",
})
FIND_EXEC = frozenset({"-exec", "-execdir", "-ok", "-okdir"})
XARGS_VALUE_OPTS = frozenset({"-I", "-L", "-n", "-P", "-s", "-d", "-E", "-a", "--delimiter", "--max-args", "--max-procs"})
GREP_VALUE_LETTERS = frozenset("efmABCdD")
RG_VALUE_LETTERS = frozenset("efgtTmABCjMrE")
MAX_BRACE_EXPANSIONS = 256
DOCKER_LEAK_RES = (
    (re.compile(r"\bdocker[\s-]+compose\b(?![^|;&]*--no-interpolate)[^|;&]*\sconfig\b"), "`docker compose config` prints the values compose read from `.env`; add `--no-interpolate`"),
    (re.compile(r"\bdocker\s+(?:container\s+)?inspect\b"), "`docker inspect` prints a container's environment"),
    (re.compile(r"\bdocker[\s-]+(?:compose\s+)?(?:exec|run)\b[^|;&]*\s(?:env|printenv)\b"), "`env` or `printenv` in a container prints its secrets"),
)


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


def shell_tokens(command: str) -> list[str]:
    """Split like the shell: quotes removed, operators as their own tokens; fall back to whitespace."""
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    try:
        return list(lexer)
    except ValueError:
        return command.split()


def commands(tokens: list[str]) -> list[list[str]]:
    """Group tokens into the simple commands the operators separate."""
    groups: list[list[str]] = [[]]
    for token in tokens:
        if token in SEPARATORS:
            groups.append([])
        else:
            groups[-1].append(token)
    return [g for g in groups if g]


def expand_braces(word: str) -> list[str]:
    """Expand `{a,b}` groups the way the shell would, innermost first."""
    match = re.search(r"\{([^{}]*,[^{}]*)\}", word)
    if not match:
        return [word]
    head, tail = word[:match.start()], word[match.end():]
    return [e for part in match.group(1).split(",") for e in expand_braces(head + part + tail)]


def program(words: list[str]) -> tuple[str, list[str]]:
    """Return the command's program name and its arguments, past assignments and prefixes like `sudo`."""
    rest = [w for w in words]
    while rest and ("=" in rest[0] and not rest[0].startswith("-") or posixpath.basename(rest[0]) in COMMAND_PREFIXES):
        rest = rest[1:]
    return (posixpath.basename(rest[0]), rest[1:]) if rest else ("", [])


def short_letters(arg: str, value_letters: frozenset[str]) -> str:
    """Return the flag letters of a short-option cluster, stopping at the first letter that takes a value."""
    if not arg.startswith("-") or arg.startswith("--") or arg == "-":
        return ""
    letters = ""
    for ch in arg[1:]:
        letters += ch
        if ch in value_letters:
            break
    return letters


def forbidden_env_word(command: str, words: Iterable[str]) -> str | None:
    """Return the first `.env…` word that is not exactly an allowed file."""
    found = ENV_TOKEN_RE.findall(command) + [t for w in words for t in ENV_TOKEN_RE.findall(w)]
    return next((t for t in found if t.lower() not in ALLOWED_ENV_FILES), None)


def dotfile_glob(words: Iterable[str]) -> str | None:
    """Return the first glob the shell would expand to an env dotfile."""
    def reaches_env(word: str) -> bool:
        base = posixpath.basename(word.rstrip("/")).lower()
        return base.startswith(".") and any(fnmatch.fnmatchcase(p, base) for p in DOTFILE_PROBES)
    return next((w for w in words if GLOB_CHARS & set(w) and reaches_env(w)), None)


def recursive_grep(args: list[str]) -> bool:
    """True for grep run recursively, in any spelling."""
    pairs = zip(args, args[1:] + [""])
    return any(
        a in ("--recursive", "--dereference-recursive", "--directories=recurse")
        or (a in ("-d", "--directories") and b == "recurse")
        or a == "-drecurse"
        or bool(set(short_letters(a, GREP_VALUE_LETTERS)) & {"r", "R"})
        for a, b in pairs
    )


def rg_reaches_hidden(args: list[str]) -> bool:
    """True when rg would search hidden or ignored files."""
    unrestricted = sum(short_letters(a, RG_VALUE_LETTERS).count("u") for a in args) + args.count("--unrestricted")
    return unrestricted > 0 or "-." in args or any(a == "--hidden" or a.startswith("--no-ignore") or "." in short_letters(a, RG_VALUE_LETTERS) for a in args)


def runs_reader(args: list[str], markers: frozenset[str]) -> bool:
    """True when one of the marker arguments is followed by a program that prints files."""
    return any(a in markers and i + 1 < len(args) and posixpath.basename(args[i + 1]) in READERS for i, a in enumerate(args))


def xargs_reader(args: list[str]) -> bool:
    """True when xargs runs a program that prints its file arguments."""
    rest = list(args)
    while rest and rest[0].startswith("-"):
        rest = rest[2:] if rest[0] in XARGS_VALUE_OPTS else rest[1:]
    return bool(rest) and posixpath.basename(rest[0]) in READERS


def bulk_read(words: list[str]) -> str | None:
    """Return why a single command would sweep env files into its output, or None."""
    name, args = program(words)
    if name in ("grep", "egrep", "fgrep") and recursive_grep(args):
        return "recursive grep reads hidden files such as `.env`; use `rg` (skips hidden and gitignored files) or `git grep`"
    if name == "rg" and rg_reaches_hidden(args):
        return "`rg` with hidden or ignored files enabled would read `.env`"
    if name == "git" and "grep" in args and ({"--no-index", "--no-exclude-standard"} & set(args)):
        return "`git grep --no-index` or `--no-exclude-standard` reads gitignored files such as `.env`"
    if name == "find" and runs_reader(args, FIND_EXEC):
        return "`find -exec` with a program that prints files would read `.env`; use `rg` or name the files"
    if name == "xargs" and xargs_reader(args):
        return "`xargs` feeding a program that prints files would read `.env`; use `rg` or name the files"
    return None


def leak_reason(command: str, groups: list[list[str]]) -> str | None:
    """Return why the command would read env files indirectly, or None."""
    reasons = (bulk_read(words) for words in groups)
    return next((r for r in reasons if r), None) or next((why for pattern, why in DOCKER_LEAK_RES if pattern.search(command)), None)


def decide(command: str) -> None:
    """Deny the command when it could reach an env file other than the example."""
    tokens = shell_tokens(command)
    expanded = [e for t in tokens for e in expand_braces(t)]
    if len(expanded) > MAX_BRACE_EXPANSIONS * max(len(tokens), 1):
        deny("Blocked: the command's brace expansion is too large to check. Name the files directly.")
    target = forbidden_env_word(command, expanded) or dotfile_glob(expanded)
    if target:
        deny(
            f"Reading or modifying `{target}` from Claude Code is blocked. "
            f"`.env*` files hold runtime secrets (API keys, tokens, DB "
            f"credentials) that must never reach an LLM context, transcript, "
            f"or git history. Only `.env.example` is open to agents, by its "
            f"exact name. If you need a value, ask the human directly; to "
            f"create `.env` from the example, ask the human to run the copy. "
            f"A commit message that mentions env files goes through `git commit -F <file>`."
        )
    reason = leak_reason(command, commands(tokens))
    if reason:
        deny(f"Blocked: {reason}. See CONTRIBUTING.md § 12 (Secrets discipline).")


def main() -> None:
    try:
        payload = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        deny("Blocked: the hook payload could not be read, so the command could not be checked for secrets.")
    command = ((payload.get("tool_input") or {}).get("command") or "")
    if command:
        decide(command)
    allow()


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # fail closed: a crash must never let a command through unchecked
        deny(f"Blocked: env-protection failed ({type(exc).__name__}: {exc}), so the command could not be checked.")
