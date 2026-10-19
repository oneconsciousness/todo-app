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

The command is read the way the shell reads it (shell_words.py). Each
check fails closed:
  - every `.env…` word, after quote removal and brace or range
    expansion, must be exactly `.env.example` (case-insensitive)
  - no glob the shell would expand to a dotfile like `.env`
  - no bulk read that could sweep `.env` up. `find -exec` and `xargs`
    may run only programs that print no file contents (or a quiet grep,
    or sed -i), unless xargs reads from a gitignore-aware lister such as
    `git ls-files` or `rg -l`. Recursive grep or ugrep, `git grep
    --no-index`, `rg` or `ug` on hidden or ignored files, `git add
    --force`, `git stash --all` and `tar` writing an archive to stdout
    are blocked, long options matched by any abbreviation git or grep
    accepts.
  - no docker command that prints the values compose read from `.env`
  - an unreadable payload or a crash in this hook denies the command

What string matching cannot see (a path built at run time, a loop
reading file names, a script that opens the file) is listed in
CONTRIBUTING.md § 12.6, with the backstops that cover it.

No allow rule in any settings file can override a hook deny.
"""
from __future__ import annotations

import fnmatch
import json
import posixpath
import re
import sys
from typing import Iterable, NoReturn


def deny(reason: str) -> NoReturn:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(0)


try:
    from shell_words import Command, commands, expand, expansion_count, long_option, program
except Exception as exc:  # fail closed: without its reader the hook cannot check anything
    deny(f"Blocked: env-protection could not load shell_words.py ({exc}), so the command could not be checked.")

# --- config ---------------------------------------------------------------
ALLOWED_ENV_FILES = frozenset({".env.example"})  # exact basenames agents may touch
# --------------------------------------------------------------------------

ENV_WORD_RE = re.compile(r"(?<![A-Za-z0-9_\-\\])(\.env[^\s'\"`;|&<>()]*)", re.IGNORECASE)
GLOB_CHARS = frozenset("*?[")
DOTFILE_PROBES = (".env", ".env.local", ".env.production")
MAX_EXPANSIONS = 512
GREP_FAMILY = frozenset({"grep", "egrep", "fgrep", "ugrep", "ug"})
GREP_VALUE_LETTERS = frozenset("efmABCdD")
GREP_LONG = ("--recursive", "--dereference-recursive", "--directories", "--hidden")
RG_VALUE_LETTERS = frozenset("efgtTmABCjMrE")
RG_LONG = ("--hidden", "--no-ignore", "--no-ignore-vcs", "--no-ignore-dot", "--no-ignore-parent", "--no-ignore-global", "--no-ignore-files", "--unrestricted")
GIT_GREP_LONG = ("--no-index", "--no-exclude-standard", "--exclude-standard")
GIT_ADD_LONG = ("--force",)
GIT_STASH_LONG = ("--all",)
QUIET_GREP = frozenset({"-l", "-L", "-c", "-q", "--files-with-matches", "--files-without-match", "--count", "--quiet", "--silent"})
SAFE_EXEC = frozenset({"rm", "rmdir", "chmod", "chown", "touch", "mkdir", "ls", "stat", "file", "wc", "du", "echo", "true", "test", "basename", "dirname", "realpath"})
SAFE_SOURCES = frozenset({"git", "rg", "fd", "echo", "printf"})  # listers that skip gitignored and hidden files, or print only what they are told
FIND_EXEC = frozenset({"-exec", "-execdir", "-ok", "-okdir"})
XARGS_VALUE_OPTIONS = frozenset({"-I", "-L", "-n", "-P", "-s", "-d", "-E", "-a", "--delimiter", "--max-args", "--max-procs", "--replace"})
DOCKER_LEAK_RES = (
    (re.compile(r"\bdocker[\s-]+compose\b(?![^|;&]*--no-interpolate)[^|;&]*\s(?:config|convert)\b"), "`docker compose config` or `convert` prints the values compose read from `.env`; add `--no-interpolate`"),
    (re.compile(r"\bdocker\s+(?:container\s+)?inspect\b"), "`docker inspect` prints a container's environment"),
    (re.compile(r"\bdocker[\s-]+(?:compose\s+)?(?:exec|run)\b[^|;&]*(?:\bprintenv\b|(?<![-\w])env\b|environ)"), "printing a container's environment shows its secrets"),
)


def short_letters(arg: str, value_letters: frozenset[str]) -> str:
    """Return the flag letters of a short-option cluster, up to the first letter that takes a value."""
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
    found = ENV_WORD_RE.findall(command) + [t for w in words for t in ENV_WORD_RE.findall(w)]
    return next((t for t in found if t.lower() not in ALLOWED_ENV_FILES), None)


def dotfile_glob(words: Iterable[str]) -> str | None:
    """Return the first glob the shell would expand to an env dotfile."""
    def reaches_env(word: str) -> bool:
        base = posixpath.basename(word.rstrip("/")).lower()
        return base.startswith(".") and any(fnmatch.fnmatchcase(p, base) for p in DOTFILE_PROBES)
    return next((w for w in words if GLOB_CHARS & set(w) and reaches_env(w)), None)


def prints_nothing(words: list[str]) -> bool:
    """True when a program run by find or xargs would print no file contents."""
    name, args = program(words)
    if name in SAFE_EXEC:
        return True
    if name in GREP_FAMILY or name == "rg":
        return bool(QUIET_GREP & {long_option(a, QUIET_GREP) for a in args})
    return name == "sed" and any(a == "-i" or a.startswith(("-i", "--in-place")) for a in args)


def recursive_grep(name: str, args: list[str]) -> bool:
    """True for grep or ugrep searching recursively or into hidden files, in any spelling."""
    resolved = [(long_option(a, GREP_LONG), a) for a in args]
    pairs = zip(resolved, resolved[1:] + [("", "")])
    return any(
        r in ("--recursive", "--dereference-recursive", "--hidden")
        or (r == "--directories" and (raw.endswith("=recurse") or nxt[1] == "recurse"))
        or (raw == "-d" and nxt[1] == "recurse") or raw == "-drecurse"
        or bool(set(short_letters(raw, GREP_VALUE_LETTERS)) & ({"r", "R", "."} if name in ("ugrep", "ug") else {"r", "R"}))
        for (r, raw), nxt in pairs
    )


def rg_reaches_hidden(args: list[str]) -> bool:
    """True when rg would search hidden or ignored files."""
    resolved = [long_option(a, RG_LONG) for a in args]
    letters = "".join(short_letters(a, RG_VALUE_LETTERS) for a in args)
    return "u" in letters or "." in letters or any(r in RG_LONG for r in resolved)


def runs_unsafe_program(args: list[str]) -> bool:
    """True when find runs, through -exec or -ok, a program that could print file contents."""
    starts = [i + 1 for i, a in enumerate(args) if a in FIND_EXEC]
    return any(not prints_nothing(args[i:]) for i in starts)


def xargs_unsafe(cmd: Command, args: list[str]) -> bool:
    """True when xargs runs a program that prints files, fed by something that could list `.env`."""
    rest = list(args)
    while rest and rest[0].startswith("-"):
        rest = rest[2:] if rest[0] in XARGS_VALUE_OPTIONS else rest[1:]
    source, source_args = program(cmd.piped_from)
    safe_source = source in SAFE_SOURCES and not (source == "rg" and rg_reaches_hidden(source_args))
    return bool(rest) and not prints_nothing(rest) and not safe_source


def tar_to_stdout(args: list[str]) -> bool:
    """True when tar creates an archive and writes it to stdout (`-` as the file, or no file at all)."""
    clusters = [a.lstrip("-") for a in args if a.startswith("-") and not a.startswith("--")] + ([args[0]] if args and not args[0].startswith("-") else [])
    creates = "--create" in args or any("c" in c for c in clusters)
    names_file = "--file" in args or any("f" in c for c in clusters)
    return creates and ("-" in args or "--to-stdout" in args or not names_file)


def bulk_read(cmd: Command) -> str | None:
    """Return why one command would sweep env files into its output or into git, or None."""
    name, args = program(cmd.words)
    if name in GREP_FAMILY and recursive_grep(name, args):
        return "recursive grep reads hidden files such as `.env`; use `rg` (skips hidden and gitignored files) or `git grep`"
    if name == "rg" and rg_reaches_hidden(args):
        return "`rg` with hidden or ignored files enabled would read `.env`"
    if name == "git":
        sub = next((a for a in args if not a.startswith("-")), "")
        resolved = {long_option(a, GIT_GREP_LONG + GIT_ADD_LONG + GIT_STASH_LONG) for a in args}
        letters = "".join(short_letters(a, frozenset("m")) for a in args)
        if sub == "grep" and {"--no-index", "--no-exclude-standard"} & resolved:
            return "`git grep --no-index` or `--no-exclude-standard` reads gitignored files such as `.env`"
        if sub == "add" and ("--force" in resolved or "f" in letters):
            return "`git add --force` stages gitignored files such as `.env`"
        if sub == "stash" and ("--all" in resolved or "a" in letters):
            return "`git stash --all` stashes gitignored files such as `.env`, and the stash can then be printed"
    if name == "find" and runs_unsafe_program(args):
        return "`find -exec` may only run programs that print no file contents; use `rg`, or name the files"
    if name == "xargs" and xargs_unsafe(cmd, args):
        return "`xargs` may feed files to a printing program only from `git ls-files` or `rg -l`; use those, or name the files"
    if name == "tar" and tar_to_stdout(args):
        return "`tar` writing an archive to stdout would carry `.env` along"
    return None


def decide(command: str) -> None:
    """Deny the command when it could reach an env file other than the example."""
    cmds = commands(command)
    words = [w for c in cmds for w in c.words]
    if any(expansion_count(w) > MAX_EXPANSIONS for w in words):
        deny("Blocked: the command's brace expansion is too large to check. Name the files directly.")
    expanded = [e for w in words for e in expand(w)]
    target = forbidden_env_word(command, expanded) or dotfile_glob(expanded)
    if target:
        deny(
            f"Reading or modifying `{target}` from Claude Code is blocked. "
            f"`.env*` files hold runtime secrets (API keys, tokens, DB "
            f"credentials) that must never reach an LLM context, transcript, "
            f"or git history. Only `.env.example` is open to agents, by its "
            f"exact name. If you need a value, ask the human directly; to "
            f"create `.env` from the example, ask the human to run the copy. "
            f"For text that mentions env files, use the Write tool and `git commit -F <file>`."
        )
    reason = next((r for r in (bulk_read(c) for c in cmds) if r), None) or next((why for pattern, why in DOCKER_LEAK_RES if pattern.search(command)), None)
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
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # fail closed: a crash must never let a command through unchecked
        deny(f"Blocked: env-protection failed ({type(exc).__name__}: {exc}), so the command could not be checked.")
