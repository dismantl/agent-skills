---
name: codex-automation-recommender
description: Analyze a repository and recommend Codex-native automations, then ask which recommendations to implement. Use when the user asks for Codex automation recommendations, wants to optimize a Codex setup, asks how to set up Codex for a project, wants a Codex equivalent of Claude automation guidance, or wants Codex skills, plugins, MCP servers, hooks, rules, automations, subagents, prompts, or AGENTS.md improvements suggested for a codebase.
---

# Codex Automation Recommender

Analyze a codebase, recommend Codex-native automation improvements, ask the user
which ones they want, and implement only the selected items.

## Contract

- Phase 1 is read-only: inspect the repo and current Codex setup.
- Phase 2 presents a numbered recommendation menu and stops for user selection.
- Phase 3 implements only the selected recommendations.
- A user selection authorizes normal repo-local edits for the selected items.
- Ask again before account-wide installs, connector authorization, secrets,
  live service changes, deploys, broad permission changes, or anything outside
  the current repository.
- If the user asks for recommendations only, do not implement.

## Workflow

### 1. Analyze the Repository

Gather enough context to tailor recommendations:

```bash
git rev-parse --show-toplevel 2>/dev/null
git status --short 2>/dev/null
rg --files -g 'AGENTS.md' -g 'AGENTS.override.md' -g '.codex/**' -g '.agents/**' -g '.github/workflows/**' -g 'package.json' -g 'pyproject.toml' -g 'go.mod' -g 'Cargo.toml' -g 'Gemfile' -g 'requirements*.txt' -g 'compose*.yml' -g 'Dockerfile*' -g '*.{md,yml,yaml,toml,json}' | head -200
```

Look for:

- language, framework, package manager, test runner, linting, formatting
- repo guidance: `AGENTS.md`, nested overrides, README, CONTRIBUTING
- Codex setup: `.codex/`, `.agents/skills/`, existing hooks, rules, prompts,
  agents, MCP config, plugin notes
- CI and forge: GitHub Actions, Forgejo/Gitea, GitHub PR workflow
- external systems: databases, cloud providers, issue trackers, docs, browsers,
  monitoring, design tools
- repeated workflows: release, PR review, test generation, deploy prep,
  migrations, docs, security review

Read only the files needed to understand those signals. Do not inspect secrets
or `.env` files.

### 2. Load References As Needed

- Read `references/codex-surfaces.md` when choosing the Codex surface for each
  recommendation.
- Read `references/recommendation-patterns.md` when matching repo signals to
  concrete recommendations.
- For current Codex syntax before writing config, hooks, rules, custom agents,
  plugin manifests, MCP config, GitHub Actions, or automations, consult current
  official Codex docs or the local Codex manual if available. Do not invent
  syntax from memory.
- For library or framework docs, prefer the current docs tools available in the
  active Codex session, such as Context7 or official project docs.

### 3. Recommend

Return a concise report. Recommend at most 1-2 items per relevant category
unless the user requested one category only. Skip categories that do not fit.

Use stable IDs so the user can choose items easily:

```markdown
## Codex Automation Recommendations

### Codebase Profile
- Type:
- Frameworks:
- Test/quality tools:
- Existing Codex setup:

### Recommended Menu

#### A1. AGENTS.md: [short title]
Why: [repo-specific reason]
Implementation: [repo-local files or manual/account action]
Risk: [low/medium/high, and why]

#### S1. Skill: [short title]
Why:
Implementation:
Risk:

#### M1. MCP or Connector: [short title]
Why:
Implementation:
Risk:

#### H1. Hook or Rule: [short title]
Why:
Implementation:
Risk:

#### U1. Subagent: [short title]
Why:
Implementation:
Risk:

#### T1. Automation: [short title]
Why:
Implementation:
Risk:

### Pick What To Implement
Reply with IDs, for example `A1 S1 H1`, or say `all low-risk`.
```

After the menu, stop and wait. Do not add "I'll start now" language unless the
user already selected items in the same prompt.

### 4. Implement Selected Items

When the user selects items:

1. Map each selected ID to the previous recommendation menu. If the menu is not
   in context, rerun analysis and ask again.
2. Confirm no selected item requires a separate approval from the Contract.
3. Check repo state before editing:

   ```bash
   git status --short
   ```

4. Make narrowly scoped edits following repo instructions.
5. For each selected item, verify the relevant behavior:
   - skill: validate frontmatter and referenced files
   - `AGENTS.md`: inspect final instruction chain and path placement
   - MCP/plugin/connector: verify install/config shape without printing secrets
   - hook/rule: run the official syntax checker or a dry-run command when
     available
   - subagent: validate TOML and required fields
   - automation: test the prompt manually before scheduling when possible
   - GitHub Action: lint YAML or run an available workflow check
6. Report what changed and what still needs user action.

## Implementation Guidance

Prefer the smallest durable surface:

- One-off behavior -> current prompt, not config.
- Repo conventions -> `AGENTS.md` or nested `AGENTS.override.md`.
- Repeatable workflow -> `.agents/skills/<name>/SKILL.md` for repo scope, or
  user skill only when the user wants it globally.
- External tool access -> MCP server, app connector, or plugin.
- Mechanical enforcement -> hook or rule.
- Recurring follow-up -> Codex automation.
- Specialized parallel work -> custom subagent.
- CI/background execution -> Codex GitHub Action or existing CI workflow.

Avoid recommending a plugin when a single skill is enough. Avoid recommending a
hook or rule when a repo instruction is sufficient. Avoid project-local config
that depends on private user secrets unless the config safely references
environment variable names.

## Safety Defaults

- Do not edit global `~/.codex/config.toml`, install plugins/connectors, or add
  account-level MCP servers without explicit confirmation for that action.
- Do not write secrets, tokens, API keys, or `.env` content.
- Do not broaden approval, sandbox, network, auth, deployment, or infrastructure
  behavior without explicit confirmation.
- Do not recommend initially disabled work as "done"; if activation is required,
  make it explicit and either complete it or list it as remaining user action.
- Keep recommendations grounded in observed files and current callable tools.
