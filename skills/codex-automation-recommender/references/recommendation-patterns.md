# Codex Recommendation Patterns

Use observed repo signals to choose high-value recommendations. Recommend only
the items that fit the current repository.

## Core Setup

| Signal | Recommendation |
|---|---|
| No `AGENTS.md` | Add a root `AGENTS.md` with setup, test, style, review, and safety instructions. |
| Large monorepo or distinct packages | Add nested `AGENTS.override.md` files for package-specific commands and constraints. |
| Existing README has setup/test commands but no agent guidance | Mirror durable commands into `AGENTS.md` with less prose and clearer verification steps. |
| Team-specific review expectations | Add a Review Guidelines section to `AGENTS.md`. |

## Skills

| Signal | Recommendation |
|---|---|
| Repeated release, migration, PR, docs, or deploy-prep workflow | Create a repo skill in `.agents/skills/<workflow>/SKILL.md`. |
| Workflow needs templates, scripts, or examples | Create a skill with `references/`, `scripts/`, or `assets/` as needed. |
| Workflow is useful across many repos | Recommend a user skill or package it into a plugin. |
| Existing long prompt copied between tasks | Convert it to a skill or custom prompt depending on complexity. |

## MCP Servers and Connectors

| Signal | Recommendation |
|---|---|
| Popular libraries or SDKs with fast-changing APIs | Add Context7 or official docs MCP for current documentation. |
| Frontend UI or browser workflows | Add Playwright or Chrome DevTools MCP, or use the built-in browser surface when available. |
| GitHub issues, PRs, Actions, or repo triage | Use the GitHub plugin/connector or GitHub MCP. |
| Forgejo/Gitea repo | Use a Forgejo/Gitea MCP server if one is available in the environment. |
| Google Docs, Sheets, Drive, Calendar workflows | Use the Google Drive or Google Calendar connector/plugin. |
| Linear or Slack workflows | Use the Linear or Slack integration when installed and authorized. |
| Sentry or observability workflow | Add Sentry or matching observability MCP. |
| Database-backed project | Add a database-specific MCP only when credentials and data boundaries are clear. |

## Hooks and Rules

| Signal | Recommendation |
|---|---|
| Formatter config exists | Add a post-edit formatting hook after checking current hook syntax. |
| Linter/type checker is fast and reliable | Add a post-edit lint or type-check hook scoped to changed files when practical. |
| Sensitive files exist | Add rules or instructions to block or require confirmation for edits to secrets, generated credentials, or lock files. |
| Dangerous project commands recur | Add exact prefix rules with examples. |
| Tests are expensive | Prefer a skill or AGENTS guidance for targeted tests over automatic hooks. |

## Custom Subagents

| Signal | Recommendation |
|---|---|
| Large codebase or PR-heavy workflow | Create a focused reviewer subagent for correctness, tests, and regressions. |
| Auth, payments, secrets, or user data | Create a security reviewer subagent with read-only defaults. |
| Frontend-heavy project | Create a UI/accessibility reviewer subagent. |
| Performance-sensitive API or data layer | Create a performance analyzer subagent. |
| Many independent exploration tasks | Use built-in explorer/worker agents or define narrow custom agents. |

## Automations

| Signal | Recommendation |
|---|---|
| Recurring CI, dependency, or PR status checks | Create a Codex automation with a durable prompt. |
| Long-running review/fix loop | Use a thread automation or skill-driven loop that knows when to stop. |
| Regular guidance drift or docs rot | Schedule a read-only automation that reports findings instead of writing. |
| Automation would write files unattended | Recommend a worktree-backed run and conservative permissions. |

## CI and Noninteractive Codex

| Signal | Recommendation |
|---|---|
| GitHub repo with CI review needs | Recommend Codex code review or the Codex GitHub Action. |
| Existing workflows are missing agent-friendly checks | Add a CI job that runs the repo's canonical lint/test commands. |
| Need generated fixes in CI | Be cautious: prefer reporting findings unless the user explicitly wants automated writes. |

## Plugins

| Signal | Recommendation |
|---|---|
| Existing plugin solves most of the workflow | Recommend installing the plugin before creating local custom files. |
| Multiple related skills plus app/MCP integration | Create or recommend a plugin. |
| Single repo-specific workflow | Create a repo skill instead of a plugin. |
