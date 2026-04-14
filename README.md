# agent-skills

Shared agent skills intended to be reusable across tools like Codex and Claude Code.

## Skills

- `handoff`
- `session-historian`

## Install

### Codex

Codex can consume these skills by linking `skills/<name>` into `~/.agents/skills/`.

Example:

```bash
git clone git@github.com:dismantl/agent-skills.git ~/.codex/agent-skills
mkdir -p ~/.agents/skills
ln -s ~/.codex/agent-skills/skills/handoff ~/.agents/skills/handoff
ln -s ~/.codex/agent-skills/skills/session-historian ~/.agents/skills/session-historian
```

The dotfiles bootstrap handles that automatically.

### Claude Code

Claude Code can consume these skills by copying or linking them into
`~/.claude/skills/`.

Example:

```bash
git clone git@github.com:dismantl/agent-skills.git ~/.claude/agent-skills
mkdir -p ~/.claude/skills
ln -s ~/.claude/agent-skills/skills/handoff ~/.claude/skills/handoff
ln -s ~/.claude/agent-skills/skills/session-historian ~/.claude/skills/session-historian
```

## Design Notes

- Shared project state should live in neutral locations like `.agents/`.
- Tool-local fallbacks are allowed, but should not be the canonical source of truth.
- Skill bodies should avoid assuming a single install root when possible.
