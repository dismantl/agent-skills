---
name: session-historian
description: Read and analyze Codex and Claude session history. Use when asking about previous sessions, past debugging attempts, continuity across tools, recent errors, what work happened on a project, or which session touched a file or topic.
---

# Session Historian

Inspect both Codex and Claude session logs through one interface.

## Script root

Detect the install root before running commands:

```bash
if [ -d "$HOME/.agents/skills/session-historian/scripts" ]; then
  SESSION_HISTORIAN_ROOT="$HOME/.agents/skills/session-historian"
elif [ -d "$HOME/.claude/skills/session-historian/scripts" ]; then
  SESSION_HISTORIAN_ROOT="$HOME/.claude/skills/session-historian"
else
  echo "session-historian is not installed" >&2
  exit 1
fi
```

## Commands

List recent sessions:

```bash
python3 -B "$SESSION_HISTORIAN_ROOT/scripts/list_sessions.py" --source all --days 7 --limit 10
```

Summarize one session:

```bash
python3 -B "$SESSION_HISTORIAN_ROOT/scripts/summarize_session.py" --session-id <id>
```

Search sessions:

```bash
python3 -B "$SESSION_HISTORIAN_ROOT/scripts/search_sessions.py" --source all --text "handoff" --days 14
```

Find recent error-heavy sessions:

```bash
python3 -B "$SESSION_HISTORIAN_ROOT/scripts/find_errors.py" --source all --days 7
```

Get deep context:

```bash
python3 -B "$SESSION_HISTORIAN_ROOT/scripts/get_session_context.py" --session-id <id>
```

Cross-session analysis:

```bash
python3 -B "$SESSION_HISTORIAN_ROOT/scripts/cross_session_analysis.py" --source all --days 30 --focus tools
```

## Behavior

- Default to `--source all` unless the user asked for only Codex or only Claude.
- Use `--project <substring>` to narrow by working directory or project path when helpful.
- Prefer concise summaries first, then go deeper if the user asks.
- Be explicit about which source a result came from.

The scripts normalize enough metadata for continuity and debugging, but Codex and Claude session formats differ. When an inferred field may be incomplete, say so.
