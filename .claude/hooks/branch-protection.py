#!/usr/bin/env python3
"""PreToolUse hook for Bash. Blocks commits and pushes to protected branches, `--no-verify`, and moves of release tags.

Edit the config block; every pattern and message is derived from it. The command is read the way the shell
reads it: split into simple commands, quotes removed, git's global options (`-C`, `-c`, `--git-dir`) skipped.

Behaviour:
  - `git commit` while on a protected branch                         -> DENY
  - `git push` naming a protected branch in any refspec, quoted or not,
    as `<branch>`, `<src>:<branch>`, `refs/heads/<branch>` or `+<…>`  -> DENY
  - `git push --all`, `--mirror` or `--branches`                       -> DENY
  - `git push` with no refspec while on a protected branch           -> DENY
  - `git checkout <protected> && git commit ...` in one command      -> DENY
  - `git commit --no-verify` / `-n` (also inside `-nm`) / `git push --no-verify` -> DENY
  - delete, force-move or re-create an existing release tag, locally or on the remote -> DENY
  - an unreadable payload or a crash in this hook                    -> DENY
  - everything else                                                  -> ALLOW

Returns Claude Code's PreToolUse deny shape on stdout with exit 0:
  {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                          "permissionDecision": "deny",
                          "permissionDecisionReason": "..."}}
"""
from __future__ import annotations

import fnmatch
import json
import os
import re
import subprocess
import sys
from typing import NoReturn

# --- config ---------------------------------------------------------------
PROTECTED = ("main", r"round/[a-z0-9][a-z0-9.-]*")  # regexes: branches nobody commits on or pushes to directly
BASE = "round/<n>-<name>"  # where child branches start and where child PRs go; only a round's parent PR targets main
SECTION_REF = "CONTRIBUTING.md § 8 (the kind-stop protocol)"
TAG_RE = r"v\d+\.\d+\.\d+"  # release tags are never moved; set to "" to skip the guard
# --------------------------------------------------------------------------

PROTECTED_ALT = "|".join(f"(?:{b})" for b in PROTECTED)
PROTECTED_LIST = "`main` and every `round/<n>-<name>` integration branch"
GIT_VALUE_OPTIONS = frozenset({"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--config-env", "--super-prefix", "--exec-path"})
COMMIT_VALUE_LETTERS = frozenset("mFCct")  # short options that take the rest of the cluster or the next word
COMMIT_ATTACHED_LETTERS = frozenset("Su")  # short options whose value can only be attached (`-Skey`, `-uno`)
COMMIT_VALUE_OPTIONS = frozenset({"--message", "--file", "--reuse-message", "--reedit-message", "--template", "--author", "--date", "--trailer", "--fixup", "--squash", "--cleanup"})
PUSH_VALUE_OPTIONS = frozenset({"-o", "--push-option", "--repo", "--receive-pack", "--exec"})
TAG_VALUE_LETTERS = frozenset("mFu")
COMMIT_LONG = ("--no-verify", "--message", "--file", "--reuse-message", "--reedit-message", "--template", "--author", "--date", "--trailer", "--fixup", "--squash", "--cleanup", "--all", "--amend")
PUSH_LONG = ("--no-verify", "--all", "--mirror", "--branches", "--tags", "--force", "--force-with-lease", "--force-if-includes", "--delete", "--dry-run", "--set-upstream", "--push-option", "--repo")
UNSAFE_CONFIG_KEYS = ("remote.", "alias.", "core.hookspath", "push.", "branch.")  # `git -c` keys that redirect a push, rename a command or skip hooks
PROBE_PROTECTED = ("main", "round/1-probe")  # names a wildcard refspec is tested against


def deny(reason: str) -> NoReturn:
    """Print the deny decision and exit."""
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(0)


def allow() -> NoReturn:
    """Exit without a decision."""
    sys.exit(0)


try:
    from shell_words import commands, long_option, program
except Exception as exc:  # fail closed: without its reader the hook cannot check anything
    deny(f"Blocked: branch-protection could not load shell_words.py ({exc}), so the command could not be checked.")


def current_branch(cwd: str) -> str | None:
    """Return the checked-out branch name, or None outside a repo."""
    try:
        result = subprocess.run(["git", "-C", cwd, "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, timeout=2)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def tag_exists(cwd: str, tag: str) -> bool:
    """True when the release tag already exists locally."""
    return subprocess.run(["git", "-C", cwd, "rev-parse", "-q", "--verify", f"refs/tags/{tag}"], capture_output=True, text=True).returncode == 0


def is_protected(branch: str) -> bool:
    """True when the branch name matches one of the protected patterns."""
    return re.fullmatch(PROTECTED_ALT, branch) is not None


def is_release_tag(name: str) -> bool:
    """True when the name, without a `refs/tags/` prefix, is a release tag."""
    return bool(TAG_RE) and re.fullmatch(TAG_RE, name.removeprefix("refs/tags/")) is not None


def git_parts(args: list[str]) -> tuple[dict[str, list[str]], str, list[str]]:
    """Split git's arguments into its global options with values, the subcommand, and the subcommand's arguments."""
    options: dict[str, list[str]] = {}
    rest = list(args)
    while rest and rest[0].startswith("-"):
        name = rest[0].split("=", 1)[0]
        takes_value = name in GIT_VALUE_OPTIONS and "=" not in rest[0]
        value = rest[1] if takes_value and len(rest) > 1 else rest[0].split("=", 1)[-1]
        options.setdefault(name, []).append(value)
        rest = rest[2:] if takes_value else rest[1:]
    return (options, rest[0], rest[1:]) if rest else (options, "", [])


def short_flags(arg: str, value_letters: frozenset[str], attached_letters: frozenset[str] = frozenset()) -> tuple[str, bool]:
    """Return a short-option cluster's flag letters, and whether its last letter takes the next word as a value."""
    if not arg.startswith("-") or arg.startswith("--") or arg == "-":
        return "", False
    for i, ch in enumerate(arg[1:], start=1):
        if ch in value_letters:
            return arg[1:i + 1], i == len(arg) - 1
        if ch in attached_letters:
            return arg[1:i + 1], False
    return arg[1:], False


def parse_options(args: list[str], value_letters: frozenset[str], value_options: frozenset[str], known_long: tuple[str, ...] = (), attached_letters: frozenset[str] = frozenset()) -> tuple[set[str], list[str]]:
    """Split arguments into the option names used (short letters, long names resolved from abbreviations) and the positional words."""
    used: set[str] = set()
    positional: list[str] = []
    skip = False
    for arg in args:
        if skip:
            skip = False
        elif arg == "--":
            skip = False
        elif arg.startswith("--"):
            name = long_option(arg, known_long) if known_long else arg.split("=", 1)[0]
            used.add(name)
            skip = name in value_options and "=" not in arg
        elif arg.startswith("-") and arg != "-":
            letters, takes_next = short_flags(arg, value_letters, attached_letters)
            used.update(f"-{ch}" for ch in letters)
            skip = takes_next or arg in value_options
        else:
            positional.append(arg)
    return used, positional


def refspec_target(spec: str, branch: str | None) -> tuple[str, bool]:
    """Return a refspec's destination branch name, and whether it is forced with `+`."""
    forced = spec.startswith("+")
    spec = spec.lstrip("+")
    dst = spec.split(":", 1)[1] if ":" in spec else spec
    dst = dst.removeprefix("refs/heads/")
    return (branch or "HEAD") if dst == "HEAD" else dst, forced


def check_commit(args: list[str], branch: str | None, chained_checkout: bool) -> None:
    """Deny a commit that skips hooks or lands on a protected branch."""
    used, _ = parse_options(args, COMMIT_VALUE_LETTERS, COMMIT_VALUE_OPTIONS, COMMIT_LONG, COMMIT_ATTACHED_LETTERS)
    if {"--no-verify", "-n"} & used:
        deny(f"`--no-verify` skips the repo's git hooks. That is blocked here; fix what the hook reports instead. See {SECTION_REF}.")
    if branch is not None and is_protected(branch):
        deny(
            f"Heads up — this would commit directly on `{branch}`. "
            f"Our flow: branch off `{BASE}`, commit there, open a child PR. "
            f"Try: `git checkout -b <type>/<descriptive-name>` then re-run your commit. "
            f"If there's a reason to override, see {SECTION_REF}."
        )
    if chained_checkout:
        deny(
            f"Heads up — this chains a checkout to a protected branch ({PROTECTED_LIST}) with a "
            f"commit, which would land the commit on a shared branch. Try: "
            f"`git checkout -b <type>/<descriptive-name> {BASE}` and commit there. See {SECTION_REF}."
        )


def check_push(args: list[str], branch: str | None) -> None:
    """Deny a push that skips hooks, reaches a protected branch, or moves or deletes a release tag."""
    used, positional = parse_options(args, frozenset(), PUSH_VALUE_OPTIONS, PUSH_LONG)
    flags = used | {f"-{ch}" for a in args if a.startswith("-") and not a.startswith("--") for ch in a[1:]}
    if "--no-verify" in flags:
        deny(f"`--no-verify` skips the repo's git hooks. That is blocked here; fix what the hook reports instead. See {SECTION_REF}.")
    if {"--all", "--mirror", "--branches"} & flags:
        deny(f"`git push --all`, `--mirror` or `--branches` would push the protected branches ({PROTECTED_LIST}). Push your one branch instead. See {SECTION_REF}.")
    forced = bool({"--force", "-f", "--force-with-lease", "--force-if-includes"} & flags)
    deleting = bool({"--delete", "-d"} & flags)
    specs = positional[1:]
    if not specs and branch is not None and is_protected(branch):
        deny(f"Heads up — this would push directly to `{branch}` (your current branch is shared). Push a feature branch and open a child PR into `{BASE}`. See {SECTION_REF}.")
    if forced and "--tags" in flags:
        deny(f"Blocked: force-pushing tags would move release tags. A release tag is never moved; cut the next version. See {SECTION_REF}.")
    for spec in specs:
        target, forced_spec = refspec_target(spec, branch)
        if any(c in target for c in "*?[") and (any(fnmatch.fnmatchcase(p, target) for p in PROBE_PROTECTED) or (forced or forced_spec) and fnmatch.fnmatchcase("refs/tags/v1.0.0", target)):
            deny(f"Blocked: the wildcard refspec `{spec}` would push protected branches or move release tags. Push your one branch by name. See {SECTION_REF}.")
        if is_release_tag(target) and (forced or forced_spec or deleting or spec.startswith(":")):
            deny(f"Blocked: this would move or delete the release tag `{target}` on the remote. A release tag is never moved or deleted; cut the next version. See {SECTION_REF}.")
        if is_protected(target):
            if forced or forced_spec:
                deny(
                    f"Force-pushing to a protected branch ({PROTECTED_LIST}) is blocked unconditionally — "
                    "it rewrites history everyone else has based work on. If you have an authorized "
                    f"exception (incident response, security rotation), do this manually outside Claude Code. See {SECTION_REF}."
                )
            deny(
                f"Heads up — this would push directly to `{target}`, a protected branch. "
                f"Our flow: push your feature branch, then open a child PR into `{BASE}`. "
                f"Try: `git push -u origin <your-feature-branch>`. If there's a reason to override, see {SECTION_REF}."
            )


def check_tag(args: list[str], cwd: str) -> None:
    """Deny deleting, force-moving or re-creating an existing release tag."""
    used, positional = parse_options(args, TAG_VALUE_LETTERS, frozenset({"--message", "--file", "--local-user"}))
    names = [p for p in positional if is_release_tag(p)]
    if not names or {"-l", "--list"} & used:
        return
    if {"-d", "-D", "--delete"} & used:
        deny(f"Blocked: deleting the release tag `{names[0]}`. A release tag is never moved or deleted; cut the next version. See {SECTION_REF}.")
    if {"-f", "--force"} & used:
        deny(f"Blocked: moving the release tag `{names[0]}` with --force. A release tag is never moved; cut the next version. See {SECTION_REF}.")
    if tag_exists(cwd, names[0]):
        deny(f"Blocked: re-tagging `{names[0]}`, which already exists. A release tag is never moved; cut the next version. See {SECTION_REF}.")


def checkout_target(args: list[str]) -> str:
    """Return the branch a checkout or switch leaves you on: the new branch for `-b`/`-c`, else the first name."""
    new = next((args[i + 1] for i, a in enumerate(args[:-1]) if a in ("-b", "-B", "-c", "-C", "--orphan")), None)
    return new or next((a for a in args if not a.startswith("-")), "")


def check_config(options: dict[str, list[str]]) -> None:
    """Deny `git -c` settings that could redirect a push, rename a command or switch off hooks."""
    keys = [v.split("=", 1)[0].lower() for v in options.get("-c", []) + options.get("--config-env", [])]
    bad = next((k for k in keys if k.startswith(UNSAFE_CONFIG_KEYS)), None)
    if bad:
        deny(f"Blocked: `git -c {bad}=…` can redirect a push, rename a command or skip hooks. Use the command itself. See {SECTION_REF}.")


def check_output_option(sub: str, args: list[str]) -> None:
    """Deny `--output` (or an abbreviation) on git's display commands, which writes any file without the Edit permission."""
    if sub in ("diff", "log", "show", "format-patch", "range-diff") and any("--output".startswith(a.split("=", 1)[0]) and len(a.split("=", 1)[0]) >= 5 for a in args if a.startswith("--")):
        deny(f"Blocked: `git {sub} --output` writes a file, which goes around the Edit permission and could overwrite a hook. Print to stdout instead. See {SECTION_REF}.")


def check_branch(args: list[str]) -> None:
    """Deny force-moving, deleting, renaming or copying onto a protected branch with `git branch`."""
    used, positional = parse_options(args, frozenset(), frozenset(), ("--force", "--delete", "--move", "--copy"))
    rewrites = {"-f", "-d", "-D", "-m", "-M", "-c", "-C", "--force", "--delete", "--move", "--copy"} & used
    target = next((p for p in positional if is_protected(p)), None)
    if rewrites and target:
        deny(f"Blocked: `git branch {sorted(rewrites)[0]}` on the protected branch `{target}` rewrites a shared branch locally. See {SECTION_REF}.")


def check_update_ref(args: list[str]) -> None:
    """Deny moving or deleting a protected branch or a release tag through plumbing."""
    refs = [a for a in args if a.startswith("refs/")]
    if any(is_protected(r.removeprefix("refs/heads/")) for r in refs if r.startswith("refs/heads/")) or any(is_release_tag(r) for r in refs if r.startswith("refs/tags/")):
        deny(f"Blocked: `git update-ref` on a protected branch or a release tag goes around every guard. See {SECTION_REF}.")


def decide(command: str, cwd: str) -> None:
    """Check every git command in the line, following `cd` and `git -C` to the repo each one runs in."""
    here = cwd
    planned: list[tuple[str, str, list[str]]] = []
    for cmd in commands(command):
        name, args = program(cmd.words)
        if name == "cd":
            here = os.path.normpath(os.path.join(here, os.path.expanduser(args[0] if args else "~")))
        elif name == "git":
            options, sub, sub_args = git_parts(args)
            check_config(options)
            where = os.path.normpath(os.path.join(here, *options["-C"])) if "-C" in options else here
            planned.append((where, sub, sub_args))
    checks_out_protected = any(sub in ("checkout", "switch") and is_protected(checkout_target(a)) for _, sub, a in planned)
    for where, sub, sub_args in planned:
        branch = current_branch(where)
        if sub == "commit":
            check_commit(sub_args, branch, checks_out_protected)
        elif sub == "push":
            check_push(sub_args, branch)
        elif sub == "tag":
            check_tag(sub_args, where)
        elif sub == "update-ref":
            check_update_ref(sub_args)
        elif sub == "branch":
            check_branch(sub_args)
        check_output_option(sub, sub_args)


def main() -> None:
    """Read the hook payload and decide."""
    try:
        payload = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        deny("Blocked: the hook payload could not be read, so the command could not be checked against branch protection.")
    tool_input = payload.get("tool_input") or {}
    command = (tool_input.get("command") or "").strip()
    if command:
        decide(command, payload.get("cwd") or tool_input.get("cwd") or os.getcwd())
    allow()


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # fail closed: a crash must never let a commit or push through unchecked
        deny(f"Blocked: branch-protection failed ({type(exc).__name__}: {exc}), so the command could not be checked.")
