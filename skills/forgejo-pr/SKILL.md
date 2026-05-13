---
name: forgejo-pr
description: "Use when working with pull requests on a Forgejo or Gitea repository: listing, viewing, commenting, checking status, checking out, creating, merging, or closing PRs on a self-hosted Forgejo/Gitea remote."
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

## Bodies are JSON, never multipart

Forgejo's API expects JSON request bodies. The wrapper rejects `-F` / `--form` / `--form-string` up front (HTTP 422 across the board); pass the body via `--data '<json>'` or `--data @-` with a heredoc (see "Common Operations" below). The wrapper sets `Content-Type: application/json` for you, so you don't need `-H 'Content-Type: ...'` either. Reach for curl's multipart form-data flags on instinct and you'll round-trip through the wrapper's error message before getting back here.

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

For multi-line bodies, pipe a heredoc through `--data @-`:

```sh
$api POST /repos/<owner>/<repo>/pulls --data @- <<'JSON'
{
  "head": "feature-branch",
  "base": "main",
  "title": "feat: add thing",
  "body": "## Summary\n- change one\n- change two\n\n## Test plan\n- [x] tests"
}
JSON
```

The helper reads its curl config from a temp file, so stdin is free for `--data @-`. Keep the heredoc delimiter quoted (`<<'JSON'`) so the shell doesn't expand `$` or backticks inside the JSON.

Prefer `--data @-` even for single-line bodies when the JSON contains shell metacharacters — `(`, `)`, `$`, backticks, or unescaped single quotes inside a `--data '<json>'` invocation will be parsed by bash before the helper ever runs (e.g. a PR body referencing `(PR 1)` triggers `syntax error near unexpected token '('`). The heredoc form sidesteps the parser entirely.

Do **not** wrap the heredoc in command substitution — `--data "$(cat <<'JSON' ... JSON)"` looks similar but is structurally different: the heredoc is captured into a string that bash then parses as a `--data` argument, so any `(`, `$`, or backtick in the body still hits the parser. With `--data @-`, the heredoc is piped to the helper's stdin and bash never sees the body as a shell argument.

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
| 404 with `could not find '<branch>' to be a commit, branch or tag` on PR creation | Stacked-PR base branch was deleted (typically because the parent PR merged and Forgejo auto-deleted its branch) | Retarget the child PR to `main` (or the new common ancestor) and rebase the head branch onto it. Then retry creation. |
| Empty or truncated lists | Pagination limit | Query narrower, or inspect `/swagger.v1.json` for pagination parameters. |
| `curl: (22) ... error: 4xx` followed by a JSON `{"message": ...}` | HTTP error from Forgejo | The helper exits non-zero on 4xx/5xx but prints the response body too. Read the message to decide: validation error (fix payload), 404 (wrong path), 401 (token scope). |
