# Hooks And Rules

Use this reference for mechanical enforcement around edits, commands, and
approval policy. Prefer `AGENTS.md` or a skill when human-readable guidance is
enough.

## Hooks

| Signal | Recommendation |
|---|---|
| Formatter config exists | Add a post-edit formatting hook after checking current hook syntax. |
| Linter or type checker is fast and reliable | Add a scoped post-edit lint or type-check hook when it will not make normal work noisy. |
| Generated files require regeneration | Add a hook only if regeneration is deterministic and cheap. |
| Tests are expensive | Prefer AGENTS.md or a skill for targeted checks instead of an automatic hook. |
| Hook would mutate broad project state | Avoid it unless the user explicitly wants that automation. |

## Rules

| Signal | Recommendation |
|---|---|
| Dangerous commands recur | Add exact command-prefix rules with positive and negative examples. |
| Sensitive files exist | Add rules or instructions to require confirmation for secrets, generated credentials, lock files, or deployment config. |
| Repo has known forbidden tools | Add a deny rule with a clear recommended alternative. |
| Command is safe but frequently prompts | Add a narrow allow rule instead of broadening permissions globally. |

## Guardrails

- Check current Codex docs before writing hook or rule syntax.
- Keep hooks and rules narrow; broad defaults are policy changes.
- Do not broaden sandbox, approval, network, auth, deployment, or
  infrastructure behavior without explicit confirmation.
- Include dry-run or syntax validation commands when the tool supports them.
