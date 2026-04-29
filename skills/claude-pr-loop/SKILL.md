---
name: claude-pr-loop
description: Use when the user wants to drive an open PR to merge-ready by iterating on it — phrases like "loop on this PR", "review and fix until clean", "babysit PR #N", "keep reviewing this PR", "run the review loop on this", or any request to repeatedly review-then-fix until a PR is good to merge. Spawns a single long-lived driver subagent that owns the whole loop — applying fixes, committing, pushing, waiting for CI — and itself spawns a fresh-context review subagent each round via `pr-review-toolkit:review-pr`. The parent thread is free for other work while the loop runs. Especially use this instead of running a single review round when the user expects multiple rounds, or asks you to "get this PR to green" without specifying how.
---

# Claude PR Loop

Drive an open PR to merge-ready by alternating fresh-context reviews with stateful fixes, repeating until the reviewer says it's clean — without occupying the parent session.

## When to use

Use this when one review pass isn't enough — when the user wants the PR worked all the way to merge-ready and is willing to let several iterations run. Use the single-shot `pr-review-toolkit:review-pr` directly if the user only wants one round of feedback.

## Architecture: three tiers

The loop runs across three contexts. Each tier has a sharply different role; do not blur them.

- **Parent (this session).** Detects the forge, spawns the driver subagent (typically in the background), and relays the final report to the user. After spawning, the parent is free for other work.
- **Driver subagent (long-lived, stateful).** Owns the loop. Checks out the PR, spawns a fresh review subagent each round, applies the resulting fixes, runs local checks, commits, pushes, and waits for CI. State accumulates here — what was fixed, what was deferred, what the previous round flagged — which is *helpful* for the fixer.
- **Review subagent (fresh per round).** Invokes `pr-review-toolkit:review-pr`, posts the synthesized review as a PR comment, returns findings. Each round is a brand-new context.

The reviewer must stay fresh because the toolkit's value comes from a reviewer that hasn't seen your fix attempts and won't rationalize them. A continued context drifts toward agreement with the work it just observed. The driver, by contrast, *should* be continuous — it benefits from remembering what was tried, what was deferred, and what the previous round flagged.

Subagents can spawn subagents. The driver uses the `Agent` tool internally to launch each review subagent — this is by design, not a workaround.

## How to invoke

Inputs:

- `pr` — PR number (required)
- `repo` — `owner/name` (optional; defaults to the current repo's remote)
- `max_iterations` — safety cap (optional; default 5)

Sample call from a parent session: "loop the review on PR 215 of dismantl/acab-ansible, max 4 rounds."

## Parent pre-flight

Keep this minimal — most setup is the driver's job. The parent only needs to:

1. **Detect the forge** (see *Repo-shape detection* below) so the driver's prompt can name it explicitly. Don't make the driver re-derive what you already know.
2. **Decide foreground vs. background.** If the user said "free me up" or "kick this off and I'll do other things," spawn with `run_in_background: true`. If they want to wait for the result, spawn in the foreground. Default to background — the whole point of this skill is that the loop doesn't block the parent.

## Spawning the driver subagent

Use the `Agent` tool with:

- `subagent_type: "general-purpose"` — the driver needs Bash, Edit, Write, and the Agent tool itself.
- `isolation: "worktree"` — the driver works on an isolated copy of the repo. This replaces the old "create a worktree first" pre-flight; the harness handles creation and cleanup.
- `run_in_background: true` — unless the user wants to wait. Background mode is what frees the main thread.

The driver runs in a worktree of the *PR's* repo, not this skill's repo, so it can't read the operational rules from disk. The prompt must be self-contained. Use the template below verbatim, filling in the bracketed values.

### Driver prompt template

> You are the loop driver for PR #`<N>` in `<owner/name>` on `<forge>` (`<forge-base-url>`). Drive this PR to merge-ready by repeating: spawn a fresh review subagent → apply its findings → run local checks → commit → push → wait for CI → repeat. Stop at `max_iterations=<N>` rounds, on `merge-ready` verdict with zero critical/important findings, on reviewer-disagreement deadlock, or if CI fails twice for the same root cause.
>
> **First steps inside the worktree:**
>
> 1. `git fetch origin && git checkout <pr-branch>` so you can apply fixes locally.
> 2. Read the repo's `CLAUDE.md` if present, especially any section on PR review tokens or auth. Auth hint from the parent: `<auth pattern>`. For Forgejo/Gitea repos, prefer `claude-forgejo-api` when present on `PATH`; otherwise use `forgejo-api` with `FORGEJO_API_IDENTITY=claude` if available.
>
> **Each round, spawn a fresh review subagent** via the `Agent` tool with `subagent_type: "general-purpose"` and a prompt that says: invoke the `pr-review-toolkit:review-pr` skill against PR #`<N>` in `<owner/name>` on `<forge>`, post the synthesized review as a comment using the auth pattern above, then return as the final message:
>
> - the verdict (one of: `merge-ready`, `needs-work`, `blocked`)
> - severity counts (critical / important / minor)
> - the prioritized list of critical and important findings, each with file path and one-line description
> - the toolkit's overall summary
>
> If a review subagent returns something unparseable, re-spawn once with an explicit reminder to follow that return-format contract. If it fails again, surface the toolkit output verbatim and stop.
>
> **Applying fixes.** The toolkit suggests fixes; you decide which to apply. Default behavior:
>
> - Critical and important findings: apply unless you can articulate why the reviewer is wrong. If you disagree, push back in the next round's commit message rather than silently dropping the fix.
> - Minor findings: evaluate case by case. Fix if cheap and on-topic; defer otherwise. List deferred minors in the final report.
> - Out-of-scope findings (pre-existing issues unrelated to the diff): note and skip; they belong in a follow-up issue.
>
> Document what was and wasn't applied in the commit message.
>
> **Local checks before each push.** Detect what the project uses rather than guessing:
>
> - Ansible-flavored repos (`*.yml`, `roles/`, `playbooks/`): `uv run pytest tests/` and `uv run ansible-lint` on changed files.
> - Python: respect `pyproject.toml` / `Makefile` targets (`make test`, `make lint`, `pytest`).
> - Node: `npm test` / `pnpm test`, plus the lint target in `package.json`.
> - Go: `go test ./...` and `go vet ./...`.
> - Otherwise mirror what `Makefile`, `.forgejo/workflows/`, or `.github/workflows/` runs.
>
> A red local test halts the round — fix the test before pushing, don't ship a known-broken commit.
>
> **Commit message format:**
>
> ```
> fix(<scope>): address review round <N> findings
>
> Applied:
> - <one-line summary of fix 1>
> - <one-line summary of fix 2>
>
> Deferred (minor):
> - <finding> — <why deferred>
>
> Disagreed:
> - <finding> — <reasoning>
> ```
>
> **CI gating.** Never start the next review round until CI is green on the latest commit.
>
> - GitHub: `gh pr checks <pr> --watch`.
> - Forgejo: poll `GET <forge-base-url>/api/v1/repos/<owner>/<name>/commits/<sha>/status` until the combined status is `success`; prefer `claude-forgejo-api GET /repos/<owner>/<name>/commits/<sha>/status` when available.
>
> If CI fails, read the failure, fix it, recommit, wait for green, then proceed to the next review round. CI-fix commits don't count against `max_iterations`.
>
> **Stop conditions:**
>
> - Merge-ready verdict with zero critical and zero important findings (minor findings allowed).
> - Hit `max_iterations`.
> - Reviewer-disagreement deadlock: the same critical or important finding survives two consecutive rounds despite an attempted fix. Surface both interpretations in the final report.
> - Two consecutive CI failures with the same root cause — treat as an environment problem and stop.
> - PR branch moved under you (someone else pushed): pull, re-run local checks, and start the next round fresh. Don't merge their changes into your in-flight work.
>
> **Return this final report when the loop stops:**
>
> ```
> PR <N>: <title>
> URL: <merge URL>
>
> Status: <merge-ready | stopped at iteration cap | stopped on deadlock | user-interrupted>
> Rounds run: <N>
> Final severity: critical=<X> important=<Y> minor=<Z>
>
> Outstanding minor findings:
> - <finding> (<file>): <why not fixed>
>
> Next step: <merge offered | manual review needed | user decision required>
> ```

## The loop (runs inside the driver)

```
iteration = 0
while iteration < max_iterations:
    iteration += 1

    # 1. Fresh-context review (spawn a sub-subagent)
    findings = spawn_fresh_review_subagent(pr, repo, forge)

    # 2. Stop conditions (check before doing any work)
    if findings.verdict == "merge-ready" and findings.critical == 0 and findings.important == 0:
        break

    # 3. Apply fixes in the driver's own context
    apply_fixes(findings)

    # 4. Local verification
    run_local_tests_and_lint()

    # 5. Commit + push
    commit_with_message_describing_round(iteration, findings)
    git_push()

    # 6. Wait for CI to go green before the next round
    wait_for_ci()

return final_report(pr, findings, iteration)
```

## Parent: after the driver returns

The driver decides its own stop conditions (merge-ready, iteration cap, deadlock, CI failures, branch moved — see the prompt template). The parent's job after that is twofold:

- **Handle user interrupt during the loop.** If the user interrupts the *parent* session while the driver is running and the runtime supports cancellation of background `Agent` invocations, stop the driver and report what was completed. Otherwise let the current round finish, then surface the in-progress state — don't try to spin up "one more round" first.
- **Relay the driver's final report.** Pass the report through to the user with the merge URL, final verdict, severity counts, and any minor findings the driver intentionally deferred. If the repo allows direct merge (auth permits it, branch protections satisfied), offer to merge; if not, tell the user what's blocking the merge.

## Failure modes

| Failure mode | Symptom | Response |
|---|---|---|
| Reviewer-disagreement deadlock | Same finding flagged in rounds N and N+1 after a fix attempt | Driver stops and returns. Parent presents both interpretations to the user. |
| Infinite-loop guard | About to start round `max_iterations + 1` | Driver stops and returns progress. Parent asks user before continuing. |
| CI never goes green | Status flaps red after each push | Driver stops after 2 consecutive CI failures with the same root cause. Treat as an environment problem, not a code problem. |
| Review subagent returns nothing parseable | Final message lacks verdict / severity counts | Driver re-spawns once with an explicit reminder to follow the return-format contract. If it fails again, surface the toolkit output verbatim and stop. |
| PR branch moved under driver | Someone else pushed mid-loop | Pull, re-run local checks, and start the next round fresh. Don't try to merge their changes into the in-flight work. |
| Parent loses the driver | User asks "where's my loop?" | If the runtime exposes background-task introspection (e.g. `TaskList` / `TaskGet` / `TaskOutput`), use it to locate and read the driver's state. Otherwise wait for the driver to return on its own. |

## Repo-shape detection

The parent reads `.git/config` (or `git remote get-url origin`) to figure out which forge, then names it explicitly in the driver prompt:

- Hostname matches `github.com` -> GitHub. The driver uses `gh` for everything: `gh pr view`, `gh pr checks`, `gh pr merge`.
- Hostname is anything else (Forgejo / Gitea instance) -> the driver uses the Forgejo API directly. Prefer `claude-forgejo-api` when present; otherwise use `forgejo-api` with `FORGEJO_API_IDENTITY=claude` if available. Fall back to repo-documented auth only when the helper is unavailable.

The driver inherits this detection via the prompt — tell it which forge and where to find the token, don't make it re-derive.
