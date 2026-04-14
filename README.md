# agent-skills

Shared agent skills intended to be reusable across tools like Codex and Claude Code.

## Skills

- `handoff`
- `session-historian`

## Codex install shape

Codex can consume these skills by linking `skills/<name>` into `~/.agents/skills/`.

The dotfiles bootstrap handles that automatically by cloning this repo into
`~/.codex/agent-skills` and symlinking the installed skills.
