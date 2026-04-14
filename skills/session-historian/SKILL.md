---
name: session-historian
description: Read and analyze Codex and Claude session history. Use when asking about previous sessions, past debugging attempts, continuity across tools, recent errors, what work happened on a project, or which session touched a file or topic.
---

# Session Historian

Inspect both Codex and Claude session logs through one interface.

## Script locations

- Codex install path: `~/.agents/skills/session-historian/scripts/...`
- Claude Code install path: `~/.claude/skills/session-historian/scripts/...`

Use the path that matches the current tool installation.

## Commands

List recent sessions:

```bash
python3 -B ~/.agents/skills/session-historian/scripts/list_sessions.py --source all --days 7 --limit 10
```

Summarize one session:

```bash
python3 -B ~/.agents/skills/session-historian/scripts/summarize_session.py --session-id <id>
```

Search sessions:

```bash
python3 -B ~/.agents/skills/session-historian/scripts/search_sessions.py --source all --text "handoff" --days 14
```

Find recent error-heavy sessions:

```bash
python3 -B ~/.agents/skills/session-historian/scripts/find_errors.py --source all --days 7
```

Get deep context:

```bash
python3 -B ~/.agents/skills/session-historian/scripts/get_session_context.py --session-id <id>
```

Cross-session analysis:

```bash
python3 -B ~/.agents/skills/session-historian/scripts/cross_session_analysis.py --source all --days 30 --focus tools
```

## Behavior

- Default to `--source all` unless the user asked for only Codex or only Claude.
- Use `--project <substring>` to narrow by working directory or project path when helpful.
- Prefer concise summaries first, then go deeper if the user asks.
- Be explicit about which source a result came from.

The scripts normalize enough metadata for continuity and debugging, but Codex and Claude session formats differ. When an inferred field may be incomplete, say so.
