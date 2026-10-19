"""Read a shell command line the way the shell would, for the guard hooks. Standard library only, Python 3.9+.

The guards match text, so they see what the shell would see after quote removal, brace and range expansion,
and with wrappers (`sudo`, `env`, `if … then`, `{ … }`, backticks, `$( … )`) peeled away. They cannot see paths
built at run time or what a script does once it runs; CONTRIBUTING.md § 12.6 says so.
"""
from __future__ import annotations

import re
import shlex
from dataclasses import dataclass
from typing import Iterable

SEPARATORS = frozenset({";", "&&", "||", "|", "&", "(", ")", ";;", "|&", "\n"})
SHELL_KEYWORDS = frozenset({"if", "then", "else", "elif", "fi", "do", "done", "while", "until", "for", "in", "case", "esac", "{", "}", "!", "function", "select"})
WRAPPER_VALUE_OPTIONS: dict[str, frozenset[str]] = {  # wrapper -> its options that take the next word as a value
    "sudo": frozenset({"-u", "-g", "-C", "-h", "-p", "-U", "-r", "-t", "-D", "-R"}),
    "doas": frozenset({"-u", "-C"}),
    "env": frozenset({"-u", "-S", "-C", "--unset", "--chdir", "--split-string"}),
    "nice": frozenset({"-n"}),
    "command": frozenset(), "exec": frozenset({"-a"}), "time": frozenset({"-f", "-o"}), "nohup": frozenset(),
    "stdbuf": frozenset(), "timeout": frozenset({"-s", "-k", "--signal", "--kill-after"}),
}
WRAPPERS_WITH_ARGUMENT = frozenset({"timeout"})  # wrappers whose first plain word is their own argument, not the program
RUNNERS: dict[str, str] = {"uv": "run", "poetry": "run", "pipx": "run", "pnpm": "exec", "npm": "exec"}  # tool -> subcommand that runs a program
PLAIN_RUNNERS = frozenset({"uvx", "npx", "bunx", "pnpx"})
RUNNER_VALUE_OPTIONS = frozenset({"--with", "--python", "-p", "--project", "--directory", "--package", "--extra", "--group", "--from", "--env-file", "--spec", "-c"})
BRACE_GROUP = re.compile(r"\{([^{}]*)\}")
RANGE = re.compile(r"^(-?\d+|[A-Za-z])\.\.(-?\d+|[A-Za-z])(?:\.\.-?\d+)?$")
ZSH_ALTERNATION = re.compile(r"(?<=[^\s(|$])\(([^()\s]*\|[^()\s]*)\)")


@dataclass(frozen=True)
class Command:
    """One simple command, and the command whose output is piped into it, if any."""

    words: tuple[str, ...]
    piped_from: tuple[str, ...] = ()


def tokens(command: str) -> list[str]:
    """Split like the shell: quotes removed, operators and command substitutions as separators."""
    text = ZSH_ALTERNATION.sub(lambda m: "{" + m.group(1).replace("|", ",") + "}", command)
    text = text.replace("`", " ; ").replace("$(", " ; ").replace("<(", " ; ").replace(">(", " ; ")
    lexer = shlex.shlex(text, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    try:
        return list(lexer)
    except ValueError:
        return text.split()


def commands(command: str) -> list[Command]:
    """Group the tokens into simple commands, remembering which command each one reads from through a pipe."""
    groups: list[tuple[str, list[str]]] = [("", [])]
    for token in tokens(command):
        if token in SEPARATORS:
            groups.append((token, []))
        else:
            groups[-1][1].append(token)
    result: list[Command] = []
    for i, (separator, words) in enumerate(groups):
        if words:
            source = groups[i - 1][1] if separator == "|" and i > 0 else []
            result.append(Command(tuple(words), tuple(source)))
    return result


def program(words: Iterable[str]) -> tuple[str, list[str]]:
    """Return the program's base name and its arguments, past keywords, assignments and wrappers like `sudo -u x`."""
    rest = list(words)
    while rest:
        head = rest[0]
        if head in SHELL_KEYWORDS or ("=" in head and not head.startswith("-") and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", head)):
            rest = rest[1:]
        elif head.rsplit("/", 1)[-1] in PLAIN_RUNNERS or (head.rsplit("/", 1)[-1] in RUNNERS and len(rest) > 1 and rest[1] == RUNNERS[head.rsplit("/", 1)[-1]]):
            rest = rest[1:] if head.rsplit("/", 1)[-1] in PLAIN_RUNNERS else rest[2:]
            while rest and rest[0].startswith("-"):
                rest = rest[2:] if rest[0] in RUNNER_VALUE_OPTIONS else rest[1:]
        elif head.rsplit("/", 1)[-1] in WRAPPER_VALUE_OPTIONS:
            wrapper = head.rsplit("/", 1)[-1]
            rest = rest[1:]
            while rest and rest[0].startswith("-"):
                rest = rest[2:] if rest[0] in WRAPPER_VALUE_OPTIONS[wrapper] else rest[1:]
            rest = rest[1:] if wrapper in WRAPPERS_WITH_ARGUMENT and rest else rest
        else:
            break
    return (rest[0].rsplit("/", 1)[-1], rest[1:]) if rest else ("", [])


def long_option(arg: str, known: Iterable[str]) -> str:
    """Resolve an abbreviated long option (`--recur`) to the known option it unambiguously starts, else return it as is."""
    name = arg.split("=", 1)[0]
    if not name.startswith("--") or len(name) < 4:
        return name
    matches = [k for k in known if k.startswith(name)]
    return matches[0] if len(matches) == 1 else name


def expansion_count(word: str) -> int:
    """Return how many words brace and range expansion would make of this word, without expanding it."""
    count = 1
    for group in BRACE_GROUP.findall(word):
        rng = RANGE.match(group)
        if rng:
            a, b = rng.group(1), rng.group(2)
            count *= abs(int(b) - int(a)) + 1 if a.lstrip("-").isdigit() and b.lstrip("-").isdigit() else abs(ord(b) - ord(a)) + 1
        elif "," in group:
            count *= group.count(",") + 1
    return count


def expand(word: str) -> list[str]:
    """Expand `{a,b}` alternatives and `{a..c}` ranges the way bash and zsh would, innermost first."""
    for match in BRACE_GROUP.finditer(word):
        group = match.group(1)
        rng = RANGE.match(group)
        if rng:
            a, b = rng.group(1), rng.group(2)
            if a.lstrip("-").isdigit() and b.lstrip("-").isdigit():
                lo, hi = int(a), int(b)
                parts = [str(n) for n in (range(lo, hi + 1) if lo <= hi else range(lo, hi - 1, -1))]
            else:
                lo, hi = ord(a), ord(b)
                parts = [chr(c) for c in (range(lo, hi + 1) if lo <= hi else range(lo, hi - 1, -1))]
        elif "," in group:
            parts = group.split(",")
        else:
            continue
        head, tail = word[:match.start()], word[match.end():]
        return [e for part in parts for e in expand(head + part + tail)]
    return [word]
