# Codex Automation Surfaces

Use this to choose the smallest Codex-native surface that fits the user's
workflow. Check current Codex docs before writing exact config syntax.

## Surface Map

| Surface | Use When | Typical Location | Implementation Notes |
|---|---|---|---|
| Prompt/thread context | The behavior is one-off or task-specific | Current conversation | Do not persist unless the user wants it repeated. |
| `AGENTS.md` | Repo conventions, commands, review guidance, local workflow expectations | Repo root or nearest relevant subtree | Prefer repo root for broad guidance and nested overrides for specialized packages. |
| Skill | Repeatable workflow with instructions, references, scripts, or templates | `.agents/skills/<name>/SKILL.md` for repo scope, `$HOME/.agents/skills` for user scope | Good for workflows that Codex should discover and follow. |
| Plugin | Distributable bundle of skills, apps, MCP, hooks, assets, or marketplace metadata | Plugin directory with manifest | Use when packaging multiple related capabilities or sharing beyond one repo. |
| MCP server | External tools, docs, databases, browsers, issue trackers, observability, design tools | Codex config or plugin-provided MCP | Prefer env var references for credentials. Do not write secrets. |
| App connector | Authorized private app/workspace data such as Google Drive, Calendar, Slack, GitHub | Installed connector/app | Requires account authorization; user selection alone is not enough. |
| Hook | Lifecycle action around tool calls or file edits | Codex hook config | Use for automatic formatting, validation, or guardrails. Verify syntax from docs. |
| Rule | Command approval allow/prompt/deny policy | `.codex/rules/` or user rules | Use exact command prefixes and include inline examples when supported. |
| Custom subagent | Specialized parallel review, exploration, or implementation role | `.codex/agents/<name>.toml` or user agents | Keep narrow; required fields are name, description, developer instructions. |
| Custom prompt or slash prompt | Reusable prompt shortcut without a full workflow | Codex prompt location from current docs | Use for short reusable requests, not complex procedures. |
| Automation | Recurring or scheduled Codex work | Codex app automation | Use durable prompts; test manually before scheduling. |
| GitHub Action | CI or noninteractive Codex execution | `.github/workflows/*.yml` | Fit for repository automation when GitHub is the forge. |
| Codex code review | Automated PR review and fix follow-up on GitHub | Codex GitHub integration settings and PR comments | Recommend when the repo relies on GitHub PR review. |

## Selection Heuristics

- Persistent instruction before enforcement: try `AGENTS.md` before hooks/rules
  when human-readable guidance is enough.
- Skill before plugin: create a skill for one workflow; package a plugin when
  distribution or bundled tools matter.
- MCP or connector when Codex needs live external state or private data.
- Custom subagent when parallel specialized judgment would be valuable later;
  actual spawning still follows the active policy and explicit user intent.
- Automation when time is the trigger, not merely complexity.
- GitHub Action when CI/noninteractive execution is the trigger.

## Approval Boundaries

Repo-local files are usually safe after the user selects a recommendation.
Still ask for explicit confirmation before:

- editing global Codex config
- installing or authorizing plugins/connectors
- configuring secrets or tokens
- broadening sandbox, approval, network, auth, deployment, or infrastructure
  behavior
- scheduling unattended work with write access
