#!/usr/bin/env python3
"""Fail when shipped code carries task markers, debugger hooks, focused tests or debug-only logging."""

from __future__ import annotations

import re
import subprocess
import sys
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

PathFilter = Callable[[PurePosixPath], bool]

ROOTS = ("backend", "frontend", "e2e", "deploy", "load")
HASH_COMMENT = ("#",)
SLASH_COMMENT = ("//", "/*")
COMMENT_STARTS: dict[str, tuple[str, ...]] = {
    **dict.fromkeys((".py", ".sh", ".yml", ".yaml", ".toml", ".cfg", ".ini", ".conf"), HASH_COMMENT),
    **dict.fromkeys((".ts", ".tsx", ".js", ".jsx", ".mjs", ".css"), SLASH_COMMENT),
    ".html": ("<!--",),
}
NAMED_FILES: dict[str, tuple[str, ...]] = {"Dockerfile": HASH_COMMENT, "Containerfile": HASH_COMMENT}
SKIP_PARTS = frozenset({"node_modules", ".venv", "dist", "build", "coverage", "playwright-report", "test-results"})
QUOTES = frozenset("'\"`")


@dataclass(frozen=True)
class Check:
    """One forbidden pattern, the files it applies to, and whether it looks only inside comments."""

    label: str
    pattern: re.Pattern[str]
    applies: PathFilter
    comments_only: bool = False


@dataclass(frozen=True)
class Hit:
    """One line that failed a check."""

    label: str
    path: PurePosixPath
    line_no: int
    line: str


def suffix_in(*suffixes: str) -> PathFilter:
    """Build a filter that accepts paths with one of the given suffixes."""
    return lambda path: path.suffix in suffixes


def under(prefix: str) -> PathFilter:
    """Build a filter that accepts paths below the given folder."""
    return lambda path: path.is_relative_to(prefix)


def all_of(*filters: PathFilter) -> PathFilter:
    """Combine filters so a path must pass every one."""
    return lambda path: all(f(path) for f in filters)


def negate(f: PathFilter) -> PathFilter:
    """Invert a filter."""
    return lambda path: not f(path)


def comment_starts(path: PurePosixPath) -> tuple[str, ...]:
    """Return the comment markers for the file's language, or () when it is not a checked file."""
    return NAMED_FILES.get(path.name) or COMMENT_STARTS.get(path.suffix, ())


is_python = suffix_in(".py")
is_script = suffix_in(".ts", ".tsx", ".js", ".jsx", ".mjs")


def is_test(path: PurePosixPath) -> bool:
    """True for backend tests and frontend `*.test.*` or `*.spec.*` files."""
    return under("backend/tests")(path) or ".test." in path.name or ".spec." in path.name


CHECKS = (
    Check("task marker in a comment", re.compile(r"\b(TODO|FIXME|XXX|HACK)\b"), lambda _: True, comments_only=True),
    Check("python debugger", re.compile(r"\bbreakpoint\s*\(|\bpdb\b"), is_python),
    Check("print in backend code (use logging)", re.compile(r"(?<![\w.])print\s*\("), all_of(is_python, negate(is_test))),
    Check("javascript debugger", re.compile(r"\bdebugger\b"), is_script),
    Check("debug-only console call (use console.info, warn or error)", re.compile(r"\bconsole\.(log|debug|trace|table|dir|dirxml|group|groupCollapsed|time|timeLog|count)\s*\("), is_script),
    Check("focused test", re.compile(r"\b(it|test|describe)\.only\s*\("), all_of(is_script, is_test)),
)


def comment_text(line: str, starts: tuple[str, ...]) -> str:
    """Return the part of the line that is a comment, ignoring markers inside string literals."""
    if line.lstrip().startswith("*") and "/*" in starts:
        return line
    quote = ""
    for i, ch in enumerate(line):
        if quote:
            quote = "" if ch == quote and line[i - 1] != "\\" else quote
        elif ch in QUOTES:
            quote = ch
        elif any(line.startswith(s, i) for s in starts):
            return line[i:]
    return ""


def repo_root() -> Path:
    """Return the top of the git work tree."""
    out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True).stdout
    return Path(out.strip())


def candidate_files(root: Path) -> list[PurePosixPath]:
    """List tracked and untracked, non-ignored code files under the code roots."""
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "--", *ROOTS],
        cwd=root, capture_output=True, text=True, check=True,
    ).stdout
    paths = (PurePosixPath(line) for line in out.splitlines())
    return sorted({p for p in paths if comment_starts(p) and SKIP_PARTS.isdisjoint(p.parts)})


def scan(root: Path, path: PurePosixPath, checks: Iterable[Check]) -> Iterator[Hit]:
    """Yield every line in one file that fails a check that applies to it."""
    applicable = tuple(c for c in checks if c.applies(path))
    if not applicable:
        return
    try:
        lines = (root / path).read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return
    starts = comment_starts(path)
    yield from (
        Hit(c.label, path, n, line.strip())
        for n, line in enumerate(lines, start=1)
        for c in applicable
        if c.pattern.search(comment_text(line, starts) if c.comments_only else line)
    )


def main() -> int:
    """Scan the repo and print each hit; return 1 when there is any."""
    root = repo_root()
    hits = [hit for path in candidate_files(root) for hit in scan(root, path, CHECKS)]
    for hit in hits:
        print(f"{hit.path}:{hit.line_no}: {hit.label}: {hit.line}")
    print(f"hygiene check {'failed' if hits else 'passed'}: {len(hits)} finding(s)", file=sys.stderr if hits else sys.stdout)
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
