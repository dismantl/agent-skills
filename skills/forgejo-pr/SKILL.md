---
name: forgejo-pr
description: "Use when working with pull requests on a Forgejo or Gitea repository: listing, viewing, commenting, checking status, checking out, creating, merging, or closing PRs on a self-hosted Forgejo/Gitea remote."
---

# Forgejo / Gitea PRs

Use the Forgejo MCP tools when they are exposed in the session. Tool names are
usually surfaced as `mcp_forgejo_*`, backed by the local `forgejo-mcp` stdio
server. The MCP launcher resolves the agent's token from `gopass`, so do not
paste, print, or manually expand Forgejo tokens.

Use the API wrappers only when Forgejo MCP tools are not callable in the active
session:

- Codex fallback: `codex-forgejo-api`
- Claude Code fallback: `claude-forgejo-api`
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

3. If MCP tools are exposed, use them directly. A successful
   `mcp_forgejo_get_my_user_info` call is a good auth sentinel.

4. If MCP tools are not exposed, choose exactly one API fallback helper:

```sh
# Codex
api=codex-forgejo-api

# Claude Code
api=claude-forgejo-api

# Unknown or wrapper unavailable
api=forgejo-api
```

If the repo is not on the helper's default instance, set:

```sh
export FORGEJO_BASE_URL="https://git.example.com"
```

## MCP Response Shape

The pinned `forgejo-mcp` binary returns structured payloads as JSON text with a
top-level `Result` field:

```json
{"Result": <forgejo payload>}
```

Parse the tool response first, then read `.Result`. In examples below, `pr`,
`comments`, `files`, and similar names refer to the unwrapped payload.

## MCP Operations

List open PRs:

```text
pulls_response = mcp_forgejo_list_repo_pull_requests(owner="<owner>", repo="<repo>", state="open")
pulls = pulls_response.Result
```

View PR metadata:

```text
pr_response = mcp_forgejo_get_pull_request_by_index(owner="<owner>", repo="<repo>", index=N)
pr = pr_response.Result
```

Read PR diff or changed files:

```text
diff_response = mcp_forgejo_get_pull_request_diff(owner="<owner>", repo="<repo>", index=N)
files_response = mcp_forgejo_list_pull_request_files(owner="<owner>", repo="<repo>", index=N)
```

Read or post thread comments:

```text
comments_response = mcp_forgejo_list_issue_comments(owner="<owner>", repo="<repo>", index=N)
mcp_forgejo_create_issue_comment(owner="<owner>", repo="<repo>", index=N, body="review summary")
```

Forgejo PR thread comments are issue comments; PR and issue numbers share the
same index namespace.

Read reviews:

```text
reviews_response = mcp_forgejo_list_pull_reviews(owner="<owner>", repo="<repo>", index=N)
reviews = reviews_response.Result
```

Check workflow runs for a head SHA:

```text
runs_response = mcp_forgejo_list_workflow_runs(owner="<owner>", repo="<repo>", head_sha="<head_sha>")
runs = runs_response.Result
```

The pinned MCP server does not expose Forgejo's combined commit-status endpoint.
Use the API fallback for that endpoint when workflow runs are not enough.

Create a PR after pushing the branch:

```text
mcp_forgejo_create_pull_request(
  owner="<owner>",
  repo="<repo>",
  head="feature-branch",
  base="main",
  title="feat: add thing",
  body="## Summary\n- change\n\n## Test plan\n- [x] tests"
)
```

Update title/body/base branch:

```text
mcp_forgejo_update_pull_request(owner="<owner>", repo="<repo>", index=N, title="new title")
```

Only pass fields you intend to change.

Merge a PR only after explicit user confirmation:

```text
mcp_forgejo_merge_pull_request(owner="<owner>", repo="<repo>", index=N, style="merge")
```

Use a non-default merge mode only when the user or repo guidance specifies it.

Close a PR without merging only after explicit user confirmation:

```text
mcp_forgejo_update_pull_request(owner="<owner>", repo="<repo>", index=N, state="closed")
```

## Checkout

To check out a PR locally, read the PR metadata first and use the returned head
branch/repo details.

For same-repo branches, this is usually enough:

```sh
git fetch origin
git checkout <head-branch>
```

For forked PRs, add/fetch the head repo remote from PR metadata instead of
guessing.

## API Fallback

Use this section only when MCP tools are not available in the active session.
The wrappers handle token lookup through `gopass` and keep tokens out of curl
arguments.

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

Create a PR with a heredoc body:

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

Forgejo expects JSON request bodies. The wrapper rejects `-F` / `--form` /
`--form-string` because multipart form data returns HTTP 422 for these API
calls. Prefer `--data @-` for multi-line or shell-metacharacter-heavy bodies;
do not wrap the heredoc in command substitution.

## Safety Rules

- Prefer MCP tools whenever they are exposed.
- Never print tokens or paste helper internals into PR comments.
- Never merge, close, approve, reject, or delete branches without explicit user confirmation.
- Prefer thread comments for synthesized agent reviews.
- Keep responses scoped; unwrap `.Result` and summarize large payloads.
- If an endpoint or tool returns 404, verify both the repo slug and whether PR numbers share the issue index on that instance.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| No `mcp_forgejo_*` tools are exposed | Client session was started before Forgejo MCP was configured, or the MCP server failed to launch | Restart the client and check its MCP server list. Use the API fallback only for the current session. |
| `gopass is required` | `gopass` is not installed | Install gopass, initialize it with age, then add the agent token. |
| `could not read Forgejo MCP token` or `could not read Forgejo token` | Missing token entry | Add `agents/codex/forgejo-api-token` or `agents/claude/forgejo-api-token`. |
| 401/403 | Token lacks access | Check token scopes and repo permissions. |
| 404 | Wrong instance, owner, repo, or PR index | Re-check remote URL and PR metadata. |
| 404 with `could not find '<branch>' to be a commit, branch or tag` on PR creation | Stacked-PR base branch was deleted | Retarget the child PR to `main` or the new common ancestor, rebase the head branch onto it, then retry creation. |
| Empty or truncated lists | Pagination limit | Query narrower, pass pagination parameters when the tool exposes them, or inspect the Forgejo OpenAPI document. |
| `curl: (22) ... error: 4xx` followed by a JSON `{"message": ...}` | HTTP error from Forgejo API fallback | Read the message to decide whether the payload, path, or token scope is wrong. |
