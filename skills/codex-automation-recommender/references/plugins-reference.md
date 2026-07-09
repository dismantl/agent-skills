# Plugin Recommendations

Use this reference when a workflow is larger than a single repo skill or needs
distribution. Skip plugins when one local skill is enough.

## When To Recommend A Plugin

| Signal | Recommendation |
|---|---|
| Multiple related skills should be installed together | Create or recommend a plugin bundle. |
| The workflow should be shared across teams or machines | Package the workflow as a plugin instead of copying skill folders manually. |
| Existing plugin solves most of the workflow | Recommend installing the existing plugin before creating custom local files. |
| A skill should ship with UI metadata or assets | Package it as a plugin when that distribution model matters. |
| Single repo-specific workflow | Create a repo skill instead of a plugin. |

## Useful Plugin Categories

| Need | Plugin Direction |
|---|---|
| Skill development | Use the built-in skill/plugin creation tooling before writing manifests by hand. |
| PR or review workflows | Prefer an existing review/PR plugin when it matches the forge and workflow. |
| Security review | Prefer a security-focused plugin when the user explicitly wants security scanning or triage. |
| Document workflows | Prefer existing document plugins over custom parsing code. |
| Frontend work | Prefer frontend/design plugins when the project needs polished UI implementation help. |

## Implementation Notes

- Verify current plugin manifest syntax from official Codex docs before writing
  plugin files.
- Do not install account-level plugins without explicit confirmation.
- Keep plugin recommendations separate from repo-local skill recommendations:
  plugins are for distribution; skills are for workflow authoring.
