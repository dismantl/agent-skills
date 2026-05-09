---
name: codex-pr-loop
description: Use when the user wants Codex to keep working an open PR until it is merge-ready; triggers on requests like "loop on this PR", "review and fix until clean", "babysit PR #N", "keep reviewing this PR", or "get this PR to green".
---

# Codex PR Loop

Drive an open PR toward merge-ready by repeating: review the latest diff, apply fixes, verify locally, commit, push, wait for CI, and review again.

## Delegation Contract

Invoking this skill by name, including `$codex-pr-loop <PR>`, is an explicit user request for the parent session to spawn fresh review sub-agents during the PR loop. Treat that invocation as satisfying active tool policies that require the user to explicitly ask for sub-agents, delegation, or parallel agent work.

The fresh-context review is the point of this skill. Do not downgrade to foreground review merely because the user's message did not also include words like "delegated", "subagent", or "background".

This skill cannot override a higher-priority policy that directly forbids `spawn_agent`, a runtime where `spawn_agent` is unavailable, or an explicit user request for foreground/no-subagent execution. In those cases, say fresh-context review is unavailable and ask whether to continue in foreground mode.

## Architecture

The loop runs across two contexts. Do not add a third tier.

- **Parent session:** Owns the loop. It checks out the PR branch, spawns a fresh reviewer each round, applies accepted findings, runs verification, commits, pushes, waits for CI, detects deadlocks, and writes the final report.
- **Fresh review sub-agent:** Reviews the latest PR diff and repo instructions, then returns findings only. It must not edit files, commit, push, merge, or run the loop.

Do not spawn a long-lived driver agent to own the loop. In Codex, spawned agents cannot be assumed to have `spawn_agent` available, so a driver agent cannot reliably create fresh reviewer agents. The parent must chain reviewer agents from the main session to preserve fresh context.

## Operating Modes

Codex has two valid modes. Choose based on the user's wording and the active tool policy.

- **Fresh-review loop (default):** The parent session owns the loop and spawns a fresh review sub-agent for each review round.
- **Foreground review (fallback):** The parent session reviews the PR itself. Use this only when fresh review sub-agents are unavailable, directly blocked by the active tool policy even after the Delegation Contract above, or explicitly declined by the user.

When fresh review sub-agents are not permitted, do not pretend the reviewer context is fresh. Say fresh-context review is unavailable and ask whether to continue in foreground mode.

## Inputs

- `pr` - PR number or URL.
- `repo` - `owner/name`, optional if the current repo remote identifies it.
- `max_iterations` - safety cap, default 5.

## Parent Pre-Flight

Before starting the first review round:

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

If the user asks for the loop to be fully backgrounded, explain that the parent session must remain the orchestrator so it can spawn a fresh reviewer each round. A long-lived background driver loses the fresh-review guarantee.

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

Each round produces a structured result. The exact format is the `code-review` skill's Output Contract — see that skill for the full specification. In short:

```text
Verdict: merge-ready | needs-work | blocked
Severity: critical=<N> important=<N> minor=<N>

Critical findings:
- <file>:<line> — <one-line finding>

Important findings:
- <file>:<line> — <one-line finding>

Minor findings:
- <file>:<line> — <one-line finding>

Summary:
<1–3 sentences>
```

Empty severity sections are omitted (don't emit "Critical findings: none" — leave the section out and let the count speak).

In the default mode, the parent spawns a fresh review agent per round with a self-contained prompt that tells it to invoke the `code-review` skill and return its Output Contract verbatim. Use `fork_context: false` so the reviewer does not inherit the parent's accumulated rationale. Give the reviewer the repo path, PR number, branch, base/head refs, forge/API hints, relevant safety rules, and a reminder that the final message must follow the `code-review` skill's Output Contract. Do not include previous round findings unless the explicit purpose is deadlock adjudication.

The reviewer must inspect the latest PR diff and repo instructions, then return findings only. The parent applies fixes and posts the synthesized review summary to the PR.

If fresh review agents are unavailable, stop and report that fresh-context review is unavailable instead of silently reviewing from accumulated loop context.

In foreground fallback mode, perform the review yourself by invoking the `code-review` skill against the latest PR diff. Same axes, same Output Contract — the only difference is that the parent's context is no longer fresh, so deadlock detection across rounds becomes harder.

When auth is available, post the synthesized review summary to the PR each round. On GitHub, use `gh pr comment`. On Forgejo/Gitea, use the issue-comment API above.

## Loop

```text
iteration = 0
while iteration < max_iterations:
  iteration += 1
  spawn a fresh review agent to review latest PR diff
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
