---
name: forgejo-pr
description: Use when working with pull requests on a Forgejo or Gitea repository: listing, viewing, commenting, checking status, checking out, creating, merging, or closing PRs on a self-hosted Forgejo/Gitea remote.
---

# Forgejo / Gitea PRs

Use the local `forgejo-api` helper for API calls. It handles token lookup through `gopass` and keeps tokens out of command arguments.

Prefer identity-specific wrappers when available:

- Codex: `codex-forgejo-api`
- Claude Code: `claude-forgejo-api`
- Generic fallback: `forgejo-api`

Do not use `tea` for agent workflows unless the user explicitly asks for it.

## Pre-Flight

1. Confirm the remote:

```sh
git remote get-url origin
```

2. Extract `owner/repo` from the remote URL.

Examples:

| Remote URL | Repo slug |
|---|---|
| `git@git.example.com:alice/widgets.git` | `alice/widgets` |
| `ssh://git@git.example.com:2222/alice/widgets.git` | `alice/widgets` |
| `https://git.example.com/alice/widgets.git` | `alice/widgets` |

3. If the repo is not on the helper's default instance, set:

```sh
export FORGEJO_BASE_URL="https://git.example.com"
```

4. Choose the helper explicitly:

```sh
# Codex
api=codex-forgejo-api

# Claude Code
api=claude-forgejo-api

# Unknown or wrapper unavailable
api=forgejo-api
```

Use exactly one of those assignments. Do not infer identity from which wrappers exist, because both may be installed.

## Common Operations

List open PRs:

```sh
$api GET /repos/<owner>/<repo>/pulls
```

View PR metadata:

```sh
$api GET /repos/<owner>/<repo>/pulls/<index>
```

Read thread comments:

```sh
$api GET /repos/<owner>/<repo>/issues/<index>/comments
```

Post a thread comment:

```sh
$api POST /repos/<owner>/<repo>/issues/<index>/comments \
  --data '{"body":"review summary"}'
```

Check combined commit status:

```sh
$api GET /repos/<owner>/<repo>/commits/<sha>/status
```

Create a PR after pushing the branch:

```sh
$api POST /repos/<owner>/<repo>/pulls \
  --data '{"head":"feature-branch","base":"main","title":"feat: add thing","body":"## Summary\n- change\n\n## Test plan\n- [x] tests"}'
```

Check whether a PR is already merged:

```sh
$api GET /repos/<owner>/<repo>/pulls/<index>/merge
```

Merge a PR only after explicit user confirmation:

```sh
$api POST /repos/<owner>/<repo>/pulls/<index>/merge \
  --data '{"Do":"merge"}'
```

Use `"Do":"squash"` or another repo-supported merge mode only when the user or repo guidance specifies it.

Close a PR without merging only after explicit user confirmation:

```sh
$api PATCH /repos/<owner>/<repo>/issues/<index> \
  --data '{"state":"closed"}'
```

## Checkout

To check out a PR locally, read the PR metadata first and use the returned head branch/repo details.

For same-repo branches, this is usually enough:

```sh
git fetch origin
git checkout <head-branch>
```

For forked PRs, add/fetch the head repo remote from PR metadata instead of guessing.

## Comments And Reviews

Forgejo PR thread comments are issue comments, so general PR comments use:

```text
POST /repos/{owner}/{repo}/issues/{index}/comments
```

Inline review comments use the pull-review endpoints and need exact diff positions. Before posting inline comments non-interactively, inspect the instance OpenAPI document (`/swagger.v1.json`) or use thread comments instead.

## Safety Rules

- Never print tokens or paste helper internals into PR comments.
- Never merge, close, approve, reject, or delete branches without explicit user confirmation.
- Prefer thread comments for synthesized agent reviews.
- Keep API responses scoped; pipe through `jq` when large responses would be noisy.
- If an endpoint fails with 404, verify both the repo slug and whether PR numbers share the issue index on that instance.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `gopass is required` | `gopass` is not installed | Install gopass, initialize it with age, then add the agent token. |
| `could not read Forgejo token` | Missing token entry | Add `agents/codex/forgejo-api-token` or `agents/claude/forgejo-api-token`. |
| 401/403 | Token lacks access | Check token scopes and repo permissions. |
| 404 | Wrong instance, owner, repo, or PR index | Re-check remote URL and PR metadata. |
| Empty or truncated lists | Pagination limit | Query narrower, or inspect `/swagger.v1.json` for pagination parameters. |
