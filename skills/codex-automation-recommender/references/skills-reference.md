# Skills And Repo Guidance

Use this reference for repository instructions and Codex skills. Do not
recommend new custom prompts; current Codex docs deprecate them in favor of
skills.

## AGENTS.md

| Signal | Recommendation |
|---|---|
| No `AGENTS.md` | Add a root `AGENTS.md` with setup, test, style, review, and safety instructions. |
| Large monorepo or distinct packages | Add nested `AGENTS.override.md` files for package-specific commands and constraints. |
| Existing README has setup/test commands but no agent guidance | Mirror durable commands into `AGENTS.md` with less prose and clearer verification steps. |
| Team-specific review expectations | Add a Review Guidelines section to `AGENTS.md`. |
| Security-sensitive area | Add narrow local guidance for secrets, auth, permissions, and review expectations. |

## Skills

| Signal | Recommendation |
|---|---|
| Repeated release, migration, PR, docs, or deploy-prep workflow | Create a repo skill in `.agents/skills/<workflow>/SKILL.md`. |
| Workflow needs templates, scripts, or examples | Create a skill with `references/`, `scripts/`, or `assets/` as needed. |
| Workflow is useful across many repos | Recommend a user skill or package it into a plugin when distribution matters. |
| Long prompt copied between tasks | Convert it to a skill; avoid new custom prompts. |
| Tool-specific migration from another agent | Create a native Codex skill that preserves intent but uses Codex surfaces and policies. |

## Skill Shape

- Keep `SKILL.md` focused on the workflow and routing.
- Move long examples and category-specific patterns into `references/`.
- Prefer scripts only when deterministic behavior matters.
- Validate with the local skill validator after edits.
- Use repo-scoped `.agents/skills/` for team/project workflows and
  `$HOME/.agents/skills/` for personal cross-repo workflows.

## Deprecated Custom Prompts

Custom prompts are maintenance-only. If a repo already has personal prompt
material, recommend migrating it into a skill when it should be reused,
implicitly discovered, or shared with a team.
