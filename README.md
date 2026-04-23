# agent-skills

Shared agent skills intended to be reusable across tools like Codex and Claude Code.

## Status

- No formal releases yet
- Default branch: `main`
- For automation or dotfiles bootstrap, pin a commit if you need reproducibility
- For interactive use, pulling latest `main` and restarting the agent is the expected update flow

## Skills

- `forgejo-pr`
- `handoff`
- `session-historian`

## Install

### Codex

Codex can consume these skills by linking `skills/<name>` into `~/.agents/skills/`.

Example:

```bash
git clone git@github.com:dismantl/agent-skills.git ~/.codex/agent-skills
mkdir -p ~/.agents/skills
ln -s ~/.codex/agent-skills/skills/forgejo-pr ~/.agents/skills/forgejo-pr
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
ln -s ~/.claude/agent-skills/skills/forgejo-pr ~/.claude/skills/forgejo-pr
ln -s ~/.claude/agent-skills/skills/handoff ~/.claude/skills/handoff
ln -s ~/.claude/agent-skills/skills/session-historian ~/.claude/skills/session-historian
```

## Smoke Testing

This repo includes a small `Makefile` for local checks.

Run against the repo copy directly:

```bash
make smoke-session-historian ROOT="$PWD/skills/session-historian"
```

Run against an installed Codex copy:

```bash
make smoke-session-historian ROOT="$HOME/.agents/skills/session-historian"
```

Run against an installed Claude Code copy:

```bash
make smoke-session-historian ROOT="$HOME/.claude/skills/session-historian"
```

## Design Notes

- Shared project state should live in neutral locations like `.agents/`.
- Tool-local fallbacks are allowed, but should not be the canonical source of truth.
- Skill bodies should avoid assuming a single install root when possible.

## Public Repo Notes

This repo is intended to be safe to publish publicly:

- no credentials or tokens should be committed here
- no machine-specific private state should be committed here
- keep examples generic and avoid embedding local secrets or proprietary data
