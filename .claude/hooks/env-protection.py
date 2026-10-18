#!/usr/bin/env python3
"""
PreToolUse hook for Claude Code's Bash tool.
Blocks any Bash command that touches a `.env*` file in this repo.

`.env*` files hold runtime secrets (API keys, OAuth client secrets,
DB credentials) that must never enter an LLM context, an agent
transcript, or git history. `permissions.deny` in settings.json
already blocks Read/Edit/Write/MultiEdit on these paths; this hook
covers the Bash gap (`cat .env`, `source .env`, `cp .env x`, etc.).

Returns Claude Code's PreToolUse deny shape:
  {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                          "permissionDecision": "deny",
                          "permissionDecisionReason": "..."}}

No allow rule in any settings file can override a hook deny. If you need a
value, ask the human; if you need `.env.example`, ask them to paste it.
"""
import json
import re
import sys


ENV_FILE_RE = re.compile(
    r"(?:^|[\s=`\"'(/\\])(\.env[A-Za-z0-9._\-]*)"
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

    match = ENV_FILE_RE.search(command)
    if match:
        target = match.group(1)
        deny(
            f"Reading or modifying `{target}` from Claude Code is blocked. "
            f"`.env*` files hold runtime secrets (API keys, tokens, DB "
            f"credentials) that must never reach an LLM context, transcript, "
            f"or git history. If you need a value, ask the human directly "
            f"or load it via the running process — don't `cat`/`source` it. "
            f"No settings allow rule can override this hook; if you need "
            f"`.env.example`, ask the human to paste the lines you need."
        )

    allow()


if __name__ == "__main__":
    main()
