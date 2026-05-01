---
name: claude-pr-loop
description: Use when the user wants to drive an open PR to merge-ready by iterating on it — phrases like "loop on this PR", "review and fix until clean", "babysit PR #N", "keep reviewing this PR", "run the review loop on this", or any request to repeatedly review-then-fix until a PR is good to merge. The parent session owns the loop, spawning a fresh-context review subagent each round via `pr-review-toolkit:review-pr` and then applying the findings itself. Use this instead of running a single review round when the user expects multiple rounds, or asks you to "get this PR to green" without specifying how.
---

# Claude PR Loop

Drive an open PR to merge-ready by alternating fresh-context reviews with stateful fixes, repeating until the reviewer says it's clean.

## When to use

Use this when one review pass isn't enough — when the user wants the PR worked all the way to merge-ready and is willing to let several iterations run. Use the single-shot `pr-review-toolkit:review-pr` directly if the user only wants one round of feedback.

## Architecture: two tiers

The loop runs across two contexts. Each tier has a distinct role; do not blur them.

- **Parent (this session).** Owns the loop. Detects the forge, spawns a fresh review subagent each round, applies findings, runs local checks, commits, pushes, and waits for CI between rounds. State accumulates here — what was fixed, what was deferred, what previous rounds flagged — which informs cross-round decisions like deadlock detection and judging "the same finding came back, did we actually fix it or not."
- **Review subagent (fresh per round).** Invokes `pr-review-toolkit:review-pr`, posts the synthesized review as a PR comment, returns findings. Each round is a brand-new context.

The reviewer must stay fresh because the toolkit's value comes from a reviewer that hasn't seen prior fix attempts and won't rationalize them. A continued context drifts toward agreement with the work it just observed. The parent's continuous context is what makes the *loop* work — accumulated state is what powers deadlock detection and lets the parent push back on a finding the reviewer keeps re-raising.

> **Why isn't there a long-lived "driver" subagent that owns the loop?**
> Earlier versions of this skill described a three-tier architecture where a driver subagent owned the loop and itself spawned review subagents. That doesn't work: per the [Claude Code subagents docs](https://code.claude.com/docs/en/subagents.md), **subagents cannot spawn other subagents** — `Agent(...)` calls inside a subagent have no effect. The official guidance is to "chain subagents from your main session instead," which is what this skill now does. The cost is that the parent stays focused on the loop until it finishes; if the user explicitly wants the parent freed up, see *Parent occupation* below.

## How to invoke

Inputs:

- `pr` — PR number (required)
- `repo` — `owner/name` (optional; defaults to the current repo's remote)
- `max_iterations` — safety cap (optional; default 5)

Sample call from a parent session: "loop the review on PR 215 of dismantl/acab-ansible, max 4 rounds."

## Parent occupation

Heads-up the user before starting: the parent session will be focused on this loop until it finishes (a small number of rounds, each typically 1-5 minutes plus CI wait). If they want to do other work in parallel, the cleanest options are:

- **Run one round at a time.** Treat each invocation of `pr-review-toolkit:review-pr` + manual fix-apply as a single round; pause between rounds.
- **Foreground reviewer, background fixer (advanced).** The parent can spawn each round's reviewer in `run_in_background: true` mode and continue doing other work; when the completion notification arrives, the parent applies fixes and pushes. Reviewer time is the bulk of each round, so this recovers most of the parallelism.
- **Schedule it.** If the loop is going to run many rounds with long CI waits, ask whether to wrap it in `/schedule` — a remote agent runs the loop without holding the local session.

Don't attempt the old "spawn a long-lived background driver that runs unattended" pattern; it can't fan out to a fresh reviewer per round, so it loses the central property the skill is built on.

## Parent pre-flight

1. **Detect the forge** (see *Repo-shape detection* below) so the reviewer subagent's prompt names it explicitly. Don't make the reviewer re-derive what you already know.
2. **Confirm the PR branch is checked out locally** (or check it out): `git fetch origin && git checkout <pr-branch>`. The parent applies fixes here, so the worktree must be on the PR branch.
3. **Read the repo's `CLAUDE.md`** if present, especially any section on PR review tokens or auth — that's how the reviewer subagent knows how to post comments. For Forgejo/Gitea repos, prefer `claude-forgejo-api` when present on `PATH`; otherwise use `forgejo-api` with `FORGEJO_API_IDENTITY=claude` if available.

## The loop (runs in the parent)

```
iteration = 0
findings_history = []
ci_failure_streak = 0

while iteration < max_iterations:
    iteration += 1

    # 1. Fresh-context review — spawn a subagent
    findings = spawn_fresh_review_subagent(pr, repo, forge)
    findings_history.append(findings)

    # 2. Stop conditions (check before doing any work)
    if findings.verdict == "merge-ready" and findings.critical == 0 and findings.important == 0:
        break
    if deadlock_detected(findings_history):
        # same critical/important finding survived two consecutive rounds despite a fix attempt
        break

    # 3. Apply fixes in the parent's own context
    apply_fixes(findings)

    # 4. Local verification
    run_local_tests_and_lint()

    # 5. Commit + push
    commit_with_message_describing_round(iteration, findings)
    git_push()

    # 6. Wait for CI to go green before the next round
    if not wait_for_ci():
        ci_failure_streak += 1
        if ci_failure_streak >= 2 and same_root_cause(...):
            break
        # otherwise: read the failure, fix, recommit, retry
        continue
    ci_failure_streak = 0

return final_report(pr, findings_history, iteration)
```

## Spawning each round's reviewer

Use the `Agent` tool with:

- `subagent_type: "general-purpose"` — the reviewer needs file reads, web/HTTP for the forge API, and the ability to invoke `pr-review-toolkit:review-pr`.
- `run_in_background: true` if you want the parent free during the review (you'll get a completion notification when findings are ready). Foreground is also fine — reviews are typically short.
- No `isolation: "worktree"` — the reviewer is read-only and posts via the forge API; it doesn't need its own checkout.

### Reviewer prompt template

> Invoke the `pr-review-toolkit:review-pr` skill against PR #`<N>` in `<owner/name>` on `<forge>` (`<forge-base-url>`).
>
> Auth pattern: `<auth pattern>`. For posting the synthesized review as a PR comment:
>
> - GitHub: `gh pr comment <N> --body-file -` (read body from stdin)
> - Forgejo/Gitea: `claude-forgejo-api POST /repos/<owner>/<name>/issues/<N>/comments` if available; otherwise `curl -H "Authorization: token <token>"` against the same endpoint. PRs and issues share the comments endpoint on Forgejo.
>
> After the comment is posted, return as your final message **exactly this structure** (no extra prose):
>
> - **Verdict**: one of `merge-ready`, `needs-work`, `blocked`
> - **Severity counts**: `critical=<X> important=<Y> minor=<Z>`
> - **Critical findings**: list with `<file>:<line>` and one-line description (omit section if empty)
> - **Important findings**: list with `<file>:<line>` and one-line description (omit section if empty)
> - **Minor findings**: list with `<file>:<line>` and one-line description (omit section if empty)
> - **Summary**: the toolkit's overall summary in 1-3 sentences

If the reviewer returns something unparseable, re-spawn once with an explicit reminder to follow that return-format contract. If it fails again, surface the toolkit output verbatim and stop.

## Applying fixes

The toolkit suggests fixes; the parent decides which to apply. Default behavior:

- **Critical and important findings**: apply unless you can articulate why the reviewer is wrong. If you disagree, push back in the next round's commit message rather than silently dropping the fix.
- **Minor findings**: evaluate case by case. Fix if cheap and on-topic; defer otherwise. Track deferred minors across rounds — they go in the final report.
- **Out-of-scope findings** (pre-existing issues unrelated to the diff): note and skip; they belong in a follow-up issue.

Document what was and wasn't applied in the commit message.

## Local checks before each push

Detect what the project uses rather than guessing:

- Ansible-flavored repos (`*.yml`, `roles/`, `playbooks/`): `uv run pytest tests/` and `uv run ansible-lint` on changed files.
- Python: respect `pyproject.toml` / `Makefile` targets (`make test`, `make lint`, `pytest`).
- Node: `npm test` / `pnpm test`, plus the lint target in `package.json`.
- Go: `go test ./...` and `go vet ./...`.
- Otherwise mirror what `Makefile`, `.forgejo/workflows/`, or `.github/workflows/` runs.

A red local test halts the round — fix the test before pushing, don't ship a known-broken commit.

## Commit message format

```
fix(<scope>): address review round <N> findings

Applied:
- <one-line summary of fix 1>
- <one-line summary of fix 2>

Deferred (minor):
- <finding> -- <why deferred>

Disagreed:
- <finding> -- <reasoning>
```

## CI gating

Never start the next review round until CI is green on the latest commit.

- GitHub: `gh pr checks <pr> --watch` (foreground) or `gh pr checks <pr>` polled via the `Monitor` tool with an `until` loop.
- Forgejo: poll `claude-forgejo-api GET /repos/<owner>/<name>/commits/<sha>/status` (or raw `curl` against the same endpoint) until the combined `state` is `success`. The `Monitor` tool's `until <check>` loop is the right shape — you get a notification when the check passes.

If CI fails, read the failure, fix it, recommit, wait for green, then proceed to the next review round. CI-fix commits don't count against `max_iterations`.

## Stop conditions

- **Merge-ready** verdict with zero critical and zero important findings (minor findings allowed).
- **Iteration cap** reached (`max_iterations`).
- **Reviewer-disagreement deadlock**: the same critical or important finding survives two consecutive rounds despite an attempted fix. Surface both interpretations in the final report and let the user adjudicate.
- **Two consecutive CI failures** with the same root cause — treat as an environment problem and stop.
- **PR branch moved** under the parent (someone else pushed): pull, re-run local checks, and start the next round fresh. Don't merge their changes into in-flight work.

## Final report

When the loop stops, surface this to the user:

```
PR <N>: <title>
URL: <PR URL>

Status: <merge-ready | stopped at iteration cap | stopped on deadlock | stopped on CI failures | branch moved>
Rounds run: <N>
Final severity: critical=<X> important=<Y> minor=<Z>

Outstanding minor findings:
- <finding> (<file>): <why not fixed>

Next step: <merge offered | manual review needed | user decision required>
```

If the repo allows direct merge (auth permits it, branch protections satisfied) and the verdict is merge-ready, offer to merge. Otherwise tell the user what's blocking the merge.

## Failure modes

| Failure mode | Symptom | Response |
|---|---|---|
| Reviewer-disagreement deadlock | Same finding flagged in rounds N and N+1 after a fix attempt | Parent stops the loop and reports both interpretations. User adjudicates. |
| Infinite-loop guard | About to start round `max_iterations + 1` | Parent stops and reports progress. Asks user before continuing past the cap. |
| CI never goes green | Status flaps red after each push | Parent stops after 2 consecutive CI failures with the same root cause. Treat as an environment problem, not a code problem. |
| Reviewer returns unparseable output | Final message lacks verdict / severity counts | Re-spawn the reviewer once with an explicit reminder to follow the return-format contract. If it fails again, surface the toolkit output verbatim and stop. |
| PR branch moved under parent | Branch SHA differs from what was last pushed | Pull, re-run local checks, and start the next round fresh. Don't try to merge their changes into in-flight work. |
| User interrupts mid-loop | User sends a new message during a review or a CI wait | Finish the current round's work-in-progress (don't leave a half-applied fix), then surface state and ask. Don't try to spin up "one more round" first. |

## Repo-shape detection

The parent reads `.git/config` (or `git remote get-url origin`) to figure out which forge, then names it explicitly in the reviewer prompt:

- Hostname matches `github.com` -> GitHub. Use `gh` for everything: `gh pr view`, `gh pr checks`, `gh pr merge`, `gh pr comment`.
- Hostname is anything else (Forgejo / Gitea instance) -> use the Forgejo API directly. Prefer `claude-forgejo-api` when present; otherwise use `forgejo-api` with `FORGEJO_API_IDENTITY=claude` if available. Fall back to repo-documented auth (typically a vaulted token + `curl`) only when the helper is unavailable.

The reviewer subagent inherits this detection via the prompt — tell it which forge and where to find the token, don't make it re-derive.
