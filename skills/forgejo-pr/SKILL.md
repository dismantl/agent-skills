---
name: forgejo-pr
description: Use when working with pull requests on a Forgejo or Gitea repository via the `tea` CLI — creating, listing, viewing, reading or adding comments, approving, rejecting, or merging PRs. Especially use when `tea` commands fail with autodiscovery errors like "login does not exist", "404 not found", or "unknown host", because the git remote uses an SSH-config alias that tea can't resolve to a configured login. Triggers on phrases like "open a PR", "review this PR", "comment on PR #X", "approve the PR", "merge that PR", or any PR-related operation when the remote is a self-hosted Forgejo/Gitea instance rather than github.com / gitlab.com.
---

# Forgejo / Gitea PRs via `tea`

`tea` is the official Gitea/Forgejo CLI — a single Go binary that speaks to the server's API. Prefer it over raw `curl` calls for any PR operation on a Gitea-family remote: it handles auth, pagination, and formatting for you.

This skill covers the PR workflow end to end: create, inspect, read and add comments, approve / reject, merge.

## The autodiscovery gotcha (read this first)

`tea` tries to infer the login and repo from the current git remote's URL. That works when the remote's hostname matches a login configured via `tea login add`. It **breaks** when the remote uses an SSH-config alias, e.g.:

```
origin  git@devops.example:alice/widgets.git   (fetch)
```

Here `tea` sees host `devops.example` but the login was registered under the canonical host (e.g., `git.example.com`), so autodiscovery fails. Symptoms:

- `login name 'alice/widgets' does not exist` (usually caused by passing the repo slug to `-l` while trying to work around the error)
- `404 not found` / `repository does not exist`
- `no credentials for host <alias>`

The fix is always the same: pass `-l <login>` and `-r <owner/repo>` explicitly. Don't rely on tea's autodiscovery when the remote host looks non-canonical.

## Pre-flight: find the login and the repo slug

Before running your first `tea` command against a repo, look these up once and reuse them:

**Login name** — the `NAME` column from:

```bash
tea logins list
```

Pick the one whose `URL` matches the Forgejo/Gitea instance hosting this repo.

**Repo slug** — the `owner/repo` extracted from the git remote:

```bash
git remote get-url origin
```

Examples:

| Remote URL | Slug |
|---|---|
| `git@git.example.com:alice/widgets.git` | `alice/widgets` |
| `git@devops.example:alice/widgets.git` (SSH alias) | `alice/widgets` |
| `https://git.example.com/alice/widgets.git` | `alice/widgets` |

In the commands below, `<login>` and `<owner/repo>` mean the values from these two lookups.

## Create a PR

Push the branch first, then create the PR:

```bash
git push -u origin <feature-branch>

tea pr create \
  -l <login> \
  -r <owner/repo> \
  --head <feature-branch> \
  --base main \
  -t "conventional-commit-style title" \
  -d "$(cat <<'EOF'
## Summary
- one bullet per change

## Test plan
- [x] unit tests
- [ ] manual verification
EOF
)"
```

Notes:

- `--head` defaults to the current branch. Pass it explicitly so shell history stays unambiguous.
- `--base` defaults to the repo's default branch. Pass it explicitly to avoid surprises when the default ever changes.
- Use a heredoc for the description; quoted newlines are flaky across shells.
- `--assignees`, `--labels`, and `--milestone` accept comma-separated strings.
- On success, `tea` prints the PR URL. Surface it to the user.

## Inspect PRs

```bash
# List open PRs
tea pr list -l <login> -r <owner/repo>

# All states (open, closed, merged)
tea pr list -l <login> -r <owner/repo> --state all

# Machine-readable for further processing
tea pr list -l <login> -r <owner/repo> --output json
```

## Read PR comments

Forgejo has two distinct comment streams, and `tea` splits them:

**1. Thread comments** — the general discussion on the PR as a whole. Read them by viewing the PR detail with `--comments`:

```bash
tea pr <pr-number> -l <login> -r <owner/repo> --comments
```

Without `--comments`, you only get the title, state, and description.

**2. Inline review comments** — comments attached to specific lines of the diff. Read them separately:

```bash
tea pr review-comments <pr-number> -l <login> -r <owner/repo>
```

Default columns: `id, path, line, body, reviewer, resolver`. Customize with `--fields`. Use `--output json` if you need to post-process.

When a user says "what are the comments on PR #42", they usually mean both streams. Run both commands and present the results together.

## Add comments

**Thread comment** (general discussion):

```bash
tea comment <pr-number> -l <login> -r <owner/repo> "the comment body" </dev/null
```

The trailing `</dev/null` is load-bearing in non-interactive shells (agent harnesses, scripts, anywhere without a real TTY): `tea comment` opens stdin even when the body is provided as an argument, and hangs forever waiting for input otherwise. Close stdin explicitly.

`tea comment` works for both issues and PRs — they share the same comment API. For multi-line bodies, use a heredoc (still close stdin afterward):

```bash
tea comment <pr-number> -l <login> -r <owner/repo> "$(cat <<'EOF'
Three things blocking merge:
1. tests are red on the branch
2. the migration needs a backfill plan
3. security review flagged the new endpoint
EOF
)" </dev/null
```

**Line-level inline review comment** — not directly scriptable via `tea`. Tea's `pr review` walks the diff interactively. If the user needs inline comments non-interactively, post them via the Gitea REST API:

```
POST /repos/{owner}/{repo}/pulls/{index}/reviews
```

Fall back to that only when `tea` can't do it.

## Approve / request changes

Both are scriptable, both accept an optional (approve) or required (reject) message:

```bash
# Approve — message is optional
tea pr approve <pr-number> -l <login> -r <owner/repo> "lgtm"

# Request changes — reason is required
tea pr reject <pr-number> -l <login> -r <owner/repo> "please address security review findings"
```

These leave a review record on the PR. For a thread comment without a formal review verdict, use `tea comment` above instead.

If the user wants to leave line-by-line review comments (not just an overall approve/reject message), they'll need the interactive reviewer:

```bash
tea pr review <pr-number> -l <login> -r <owner/repo>
```

This is **not** scriptable — it prompts hunk-by-hunk for input. Only invoke it when the user is driving the terminal; don't call it from an agent workflow.

## Check out a PR locally

```bash
tea pr checkout <pr-number> -l <login> -r <owner/repo>
```

Fetches the PR's head branch and switches to it.

## Merge

```bash
tea pr merge <pr-number> -l <login> -r <owner/repo>
```

Respects the repo's configured merge style (merge commit, squash, rebase).

Merging is visible to others and hard to reverse, so confirm with the user before merging on their behalf. The local CLAUDE.md-style guidance — never push, merge, or close on someone else's repo without explicit approval — applies here.

## Close without merging

```bash
tea pr close <pr-number> -l <login> -r <owner/repo>
```

## Troubleshooting

| Error message | What went wrong | Fix |
|---|---|---|
| `login name 'owner/repo' does not exist` | Repo slug was passed to `-l` instead of `-r` | `-l` is the login from `tea logins list`; `-r` is `owner/repo` |
| `404 not found` / `repository does not exist` | Autodiscovery picked the wrong host, or the login lacks access | Pass `-l` and `-r` explicitly; verify `tea logins list` shows a login for the right URL |
| `no credentials for host <alias>` | Remote uses an SSH-config alias that tea doesn't recognise | Pass `-l` and `-r` explicitly — tea will skip autodiscovery |
| `tea: command not found` | Not installed | Install via your package manager or `go install`, then `tea login add` to configure |
| `tea comment` hangs with no output | No TTY and stdin is open — tea waits for interactive input | Add `</dev/null` to close stdin |

## Cheat sheet

| Task | Command |
|---|---|
| Create PR | `tea pr create -l <login> -r <owner/repo> --head <br> --base main -t "..." -d "..."` |
| List open PRs | `tea pr list -l <login> -r <owner/repo>` |
| View PR + thread comments | `tea pr <n> -l <login> -r <owner/repo> --comments` |
| List inline review comments | `tea pr review-comments <n> -l <login> -r <owner/repo>` |
| Add thread comment | `tea comment <n> -l <login> -r <owner/repo> "body" </dev/null` |
| Approve | `tea pr approve <n> -l <login> -r <owner/repo> "optional msg"` |
| Request changes | `tea pr reject <n> -l <login> -r <owner/repo> "reason"` |
| Checkout PR | `tea pr checkout <n> -l <login> -r <owner/repo>` |
| Merge | `tea pr merge <n> -l <login> -r <owner/repo>` |
| Close | `tea pr close <n> -l <login> -r <owner/repo>` |

`<login>` comes from `tea logins list`; `<owner/repo>` comes from the git remote URL.
