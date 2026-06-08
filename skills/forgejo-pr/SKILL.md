---
name: forgejo-pr
description: "Use when working with pull requests on a Forgejo or Gitea repository: listing, viewing, commenting, checking status, checking out, creating, merging, or closing PRs on a self-hosted Forgejo/Gitea remote."
---

# Forgejo / Gitea PRs

Use the Forgejo MCP tools. Tool names are usually surfaced as
`mcp_forgejo_*`, backed by the local `forgejo-mcp` stdio server. The MCP
launcher resolves the agent's token, so do not paste, print, or manually expand
Forgejo tokens.

If Forgejo MCP tools are not callable in the active session, stop and tell the
user that Forgejo MCP is unavailable. Do not use API helper scripts, direct
REST calls, raw `curl`, or `tea` as a fallback.

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

3. Confirm Forgejo MCP is available. A successful
   `mcp_forgejo_get_my_user_info` call is a good auth sentinel.

4. If MCP tools are not exposed or auth fails, stop and report the missing
   Forgejo MCP capability. Do not continue with API helpers or direct HTTP.

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
Use workflow runs when they are enough; otherwise report that the needed status
signal is unavailable through MCP.

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

## Safety Rules

- Use Forgejo MCP tools for Forgejo/Gitea PR operations.
- Stop when Forgejo MCP tools are unavailable instead of switching transports.
- Never print tokens or paste helper internals into PR comments.
- Never merge, close, approve, reject, or delete branches without explicit user confirmation.
- Prefer thread comments for synthesized agent reviews.
- Keep responses scoped; unwrap `.Result` and summarize large payloads.
- If a tool returns 404, verify both the repo slug and whether PR numbers share the issue index on that instance.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| No `mcp_forgejo_*` tools are exposed | Client session was started before Forgejo MCP was configured, or the MCP server failed to launch | Restart the client and check its MCP server list. Do not use API helpers as a fallback. |
| `gopass is required` | `gopass` is not installed | Install gopass, initialize it with age, then add the agent token. |
| `could not read Forgejo MCP token` | Missing token entry | Add the Forgejo MCP token secret expected by the MCP launcher. |
| 401/403 | Token lacks access | Check token scopes and repo permissions. |
| 404 | Wrong instance, owner, repo, or PR index | Re-check remote URL and PR metadata. |
| 404 with `could not find '<branch>' to be a commit, branch or tag` on PR creation | Stacked-PR base branch was deleted | Retarget the child PR to `main` or the new common ancestor, rebase the head branch onto it, then retry creation. |
| Empty or truncated lists | Pagination limit | Query narrower, pass pagination parameters when the tool exposes them, or inspect the Forgejo OpenAPI document. |
