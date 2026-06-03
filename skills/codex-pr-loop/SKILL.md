---
name: codex-pr-loop
description: Use when the user wants Codex to drive an open PR to merge-ready by iterating on it; triggers on requests like "loop on this PR", "review and fix until clean", "babysit PR #N", "keep reviewing this PR", "run the review loop on this", or "get this PR to green".
---

# Codex PR Loop

Drive an open PR to merge-ready by alternating fresh-context reviews with stateful fixes, using one authoritative full verification gate per round, and repeating until the reviewer says it is clean.

## When to Use

Use this when one review pass is not enough: the user wants the PR worked all the way to merge-ready and is willing to let several iterations run. Invoke the `multi-axis-review` skill directly without this loop if the user only wants one round of feedback.

## Delegation Contract

Invoking this skill by name, including `$codex-pr-loop <PR>`, is an explicit user request for the parent session to spawn fresh review sub-agents during the PR loop. Treat that invocation as satisfying active tool policies that require the user to explicitly ask for sub-agents, delegation, or parallel agent work.

The fresh-context review is the point of this skill. Do not downgrade to foreground review merely because the user's message did not also include words like "delegated", "subagent", or "background".

This skill cannot override a higher-priority policy that directly forbids `spawn_agent`, a runtime where `spawn_agent` is unavailable, or an explicit user request for foreground/no-subagent execution. In those cases, say fresh-context review is unavailable and ask whether to continue in foreground mode.

## Architecture

The loop runs across two contexts. Each tier has a distinct role; do not add a third tier.

- **Parent session:** Owns the loop. It detects the forge, checks out the PR branch, spawns a fresh reviewer each round, applies accepted findings, chooses the verification mode, commits, pushes, waits for the selected full gate, detects deadlocks, and writes the final report. State accumulates here: what was fixed, what was deferred, what previous rounds flagged, and whether a repeated finding is a real deadlock.
- **Fresh review sub-agent:** Invokes the `multi-axis-review` skill against the latest PR diff and repo instructions, then returns findings in the skill's structured output format. Each round is a brand-new context. It must not edit files, commit, push, merge, or run the loop.

The reviewer must stay fresh because the review's value comes from a reviewer that has not seen prior fix attempts and will not rationalize them. The parent's continuous context is what makes the loop work: accumulated state powers deadlock detection and lets the parent push back on a finding the reviewer keeps re-raising.

Do not spawn a long-lived driver agent to own the loop. In Codex, spawned agents cannot be assumed to have `spawn_agent` available, so a driver agent cannot reliably create fresh reviewer agents. The parent must chain reviewer agents from the main session to preserve fresh context.

## Operating Modes

Codex has two valid modes. Choose based on the user's wording and the active tool policy.

- **Fresh-review loop (default):** The parent session owns the loop and spawns a fresh review sub-agent for each review round.
- **Foreground review (fallback):** The parent session reviews the PR itself. Use this only when fresh review sub-agents are unavailable, directly blocked by the active tool policy even after the Delegation Contract above, or explicitly declined by the user.

When fresh review sub-agents are not permitted, do not pretend the reviewer context is fresh. Say fresh-context review is unavailable and ask whether to continue in foreground mode.

## Parent Occupation

By default, each review sub-agent runs in the background after `spawn_agent` returns, so the parent stays interactive during the slowest part of each round. The parent only blocks while applying fixes, running local checks, pushing, and waiting when the next step depends on CI.

If the user wants the loop fully backgrounded, explain that the parent session must remain the orchestrator so it can spawn a fresh reviewer each round. Acceptable alternatives are:

- **Run one round at a time.** Invoke `multi-axis-review`, apply fixes, and pause between rounds. This loses the babysit-until-merge-ready property.
- **Schedule only when fresh reviewers are available.** A scheduled or heartbeat continuation can help with long CI waits, but it must still run the same parent-orchestrated loop and spawn a fresh reviewer per round.

Do not spawn a long-lived background driver that runs unattended. It cannot fan out to a fresh reviewer per round, so it loses the central property the skill is built on.

## Inputs

- `pr` - PR number or URL.
- `repo` - `owner/name`, optional if the current repo remote identifies it.
- `max_iterations` - safety cap, default 5.

## Parent Pre-Flight

Before starting the first review round:

1. Confirm the worktree state with `git status --short`; do not overwrite unrelated user changes.
2. Detect the repo remote with `git remote get-url origin`.
3. Detect the forge so the reviewer prompt names it explicitly:
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

Each round produces a structured result. The exact format is the `multi-axis-review` skill's Output Contract — see that skill for the full specification. In short:

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

Empty severity sections are omitted (don't emit "Critical findings: none" — leave the section out and let the count speak).

## Spawning Each Round's Reviewer

In the default mode, the parent spawns a fresh review agent per round with a self-contained prompt. Use `spawn_agent` with:

- `agent_type` omitted or `default`; the reviewer needs file reads, forge/HTTP access, and the ability to invoke the `multi-axis-review` skill.
- `fork_context: false` so the reviewer does not inherit the parent's accumulated rationale.
- No isolated write workspace; the reviewer is read-only and must not edit files.

Give the reviewer the repo path, PR number, branch, base/head refs, forge/API hints, relevant safety rules, and a reminder that the final message must follow the `multi-axis-review` skill's Output Contract. Do not include previous round findings unless the explicit purpose is deadlock adjudication.

### Reviewer Prompt Template

> Invoke the `multi-axis-review` skill against PR #`<N>` in `<owner/name>` on `<forge>` (`<forge-base-url>`).
>
> This is a `codex-pr-loop` review round. Do not spawn nested agents or use `multi-axis-review`'s optional fan-out; this loop must stay at two contexts.
>
> Pull the diff with `gh pr diff <N>` for GitHub, or the Forgejo/Gitea `pulls/<N>.diff` endpoint, plus PR metadata from `gh pr view <N>` or `pulls/<N>`. Read the repo's `AGENTS.md` / `CLAUDE.md` / `CONTRIBUTING.md` / `README.md` if present so findings respect project conventions.
>
> Run the review across all applicable axes: Correctness, Readability, Architecture, Security, Performance, Tests, Comments, Error handling, Type design where relevant, Maintainability, and Change-level concerns.
>
> Auth pattern: `<auth pattern>`. After producing the review, post it as a PR comment when auth is available:
>
> - GitHub: `gh pr comment <N> --body-file -` (read body from stdin)
> - Forgejo/Gitea: `codex-forgejo-api POST /repos/<owner>/<name>/issues/<N>/comments --data @-` if available; otherwise use `forgejo-api` or the repo-documented helper. Pass JSON on stdin, for example:
>
>   ```json
>   {"body":"<markdown review summary>"}
>   ```
>
>   PRs and issues share the comments endpoint on Forgejo/Gitea.
>
> After the comment is posted, return as your final message the **`multi-axis-review` skill's Output Contract** verbatim: `Verdict:` line, `Severity:` line, severity-grouped findings sections (omit empty sections), and a 1-3 sentence `Summary:`. No extra prose, no preamble.

If the reviewer returns something unparseable, re-spawn once with an explicit reminder to follow the `multi-axis-review` skill's Output Contract. If it fails again, surface the reviewer's output verbatim and stop.

The reviewer must inspect the latest PR diff and repo instructions, then return findings only. The parent applies fixes and confirms that the synthesized review summary was posted to the PR exactly once.

If fresh review agents are unavailable, stop and report that fresh-context review is unavailable instead of silently reviewing from accumulated loop context.

In foreground fallback mode, perform the review yourself by invoking the `multi-axis-review` skill against the latest PR diff, then post the synthesized review summary to the PR when auth is available. Same axes, same Output Contract — the only difference is that the parent's context is no longer fresh, so deadlock detection across rounds becomes harder.

Comment ownership must stay singular: in fresh-review mode, the reviewer posts the PR comment and the parent only confirms it happened; in foreground fallback mode, the parent posts the PR comment.

## Loop

```text
iteration = 0
findings_history = []
ci_failure_streak = 0
verification_mode = choose_verification_mode()

while iteration < max_iterations:
  iteration += 1

  spawn a fresh review agent to review latest PR diff
  append findings to findings_history

  if verdict is merge-ready and critical == 0 and important == 0 and no actionable minor findings remain:
    stop
  if the same critical/important finding survived two consecutive rounds despite a fix attempt:
    stop

  apply accepted critical and important fixes
  resolve actionable minor findings; defer only with a concrete reason
  run cheap targeted local checks when they are available and useful
  if verification_mode is local or hybrid:
    run the full local test/lint gate before pushing
  commit with a Conventional Commit message
  push
  if verification_mode is ci or hybrid:
    wait for CI on the latest head SHA
```

Never start the next review round until the selected full verification gate has passed for the latest commit. For `ci` and `hybrid` modes, that means CI is green on the latest pushed commit.

## Applying Fixes

- Apply critical and important findings unless you can clearly explain why the review is wrong.
- Resolve all in-scope minor findings before declaring merge-ready. Minor severity means "not a merge blocker by itself," not "safe to ignore."
- Treat these minor findings as in-scope by default: stale docs, misleading runbooks, future-agent guidance drift, test/contract drift, confusing comments near changed behavior, and small maintainability issues directly related to the PR.
- Defer a minor finding only when it is unrelated to the PR, clearly pre-existing, cosmetic-only, high-risk relative to the PR, requires a broader refactor, or needs a user decision. Document every deferral with the reason.
- Keep fixes scoped to the PR.
- Skip unrelated pre-existing issues and mention them in the final report.
- Do not push, merge, or close a PR without user permission when the repo is not clearly owned/controlled by the user.

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

Choose one authoritative full verification gate before the first fix round, then re-evaluate only if CI is unavailable or clearly untrustworthy.

- `ci` - Default when PR CI exists, covers the same tests/lint as the local suite, and can be polled. Do not run the full local suite before push. Run only cheap targeted checks that catch obvious local mistakes, then push and wait for CI.
- `local` - Use when CI is absent, unavailable, unpollable, or not trusted for the repo. Run the full local test/lint gate before push.
- `hybrid` - Use only when the user asks for a no-red-commits workflow, repo policy requires it, or local and CI gates cover materially different risks. Run the full local gate before push and wait for CI after push.

Do not run a full local suite and an equivalent full CI suite by default. That duplicates the same signal and slows the review loop without improving confidence.

## Local Checks

Detect checks from repo files instead of guessing:

- Go: `go test ./...` and `go vet ./...`
- Python: `make test`, `make lint`, or `pytest`, based on `pyproject.toml` and `Makefile`
- Node: package-manager test and lint scripts
- Ansible: project test targets and `ansible-lint` where configured
- Otherwise mirror `.github/workflows/`, `.forgejo/workflows/`, or `Makefile`

In `local` and `hybrid` modes, failing local checks halt the round; fix them before pushing. In `ci` mode, local checks should stay cheap and targeted. If a targeted local check fails, fix it before pushing.

## CI Gating

- GitHub: `gh pr checks <pr> --watch`.
- Forgejo/Gitea: poll `GET /api/v1/repos/{owner}/{repo}/commits/{sha}/status` until the combined status is `success`, `failure`, or `error`.

If CI fails, read enough logs or status details to identify the root cause, reproduce locally when useful, fix it, commit, push, and wait again. CI-fix commits do not count against `max_iterations`.

### Forgejo/Gitea: Get the Head SHA from the API

Fetch the head SHA from `pulls/<N>.head.sha` fresh, immediately before polling. Do not paste a SHA from `git push` output, do not copy one from a previous round, and never complete a short prefix into a full 40-character SHA.

```sh
head_sha=$(codex-forgejo-api GET /repos/<owner>/<name>/pulls/<N> | jq -r .head.sha)
codex-forgejo-api GET /repos/<owner>/<name>/commits/$head_sha/status
```

Why this matters: Forgejo/Gitea can return a pending-shaped response for a nonexistent SHA, which can make a wait loop hang or false-positive as merge-ready. Always source the SHA from the forge.

## Stop Conditions

Stop when any of these happen:

- Merge-ready verdict with zero critical, zero important, and zero actionable minor findings. Any remaining minor findings must be explicitly deferred under the policy above.
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
Status: merge-ready | stopped at iteration cap | stopped on deadlock | stopped on CI failures | branch moved | blocked | user-interrupted
Rounds run: <N>
Final severity: critical=<N> important=<N> actionable_minor=<N> deferred_minor=<N>
Outstanding deferred minor findings:
- <finding> (<file>): <why not fixed>
Next step: <merge offered | manual review needed | user decision required>
```

If the repo allows direct merge, auth permits it, and branch protections are satisfied, offer to merge. Otherwise tell the user what is blocking the merge.

## Failure Modes

| Failure mode | Symptom | Response |
|---|---|---|
| Reviewer-disagreement deadlock | Same critical/important finding appears in rounds N and N+1 after a fix attempt | Stop and report both interpretations so the user can adjudicate. |
| Infinite-loop guard | About to start round `max_iterations + 1` | Stop and report progress; ask before continuing past the cap. |
| CI never goes green | Status fails after each push | Stop after two consecutive CI failures with the same root cause; treat it as an environment problem. |
| Reviewer returns unparseable output | Final message lacks verdict or severity counts | Re-spawn once with the return-format reminder; if it fails again, surface the raw output and stop. |
| PR branch moved under parent | Branch SHA differs from what the parent last pushed | Pull, re-run local checks, and start the next round fresh when safe; otherwise stop for a user decision. |
| User interrupts mid-loop | User sends a new message during review or CI wait | Finish any half-applied fix, then surface state and ask. |

## Repo-Shape Detection

The parent reads `.git/config` or `git remote get-url origin` to figure out which forge, then names it explicitly in the reviewer prompt:

- Hostname matches `github.com` -> GitHub. Use `gh` for PR metadata, diff, checks, comments, and merge operations.
- Any other hostname -> Forgejo/Gitea. Use the REST API directly. Prefer `codex-forgejo-api` when present; otherwise use `forgejo-api` or the repo-documented auth helper.

The reviewer inherits this detection via the prompt. Tell it which forge and where to find the token; do not make it re-derive what the parent already knows.
