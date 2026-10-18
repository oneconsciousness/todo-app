#!/usr/bin/env python3
"""Fail when shipped code carries task markers, debugger hooks, focused tests or debug-only logging."""

import re
import subprocess
import sys
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

PathFilter = Callable[[PurePosixPath], bool]

ROOTS = ("backend", "frontend", "e2e", "deploy")
TEXT_SUFFIXES = frozenset(
    {
        ".py",
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".mjs",
        ".css",
        ".html",
        ".yml",
        ".yaml",
        ".toml",
        ".cfg",
        ".ini",
        ".sh",
    }
)
SKIP_PARTS = frozenset(
    {
        "node_modules",
        ".venv",
        "dist",
        "build",
        "coverage",
        "playwright-report",
        "test-results",
    }
)


@dataclass(frozen=True)
class Check:
    """One forbidden pattern and the files it applies to."""

    label: str
    pattern: re.Pattern[str]
    applies: PathFilter


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


is_python = suffix_in(".py")
is_script = suffix_in(".ts", ".tsx", ".js", ".jsx", ".mjs")


def is_test(path: PurePosixPath) -> bool:
    """True for backend tests and frontend `*.test.*` or `*.spec.*` files."""
    return (
        under("backend/tests")(path) or ".test." in path.name or ".spec." in path.name
    )


CHECKS = (
    Check("task marker", re.compile(r"\b(TODO|FIXME|XXX|HACK)\b"), lambda _: True),
    Check("python debugger", re.compile(r"\bbreakpoint\(|\bpdb\b"), is_python),
    Check(
        "print in backend code (use logging)",
        re.compile(r"^\s*print\("),
        all_of(is_python, negate(is_test)),
    ),
    Check("javascript debugger", re.compile(r"\bdebugger\b"), is_script),
    Check(
        "debug-only console call (use console.info, warn or error)",
        re.compile(r"\bconsole\.(log|debug|trace)\("),
        is_script,
    ),
    Check(
        "focused test",
        re.compile(r"\b(it|test|describe)\.only\("),
        all_of(is_script, is_test),
    ),
)


def repo_root() -> Path:
    """Return the top of the git work tree."""
    out = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return Path(out.strip())


def candidate_files(root: Path) -> list[PurePosixPath]:
    """List tracked and untracked, non-ignored text files under the code roots."""
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "--", *ROOTS],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    paths = (PurePosixPath(line) for line in out.splitlines())
    return sorted(
        {
            p
            for p in paths
            if p.suffix in TEXT_SUFFIXES and SKIP_PARTS.isdisjoint(p.parts)
        }
    )


def scan(root: Path, path: PurePosixPath, checks: Iterable[Check]) -> Iterator[Hit]:
    """Yield every line in one file that fails a check that applies to it."""
    applicable = tuple(c for c in checks if c.applies(path))
    if not applicable:
        return
    try:
        lines = (root / path).read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return
    yield from (
        Hit(c.label, path, n, line.strip())
        for n, line in enumerate(lines, start=1)
        for c in applicable
        if c.pattern.search(line)
    )


def main() -> int:
    """Scan the repo and print each hit; return 1 when there is any."""
    root = repo_root()
    hits = [hit for path in candidate_files(root) for hit in scan(root, path, CHECKS)]
    for hit in hits:
        print(f"{hit.path}:{hit.line_no}: {hit.label}: {hit.line}")
    print(
        f"hygiene check {'failed' if hits else 'passed'}: {len(hits)} finding(s)",
        file=sys.stderr if hits else sys.stdout,
    )
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
