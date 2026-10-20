# AI transcripts for todo-app

This branch holds the full record of how the app was built with AI. The code is on [`main`](https://github.com/oneconsciousness/todo-app). This branch has only the transcripts and this guide.

The app was built by an AI agent (Claude Code, with Claude Opus) working with the lead, who set the direction, made the decisions and reviewed every pull request. The lead's words and decisions are also collected in [`docs/kickoff.md`](https://github.com/oneconsciousness/todo-app/blob/main/docs/kickoff.md) on `main`, and the time taken is in the README's "How it was made" section.

## What is here

| Path | What it is |
|---|---|
| `session/fa9c58ff-72fc-4042-9fe7-6e07e6e2c359.jsonl` | The main session, from the first message on Sunday 18 October 2026 to the submission: every message from the lead, every reply and every tool call by the agent, and every result |
| `session/fa9c58ff-72fc-4042-9fe7-6e07e6e2c359/subagents/` | The helper agents the main agent started: reviewers, a docs keeper, and builders for parts of the work |
| `session/fa9c58ff-72fc-4042-9fe7-6e07e6e2c359/tool-results/` | Tool outputs too long to keep inline in the main file |

It is one session. When the conversation grew long, Claude Code summarised the earlier part and carried on in the same file, so nothing was lost; a hook also saved a copy before every summary.

## How to read it

Each file is JSON Lines: one event per line, each with a `timestamp`.

- `"type": "user"` with plain text is the lead typing. `"type": "user"` holding a `tool_result` is the output of a tool the agent ran.
- `"type": "assistant"` is the agent: its replies, and its tool calls (`tool_use`) such as running tests, editing files or opening PRs.

To list the lead's messages with their times:

```bash
python3 -c '
import json, sys
for line in open(sys.argv[1]):
    e = json.loads(line)
    c = e.get("message", {}).get("content")
    if e.get("type") == "user" and isinstance(c, str):
        print(e["timestamp"], c[:120].replace("\n", " "))
' session/fa9c58ff-72fc-4042-9fe7-6e07e6e2c359.jsonl
```

## Before it was published

The files were scanned for secrets: private keys, cloud and GitHub tokens, API keys, JWTs, session cookies and passwords. Nothing real was found: the hits were test strings, the public example values from `.env.example`, and image digests. The secrets used by the app were never read or printed by the agent. The lead chose to publish the transcripts as they are.
