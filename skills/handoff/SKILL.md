---
name: handoff
description: Use when the user says handoff, save context, continue later, resume later, switch sessions, pick this up next time, or wants a durable project handoff that can survive moving between coding agents.
---

# Handoff

Create or refresh a shared handoff document in a neutral cross-tool location.

## Canonical locations

- Project-local shared handoff: `<repo>/.agents/handoff.md`
- Neutral machine-local fallback: `~/.agent-handoff-context.md`
- Optional tool-local fallbacks:
  - `~/.codex/handoff-context.md`
  - `~/.claude/handoff-context.md`

## Read order when resuming

1. `<repo>/.agents/handoff.md`
2. `~/.agent-handoff-context.md`
3. `<repo>/.claude/handoff.md`
4. `~/.codex/handoff-context.md`
5. `~/.claude/handoff-context.md`

## Save workflow

When saving a handoff:

1. Detect the project root with `git rev-parse --show-toplevel` when possible.
2. Gather:
   - short session summary
   - active goals
   - unfinished work
   - key files using repo-relative paths
   - important decisions
   - last user intent
   - optional user notes
3. Write a structured markdown handoff to `<repo>/.agents/handoff.md` when a repo root exists.
4. Refresh `~/.agent-handoff-context.md` as the neutral machine-local fallback.
5. Optionally refresh the tool-local fallback that matches the current environment when known.
6. If the user is resuming rather than saving, read from the first existing path in the read-order list and summarize the relevant context before continuing.

Use this template:

```markdown
# Handoff Context

> Shared between coding agents.

## Session Summary
[2-3 sentences]

## Active Goals
- [goal]

## Unfinished Work
- [ ] [task]

## Key Files
- `relative/path` - [why it matters]

## Important Decisions
- [decision]

## Last Intent
[last user intent]

## User Notes
[notes or "None"]
```

Keep handoffs concise but durable. Do not claim memory-sync behavior unless the current tool actually supports it.
