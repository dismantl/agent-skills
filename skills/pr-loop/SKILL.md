---
name: pr-loop
description: Use when an agent is asked to repeatedly review and fix an open PR until it is merge-ready or green, including "loop on this PR", "babysit PR #N", "review and fix until clean", or similar multi-round PR work.
---

# PR Loop

Drive an open PR to merge-ready by alternating fresh-context reviews with
stateful fixes, using one authoritative full verification gate per round, and
repeating until the reviewer says it is clean.

## When to Use

Use this when one review pass is not enough: the user wants the PR worked all
the way to merge-ready and is willing to let several iterations run. Use
`multi-axis-review` directly if the user only wants one round of feedback.

## Core Architecture

The loop has two tiers. Do not add a third tier.

- **Parent session:** Owns state and action. It detects the forge, checks out
  the PR branch, starts one fresh reviewer per round, applies accepted findings,
  chooses verification, commits, pushes, waits for the selected full gate,
  detects deadlocks, and writes the final report.
- **Fresh reviewer:** Invokes `multi-axis-review` against the latest PR diff and
  repo instructions, posts or returns the review as required by the harness, and
  returns structured findings. It must not edit files, commit, push, merge, or
  run the loop.

Fresh review is the point. The reviewer has not seen previous fix attempts and
will not rationalize them. The parent keeps continuous context so it can track
what changed, what was deferred, and whether repeated findings are real
deadlocks.

Do not spawn a long-lived driver agent that owns the loop. Subagents cannot be
assumed to spawn their own fresh reviewers across harnesses. The parent session
must chain each fresh reviewer.

## Inputs

- `pr` - PR number or URL.
- `repo` - `owner/name`, optional if the current remote identifies it.
- `max_iterations` - safety cap, default 5.

## Harness Adapter

Use the common loop everywhere, but map delegation and waiting to the active
harness.

### Codex

- Skill invocation by name, including `$pr-loop <PR>`, is an explicit request
  for fresh review subagents during this PR loop.
- Default mode: parent session calls `spawn_agent` once per review round.
- Use `fork_context: false` so the reviewer does not inherit the parent's
  accumulated rationale.
- Omit `agent_type` or use the default agent. The reviewer needs file reads,
  forge tools, and the ability to invoke `multi-axis-review`.
- If `spawn_agent` is unavailable or forbidden, say fresh-context review is
  unavailable and ask whether to continue in foreground mode.

### Claude Code

- Default mode: parent session calls the `Agent` tool once per review round.
- Use `subagent_type: "general-purpose"` and `run_in_background: true` when
  supported.
- Do not use an isolated write workspace for the reviewer; it is read-only.
- For long CI waits, use the runtime's monitor/schedule mechanism only to resume
  the same parent-owned loop. Do not create a background driver subagent.
- If subagents are unavailable, say fresh-context review is unavailable and ask
  whether to continue in foreground mode.

### Gemini CLI

- Activate this skill with `activate_skill` when the task matches the trigger.
- Default mode: parent session delegates each review round to a fresh Gemini
  subagent tool, usually a custom PR reviewer or `generalist` if that is the
  available capable subagent.
- The reviewer prompt must explicitly say not to call nested subagents.
- If Gemini subagents are disabled, unavailable, or blocked by policy, say
  fresh-context review is unavailable and ask whether to continue in foreground
  mode.
- Harness-specific wrapper skills are not required. Install and invoke
  `pr-loop` in every harness.

## Parent Pre-Flight

Before the first review round:

1. Confirm the worktree state with `git status --short`; do not overwrite
   unrelated user changes.
2. Detect the repo remote with `git remote get-url origin`.
3. Detect the forge so the reviewer prompt names it explicitly:
   - `github.com` -> use `gh`.
   - anything else -> treat as Forgejo/Gitea and require Forgejo MCP tools.
4. Determine the PR branch:
   - GitHub: `gh pr view <pr> --json headRefName,baseRefName,url,title`.
   - Forgejo/Gitea: use the exposed Forgejo MCP PR metadata tool.
5. Check out the PR branch in a safe workspace. If isolation matters, use a git
   worktree based on the fetched PR branch.
6. Read repo instructions such as `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`,
   `CONTRIBUTING.md`, `README.md`, and workflow files before editing.

If the user asks for the loop to be fully backgrounded, explain that the parent
session must remain the orchestrator so it can start a fresh reviewer each
round.

## Forgejo/Gitea MCP Rules

Use Forgejo MCP tools only. Do not use `tea`, API helper scripts, direct REST,
or raw `curl` for this skill.

If Forgejo MCP tools are not exposed in the active session, stop and report that
Forgejo MCP is unavailable. Use the exact callable tool names surfaced by the
client instead of inventing names from prose.

Useful operations:

- PR metadata: `get_pull_request_by_index`
- PR diff: `get_pull_request_diff`
- PR files: `list_pull_request_files`
- PR issue comments: `list_issue_comments`
- Post a PR comment: `create_issue_comment`
- Workflow runs: `list_workflow_runs`

## Review Round

Each round produces the `multi-axis-review` Output Contract:

```text
Verdict: merge-ready | needs-work | blocked
Severity: critical=<N> important=<N> minor=<N>

Critical findings:
- <file>:<line> — <one-line finding>

Important findings:
- <file>:<line> — <one-line finding>

Minor findings:
- <file>:<line> — <disposition>: <one-line finding>

Summary:
<1–3 sentences>
```

Omit empty severity sections. Do not emit "Critical findings: none"; let the
count speak.

## Reviewer Prompt

Give each reviewer a self-contained prompt:

```text
Invoke the `multi-axis-review` skill against PR #<N> in <owner/name> on <forge>
(<forge-base-url>).

This is a `pr-loop` review round. Do not spawn nested agents or use
`multi-axis-review` optional fan-out; this loop must stay at two contexts.

Repository path for local inspection: <absolute-repo-path>
Base ref: <base-ref> at <base-sha>
Head ref: <head-ref> at <head-sha>
Head branch: <head-branch>
PR URL: <pr-url>

Pull the diff with `gh pr diff <N>` for GitHub, or Forgejo/Gitea MCP diff
tooling, plus PR metadata from `gh pr view <N>` or Forgejo/Gitea MCP metadata
tooling. Read repo instructions such as AGENTS.md, CLAUDE.md, GEMINI.md,
CONTRIBUTING.md, README.md, and workflow files if present.

Review across all applicable axes: Correctness, Readability, Architecture,
Security, Performance, Tests, Comments, Error handling, Type design where
relevant, Maintainability, and Change-level concerns.

Auth pattern: <auth pattern>. After producing the review, post it as a PR
comment when the required forge tool is available:

- GitHub: `gh pr comment <N> --body-file -`
- Forgejo/Gitea: use the exposed Forgejo MCP comment tool. If it is not
  callable, return `Verdict: blocked` and report that Forgejo MCP is
  unavailable. PRs and issues share the comments namespace on Forgejo/Gitea.

After the comment is posted, return only the `multi-axis-review` Output Contract.
```

If the reviewer returns unparseable output, retry once with an explicit reminder
to follow the contract. If it fails again, surface the reviewer output verbatim
and stop.

Comment ownership must stay singular. In fresh-review mode, the reviewer posts
the PR comment and the parent confirms it happened. In foreground fallback mode,
the parent posts the PR comment.

## Loop

```text
iteration = 0
findings_history = []
ci_failure_streak = 0
verification_mode = choose_verification_mode()

while iteration < max_iterations:
  iteration += 1

  start a fresh reviewer against the latest PR diff
  append findings to findings_history

  if verdict is merge-ready and critical == 0 and important == 0 and no actionable minor findings remain:
    stop
  if the same critical/important finding survived two consecutive rounds despite a fix attempt:
    stop

  apply accepted critical and important fixes
  resolve actionable minor findings; defer only with a concrete reason
  run cheap targeted local checks when useful
  if verification_mode is local or hybrid:
    run the full local test/lint gate before pushing
  commit with a Conventional Commit message
  push
  if verification_mode is ci or hybrid:
    wait for CI on the latest head SHA
```

Never start the next review round until the selected full verification gate has
passed for the latest commit.

### Target Branch Movement After a Clean Review

If the latest review round found no issues and the target branch moves before
the PR is merged, rebase or merge the PR branch as required, then compare the
post-rebase PR diff to the diff that was already reviewed. Do not run another
review round solely because the target branch moved. Start a fresh review only
when the rebase meaningfully changes files modified by the PR, such as conflict
resolution edits or semantic changes to the PR diff.

## Applying Fixes

- Apply critical and important findings unless you can clearly explain why the
  review is wrong.
- Resolve all in-scope minor findings before declaring merge-ready.
- Treat stale docs, misleading runbooks, future-agent guidance drift,
  test/contract drift, confusing comments near changed behavior, and small
  maintainability issues directly related to the PR as in-scope by default.
- Defer a minor finding only when it is unrelated to the PR, clearly
  pre-existing, cosmetic-only, high-risk relative to the PR, requires a broader
  refactor, or needs a user decision. Document every deferral.
- Keep fixes scoped to the PR.
- Skip unrelated pre-existing issues and mention them in the final report.
- Do not push, merge, or close a PR without user permission when the repo is not
  clearly owned or controlled by the user.

Commit message format:

```text
fix(<scope>): address review round <N> findings

Applied:
- <short fix summary>

Deferred (minor):
- <minor finding> -- <reason>

Disagreed:
- <finding> -- <reasoning>
```

## Verification Strategy

Choose one authoritative full verification gate before the first fix round, then
re-evaluate only if CI is unavailable or clearly untrustworthy.

- `ci` - Default when PR CI exists, covers the same tests/lint as the local
  suite, and can be polled. Run only cheap targeted checks before push, then
  wait for CI.
- `local` - Use when CI is absent, unavailable, unpollable, or not trusted for
  the repo. Run the full local test/lint gate before push.
- `hybrid` - Use only when the user asks for no-red-commits, repo policy
  requires it, or local and CI gates cover materially different risks.

Do not run a full local suite and an equivalent full CI suite by default.

## Local Checks

Detect checks from repo files instead of guessing:

- Go: `go test ./...` and `go vet ./...`
- Python: `make test`, `make lint`, or `pytest`, based on repo files
- Node: package-manager test and lint scripts
- Ansible: project test targets and `ansible-lint` where configured
- Otherwise mirror `.github/workflows/`, `.forgejo/workflows/`, or `Makefile`

In `local` and `hybrid` modes, failing local checks halt the round. In `ci`
mode, local checks should stay cheap and targeted.

## CI Gating

- GitHub: `gh pr checks <pr> --watch`.
- Forgejo/Gitea: use MCP workflow-run tooling for the head SHA when it is
  sufficient. If MCP cannot provide the required gate, choose `local`
  verification or stop as blocked.

If CI fails, read enough logs or status details to identify the root cause,
reproduce locally when useful, fix it, commit, push, and wait again. CI-fix
commits do not count against `max_iterations`.

### Forgejo/Gitea Head SHA

Fetch the head SHA from Forgejo MCP fresh, immediately before polling. Do not
paste a SHA from `git push` output, copy one from a previous round, or complete
a short prefix into a full SHA.

## Stop Conditions

Stop when any of these happen:

- Merge-ready verdict with zero critical, zero important, and zero actionable
  minor findings.
- `max_iterations` is reached.
- The same critical or important finding survives two consecutive rounds after
  an attempted fix.
- CI fails twice for the same root cause.
- The PR branch moves under you in a way that needs a user decision.
- The user interrupts or changes direction.

## Final Report

Return a concise report:

```text
PR <N>: <title>
URL: <url>
Status: merge-ready | stopped at iteration cap | stopped on deadlock | stopped on CI failures | branch moved | blocked | user-interrupted
Rounds run: <N>
Final severity: critical=<N> important=<N> actionable_minor=<N> deferred_minor=<N>
Outstanding deferred minor findings:
- <finding> (<file>): <why not fixed>
Next step: <merge offered | manual review needed | user decision required>
```

If the repo allows direct merge, auth permits it, and branch protections are
satisfied, offer to merge. Otherwise tell the user what is blocking the merge.

## Failure Modes

| Failure mode | Response |
|---|---|
| Same critical/important finding returns after a fix attempt | Stop and report both interpretations so the user can adjudicate. |
| About to start round `max_iterations + 1` | Stop and report progress; ask before continuing past the cap. |
| CI fails twice for the same root cause | Stop and treat it as an environment problem. |
| Reviewer returns unparseable output twice | Surface the raw output and stop. |
| PR branch moved under parent | Pull, re-run local checks, and continue when safe; otherwise stop for a user decision. |
| User interrupts mid-loop | Finish any half-applied fix, then surface state and ask. |

## Repo Detection

The parent reads `.git/config` or `git remote get-url origin`:

- Hostname matches `github.com` -> GitHub. Use `gh` for PR metadata, diff,
  checks, comments, and merge operations.
- Any other hostname -> Forgejo/Gitea. Require exposed Forgejo MCP tools. If
  they are unavailable, stop and report the blocker.

The reviewer inherits this detection via the prompt. Tell it the forge and auth
pattern; do not make it re-derive what the parent already knows.
