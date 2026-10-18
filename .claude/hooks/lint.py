#!/usr/bin/env python3
"""PostToolUse hook for Edit, Write, MultiEdit and NotebookEdit. Lints the edited file and reports findings on the lines that changed.

Python: `uvx ruff check` isolated with the E, F and ANN rule sets, minus E501. TypeScript: the frontend's own ESLint through `npx --no-install`, run from the nearest folder holding `package.json`.
Report only: it never rewrites the file and never blocks (the edit already happened). Exit 2 sends the findings to Claude.
Findings are limited to lines that differ from HEAD; a new file is checked whole. A missing tool keeps the hook quiet.
Whole-project gates (type checks, the test suites) do not run here; `/verify` runs them.
"""
import json
import os
import re
import subprocess
import sys

Finding = tuple[int, int, str, str]

HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


def ruff(root: str, path: str) -> list[Finding]:
    """Run ruff on one file and return (row, col, code, message) tuples."""
    run = subprocess.run(
        ["uvx", "ruff", "check", "--quiet", "--isolated", "--select", "E,F,ANN", "--ignore", "E501", "--output-format", "json", path],
        cwd=root, capture_output=True, text=True, timeout=75,
    )
    return [(f["location"]["row"], f["location"]["column"], f["code"], f["message"]) for f in json.loads(run.stdout or "[]")]


def package_root(root: str, path: str) -> str:
    """Return the nearest folder above `path` that holds a package.json, or `root`."""
    folder = os.path.dirname(os.path.abspath(path))
    while folder.startswith(os.path.abspath(root)):
        if os.path.isfile(os.path.join(folder, "package.json")):
            return folder
        folder = os.path.dirname(folder)
    return root


def eslint(root: str, path: str) -> list[Finding]:
    """Run the frontend's ESLint on one file and return (row, col, code, message) tuples."""
    run = subprocess.run(
        ["npx", "--no-install", "eslint", "--format", "json", os.path.abspath(path)],
        cwd=package_root(root, path), capture_output=True, text=True, timeout=80,
    )
    out: list[Finding] = []
    for f in json.loads(run.stdout or "[]"):
        for m in f.get("messages", []):
            out.append((m.get("line") or 0, m.get("column") or 0, m.get("ruleId") or "error", m.get("message", "")))
    return out


# --- config ---------------------------------------------------------------
SKIP = (".venv/", "node_modules/", "dist/", "build/", "_temp/", "_ignore/")
LINTERS = {".py": ruff, ".ts": eslint, ".tsx": eslint}
# --------------------------------------------------------------------------


def changed_lines(root: str, rel: str) -> set[int] | None:
    """Line numbers that differ from HEAD, or None when the whole file counts."""
    try:
        if subprocess.run(["git", "-C", root, "ls-files", "--error-unmatch", rel], capture_output=True, timeout=10).returncode != 0:
            return None
        diff = subprocess.run(["git", "-C", root, "diff", "-U0", "HEAD", "--", rel], capture_output=True, text=True, timeout=10).stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    lines: set[int] = set()
    for m in (HUNK_RE.match(line) for line in diff.splitlines()):
        if m:
            start, count = int(m.group(1)), int(m.group(2) or 1)
            lines.update(range(start, start + max(count, 1)))
    return lines


def main() -> None:
    """Read the hook payload, lint the file, report on stderr with exit 2."""
    try:
        payload = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        sys.exit(0)
    tool_input = payload.get("tool_input") or {}
    path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    root = payload.get("cwd") or os.getcwd()
    rel = os.path.relpath(path, root) if os.path.isabs(path) else path
    if any(f"/{s}" in f"/{rel}" for s in SKIP) or not os.path.isfile(path):
        sys.exit(0)
    linter = LINTERS.get(os.path.splitext(rel)[1])
    if linter is None:
        sys.exit(0)
    try:
        findings = linter(root, path)
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError, KeyError, TypeError):
        sys.exit(0)
    keep = changed_lines(root, rel)
    rows = [f for f in findings if keep is None or f[0] in keep]
    if not rows:
        sys.exit(0)
    scope = "whole file (new)" if keep is None else "changed lines only"
    body = "\n".join(f"{rel}:{r}:{c}: {code} {msg}" for r, c, code, msg in rows[:40])
    more = f"\n... {len(rows) - 40} more" if len(rows) > 40 else ""
    print(f"lint findings in {rel}, {scope} (report only, fix what applies):\n{body}{more}", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
