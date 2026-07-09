# Subagent And Automation Patterns

Use this reference for specialized parallel work, recurring Codex tasks,
noninteractive execution, and PR review automation.

## Custom Subagents

| Signal | Recommendation |
|---|---|
| Large codebase or PR-heavy workflow | Create a focused reviewer subagent for correctness, tests, and regressions. |
| Auth, payments, secrets, or user data | Create a security reviewer subagent with read-only defaults. |
| Frontend-heavy project | Create a UI/accessibility reviewer subagent. |
| Performance-sensitive API or data layer | Create a performance analyzer subagent. |
| Many independent exploration tasks | Use built-in explorer/worker agents or define narrow custom agents. |

Custom subagent recommendations do not automatically authorize spawning.
Runtime policy and explicit user intent still control whether Codex starts
subagents.

## Automations

| Signal | Recommendation |
|---|---|
| Recurring CI, dependency, or PR status checks | Create a Codex automation with a durable prompt. |
| Long-running review/fix loop | Use a thread automation or skill-driven loop that knows when to stop. |
| Regular guidance drift or docs rot | Schedule a read-only automation that reports findings instead of writing. |
| Automation would write files unattended | Recommend worktree-backed runs and conservative permissions. |

## CI And Review Automation

| Signal | Recommendation |
|---|---|
| GitHub repo with PR review needs | Recommend Codex code review when the repo can use the GitHub integration. |
| Existing workflows are missing agent-friendly checks | Add a CI job that runs the repo's canonical lint/test commands. |
| Need noninteractive Codex in CI | Use the Codex GitHub Action or noninteractive Codex only after verifying current docs. |
| Need generated fixes in CI | Prefer reporting findings unless the user explicitly wants automated writes. |

## Guardrails

- Test automation prompts manually before scheduling them.
- Make stop conditions explicit for recurring automations.
- Do not schedule unattended write access without explicit confirmation.
- Use worktrees when background automation may edit a Git repository.
