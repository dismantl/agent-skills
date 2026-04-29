---
name: codex-pr-loop
description: Use when the user wants Codex to keep working an open PR until it is merge-ready; triggers on requests like "loop on this PR", "review and fix until clean", "babysit PR #N", "keep reviewing this PR", or "get this PR to green".
---

# Codex PR Loop

Drive an open PR toward merge-ready by repeating: review the latest diff, apply fixes, verify locally, commit, push, wait for CI, and review again.

## Operating Modes

Codex has two valid modes. Choose based on the user's wording and the active tool policy.

- **Background delegated mode (default):** Spawn one long-lived driver agent with `spawn_agent`. The driver owns checkout, review rounds, fixes, verification, commits, pushes, CI waiting, and the final report. The driver may spawn fresh review agents when that is permitted by the active Codex tool policy.
- **Foreground mode (fallback):** This session owns the loop. Use this only when background/delegated mode is unavailable, blocked by the active tool policy, or explicitly declined by the user.

When delegated mode is not permitted, do not pretend the reviewer context is fresh. Say the loop is running in foreground mode and continue.

## Inputs

- `pr` - PR number or URL.
- `repo` - `owner/name`, optional if the current repo remote identifies it.
- `max_iterations` - safety cap, default 5.

## Parent Pre-Flight

Before launching the driver or starting the first foreground review round:

1. Confirm the worktree state with `git status --short`; do not overwrite unrelated user changes.
2. Detect the repo remote with `git remote get-url origin`.
3. Detect the forge:
   - `github.com` -> use `gh`.
   - anything else -> treat as Forgejo/Gitea and use the REST API directly.
4. Determine the PR branch:
   - GitHub: `gh pr view <pr> --json headRefName,baseRefName,url,title`.
   - Forgejo: `GET /api/v1/repos/{owner}/{repo}/pulls/{index}`.
5. Check out the PR branch in a safe workspace. If already in the target repo, use a manual git worktree when isolation matters:
   - `git fetch origin`
   - `git worktree add ../<repo-slug>-pr-<N>-loop <head-ref>`
6. Read repo instructions (`AGENTS.md`, `CLAUDE.md`, `README`, workflow files) before editing.

In background mode, the parent should do steps 1-4, then spawn the driver with a self-contained prompt that includes the detected forge, repo, PR number, branch, auth hints, max iteration cap, and this skill's loop rules. The driver performs steps 5-6 inside its workspace.

## Forgejo/Gitea API Rules

Do not use `tea` for this skill. Use the Forgejo/Gitea REST API directly.

Prefer the local `codex-forgejo-api` helper when it is present on `PATH`; otherwise use `forgejo-api`, which defaults to Codex identity. The helper reads the token from `gopass` and wraps `curl` without putting the token in the curl command arguments. Example:

```sh
codex-forgejo-api GET /repos/dismantl/agent-skills/pulls/1
codex-forgejo-api POST /repos/dismantl/agent-skills/issues/1/comments --data '{"body":"review summary"}'
```

Discover the base URL from the git remote or local repo guidance. Prefer an existing token documented by the repo; otherwise ask the user for the auth pattern before posting comments, pushing, merging, or reading private CI details.

Useful endpoints:

- PR metadata: `GET /api/v1/repos/{owner}/{repo}/pulls/{index}`
- PR issue comments: `GET /api/v1/repos/{owner}/{repo}/issues/{index}/comments`
- Post a PR comment: `POST /api/v1/repos/{owner}/{repo}/issues/{index}/comments`
- Commit status: `GET /api/v1/repos/{owner}/{repo}/commits/{sha}/status`
- Commit statuses: `GET /api/v1/repos/{owner}/{repo}/commits/{sha}/statuses`

Use `Authorization: token <token>` unless the local repo documents a different accepted auth scheme.

Post review summaries with JSON:

```json
{"body":"<markdown review summary>"}
```

## Review Round

Each round produces a structured result:

```text
Verdict: merge-ready | needs-work | blocked
Severity: critical=<N> important=<N> minor=<N>
Critical/important findings:
- <file>: <one-line finding>
Summary:
- <short summary>
```

In delegated mode, spawn a fresh review agent per round with a self-contained prompt that asks for the exact result format above. The reviewer should inspect the latest PR diff and repo instructions, then return findings only; the driver applies fixes.

In foreground mode, perform the review yourself with a code-review stance: prioritize defects, regressions, security risks, broken tests, and missing verification. Focus on the PR diff, not unrelated old code.

When auth is available, post the synthesized review summary to the PR each round. On GitHub, use `gh pr comment`. On Forgejo/Gitea, use the issue-comment API above.

## Loop

```text
iteration = 0
while iteration < max_iterations:
  iteration += 1
  review latest PR diff
  if verdict is merge-ready and critical == 0 and important == 0:
    stop
  apply accepted critical and important fixes
  evaluate minor findings; fix cheap/on-topic ones, defer the rest
  run local tests and lint that match the repo
  commit with a Conventional Commit message
  push
  wait for CI on the pushed SHA
```

Never start the next review round until CI is green on the latest pushed commit.

## Applying Fixes

- Apply critical and important findings unless you can clearly explain why the review is wrong.
- Keep fixes scoped to the PR.
- Skip unrelated pre-existing issues and mention them in the final report.
- Do not push, merge, or close a PR without user permission when the repo is not clearly owned/controlled by the user.

Commit message format:

```text
fix(<scope>): address review round <N> findings

- Applied <short fix summary>
- Deferred <minor finding> because <reason>
- Disagreed with <finding> because <reason>
```

## Verification

Detect checks from repo files instead of guessing:

- Go: `go test ./...` and `go vet ./...`
- Python: `make test`, `make lint`, or `pytest`, based on `pyproject.toml` and `Makefile`
- Node: package-manager test and lint scripts
- Ansible: project test targets and `ansible-lint` where configured
- Otherwise mirror `.github/workflows/`, `.forgejo/workflows/`, or `Makefile`

If local checks fail, fix them before pushing.

## CI Gating

- GitHub: `gh pr checks <pr> --watch`.
- Forgejo/Gitea: poll `GET /api/v1/repos/{owner}/{repo}/commits/{sha}/status` until the combined status is `success`, `failure`, or `error`.

If CI fails, read enough logs or status details to identify the root cause, fix it, commit, push, and wait again. CI-fix commits do not count against `max_iterations`.

## Stop Conditions

Stop when any of these happen:

- Merge-ready verdict with zero critical and zero important findings.
- `max_iterations` is reached.
- The same critical or important finding survives two consecutive rounds after an attempted fix.
- CI fails twice for the same root cause.
- The PR branch moves under you in a way that needs a user decision.
- The user interrupts or changes direction.

## Final Report

Return a concise report:

```text
PR <N>: <title>
URL: <url>
Status: merge-ready | stopped at iteration cap | stopped on deadlock | blocked | user-interrupted
Rounds run: <N>
Final severity: critical=<N> important=<N> minor=<N>
Outstanding minor findings:
- <finding> (<file>): <why not fixed>
Next step: <merge offered | manual review needed | user decision required>
```
