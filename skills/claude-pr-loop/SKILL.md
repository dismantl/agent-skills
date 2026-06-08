---
name: claude-pr-loop
description: Use when the user wants to drive an open PR to merge-ready by iterating on it — phrases like "loop on this PR", "review and fix until clean", "babysit PR #N", "keep reviewing this PR", "run the review loop on this", or any request to repeatedly review-then-fix until a PR is good to merge. The parent session owns the loop, spawning a fresh-context review subagent each round that invokes the `multi-axis-review` skill, and then applying the findings itself. Use this instead of running a single review round when the user expects multiple rounds, or asks you to "get this PR to green" without specifying how.
---

# Claude PR Loop

Drive an open PR to merge-ready by alternating fresh-context reviews with stateful fixes, using one authoritative full verification gate per round, and repeating until the reviewer says it's clean.

## When to use

Use this when one review pass isn't enough — when the user wants the PR worked all the way to merge-ready and is willing to let several iterations run. Invoke the `multi-axis-review` skill directly (without this loop) if the user only wants one round of feedback.

## Architecture: two tiers

The loop runs across two contexts. Each tier has a distinct role; do not blur them.

- **Parent (this session).** Owns the loop. Detects the forge, spawns a fresh review subagent each round, applies findings, chooses the verification mode, commits, pushes as needed, and waits for the selected full gate between rounds. State accumulates here — what was fixed, what was deferred, what previous rounds flagged — which informs cross-round decisions like deadlock detection and judging "the same finding came back, did we actually fix it or not."
- **Review subagent (fresh per round).** Invokes the `multi-axis-review` skill against the latest PR diff, posts the synthesized review as a PR comment, returns findings in the skill's structured output format. Each round is a brand-new context.

The reviewer must stay fresh because the review's value comes from a reviewer that hasn't seen prior fix attempts and won't rationalize them. A continued context drifts toward agreement with the work it just observed. The parent's continuous context is what makes the *loop* work — accumulated state is what powers deadlock detection and lets the parent push back on a finding the reviewer keeps re-raising.

> **Why isn't there a long-lived "driver" subagent that owns the loop?**
> Earlier versions of this skill described a three-tier architecture where a driver subagent owned the loop and itself spawned review subagents. That doesn't work: per the [Claude Code subagents docs](https://code.claude.com/docs/en/subagents.md), **subagents cannot spawn other subagents** — `Agent(...)` calls inside a subagent have no effect. The official guidance is to "chain subagents from your main session instead," which is what this skill now does. The cost is that the parent stays focused on the loop until it finishes; if the user explicitly wants the parent freed up, see *Parent occupation* below.

## How to invoke

Inputs:

- `pr` — PR number (required)
- `repo` — `owner/name` (optional; defaults to the current repo's remote)
- `max_iterations` — safety cap (optional; default 5)

Sample call from a parent session: "loop the review on PR 215 of dismantl/agent-skills, max 4 rounds."

## Parent occupation

By default, each round's reviewer runs as a background subagent (see *Spawning each round's reviewer*), so the parent stays interactive during the review phase — typically the slowest part of a round. The parent only blocks during fix application (a few minutes) and CI wait (which can also be backgrounded via `Monitor` with an `until` loop). For most PRs that's enough — the user can multitask between rounds, and the loop progresses automatically.

If even that isn't enough — the user wants the parent fully free for the duration — the options are:

- **Run one round at a time.** Treat each invocation of the `multi-axis-review` skill + manual fix-apply as a single round; pause between rounds. Loses the "babysit until merge-ready" property — needs operator attention at every round boundary.
- **Schedule it.** If the loop is going to run many rounds with long CI waits, ask whether to wrap it in `/schedule` — a routine running on Anthropic-hosted infrastructure drives the loop without holding the local session at all (laptop can be closed).

Don't attempt the old "spawn a long-lived background driver subagent that runs unattended" pattern; it can't fan out to a fresh reviewer per round, so it loses the central property the skill is built on.

## Parent pre-flight

1. **Detect the forge** (see *Repo-shape detection* below) so the reviewer subagent's prompt names it explicitly. Don't make the reviewer re-derive what you already know.
2. **Confirm the PR branch is checked out locally** (or check it out): `git fetch origin && git checkout <pr-branch>`. The parent applies fixes here, so the worktree must be on the PR branch.
3. **Read the repo's `CLAUDE.md`** if present, especially any section on PR review tools or auth — that's how the reviewer subagent knows how to post comments. For Forgejo/Gitea repos, require exposed Forgejo MCP tools. If they are not callable, stop and report that Forgejo MCP is unavailable.

## The loop (runs in the parent)

```
iteration = 0
findings_history = []
ci_failure_streak = 0
verification_mode = choose_verification_mode()

while iteration < max_iterations:
    iteration += 1

    # 1. Fresh-context review — spawn a subagent
    findings = spawn_fresh_review_subagent(pr, repo, forge)
    findings_history.append(findings)

    # 2. Stop conditions (check before doing any work)
    if findings.verdict == "merge-ready" and findings.critical == 0 and findings.important == 0 and no_actionable_minors(findings):
        break
    if deadlock_detected(findings_history):
        # same critical/important finding survived two consecutive rounds despite a fix attempt
        break

    # 3. Apply fixes in the parent's own context
    apply_fixes(findings)

    # 4. Verification
    run_cheap_targeted_local_checks_when_useful()
    if verification_mode in ("local", "hybrid"):
        run_full_local_tests_and_lint()

    # 5. Commit + push
    commit_with_message_describing_round(iteration, findings)
    git_push()

    # 6. Wait for the authoritative gate before the next round
    if verification_mode in ("ci", "hybrid") and not wait_for_ci():
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

- `subagent_type: "general-purpose"` — the reviewer needs file reads, forge MCP access, and the ability to invoke the `multi-axis-review` skill.
- `run_in_background: true` — **default**. Reviews typically take minutes, so backgrounding them keeps the parent interactive during the slow part of the round. The parent gets a completion notification automatically when findings are ready. Drop to foreground only if the user has explicitly said they want the parent fully blocked during the loop, or if the runtime doesn't support background subagents.
- No `isolation: "worktree"` — the reviewer is read-only and posts via forge tooling; it doesn't need its own checkout.

### Reviewer prompt template

> Invoke the `multi-axis-review` skill against PR #`<N>` in `<owner/name>` on `<forge>` (`<forge-base-url>`).
>
> Pull the diff with `gh pr diff <N>` (GitHub) or Forgejo MCP diff tooling, plus PR metadata (`gh pr view <N>` / Forgejo MCP PR metadata tooling). Read the repo's `CLAUDE.md` / `AGENTS.md` / `CONTRIBUTING.md` / `README.md` if present so findings respect project conventions.
>
> Run the review across all applicable axes (Correctness, Readability, Architecture, Security, Performance, Tests, Comments, Error handling, Type design where relevant, Change-level concerns).
>
> Auth pattern: `<auth pattern>`. After producing the review, post it as a PR comment:
>
> - GitHub: `gh pr comment <N> --body-file -` (read body from stdin)
> - Forgejo/Gitea: use `mcp_forgejo_create_issue_comment(owner="<owner>", repo="<name>", index=<N>, body="<review>")`. If the tool is not callable, return `Verdict: blocked` and report that Forgejo MCP is unavailable. PRs and issues share the comments namespace on Forgejo.
>
> After the comment is posted, return as your final message the **`multi-axis-review` skill's Output Contract** verbatim — `Verdict:` line, `Severity:` line, severity-grouped findings sections (omit empty sections), and a 1–3 sentence `Summary:`. No extra prose, no preamble.

If the reviewer returns something unparseable, re-spawn once with an explicit reminder to follow the `multi-axis-review` skill's Output Contract. If it fails again, surface the reviewer's output verbatim and stop.

## Applying fixes

The toolkit suggests fixes; the parent decides which to apply. Default behavior:

- **Critical and important findings**: apply unless you can articulate why the reviewer is wrong. If you disagree, push back in the next round's commit message rather than silently dropping the fix.
- **Minor findings**: resolve all in-scope minor findings before declaring merge-ready. Minor severity means "not a merge blocker by itself," not "safe to ignore." Treat stale docs, misleading runbooks, future-agent guidance drift, test/contract drift, confusing comments near changed behavior, and small maintainability issues directly related to the PR as in-scope by default.
- **Minor deferrals**: defer a minor only when it is unrelated to the PR, clearly pre-existing, cosmetic-only, high-risk relative to the PR, requires a broader refactor, or needs a user decision. The reviewer's disposition tag (`nit:` / `consider:` / `defer:` / `fyi:`) is input, not an automatic decision. Document every deferral with the reason.
- **Out-of-scope findings** (pre-existing issues unrelated to the diff): note and skip; they belong in a follow-up issue.

Document what was and wasn't applied in the commit message.

## Verification strategy

Choose one authoritative full verification gate before the first fix round, then re-evaluate only if CI is unavailable or clearly untrustworthy.

- **`ci`** - Default when PR CI exists, covers the same tests/lint as the local suite, and can be polled. Do not run the full local suite before push. Run only cheap targeted checks that catch obvious local mistakes, then push and wait for CI.
- **`local`** - Use when CI is absent, unavailable, unpollable, or not trusted for the repo. Run the full local test/lint gate before push.
- **`hybrid`** - Use only when the user asks for a no-red-commits workflow, repo policy requires it, or local and CI gates cover materially different risks. Run the full local gate before push and wait for CI after push.

Do not run a full local suite and an equivalent full CI suite by default. That duplicates the same signal and slows the review loop without improving confidence.

## Local checks

Detect what the project uses rather than guessing:

- Ansible-flavored repos (`*.yml`, `roles/`, `playbooks/`): `uv run pytest tests/` and `uv run ansible-lint` on changed files.
- Python: respect `pyproject.toml` / `Makefile` targets (`make test`, `make lint`, `pytest`).
- Node: `npm test` / `pnpm test`, plus the lint target in `package.json`.
- Go: `go test ./...` and `go vet ./...`.
- Otherwise mirror what `Makefile`, `.forgejo/workflows/`, or `.github/workflows/` runs.

In `local` and `hybrid` modes, a red local test halts the round; fix it before pushing. In `ci` mode, local checks should stay cheap and targeted. If a targeted local check fails, fix it before pushing.

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

Never start the next review round until the selected full verification gate has passed for the latest commit. For `ci` and `hybrid` modes, that means CI is green on the latest pushed commit.

- GitHub: `gh pr checks <pr> --watch` (foreground) or `gh pr checks <pr>` polled via the `Monitor` tool with an `until` loop.
- Forgejo: use MCP workflow-run tooling for the head SHA when it is sufficient. If MCP cannot provide the required gate, choose `local` verification or stop as blocked; do not use API helpers or direct REST as a fallback. The `Monitor` tool's `until <check>` loop is the right shape — you get a notification when the check passes. **The `<sha>` here is a footgun — read the next subsection before polling.**

If CI fails, read the failure, reproduce locally when useful, fix it, recommit, wait for green, then proceed to the next review round. CI-fix commits don't count against `max_iterations`.

### Forgejo: get the head SHA from MCP, never type it

Fetch the head SHA from Forgejo MCP **fresh, immediately before polling**. Do not paste a SHA from `git push` output, do not copy one from a previous round, and never autoregressively complete a short prefix into a full 40-char SHA — the LLM does not have the missing 33 chars in context, and any "completion" is a hallucination.

```text
pr_response = mcp_forgejo_get_pull_request_by_index(owner="<owner>", repo="<name>", index=<N>)
head_sha = pr_response.Result.head.sha
runs_response = mcp_forgejo_list_workflow_runs(owner="<owner>", repo="<name>", head_sha=head_sha)
```

Why this matters: a hallucinated SHA can point checks at the wrong revision or an unavailable status shape. Always source the SHA from Forgejo MCP, never from the agent's own text.

## Stop conditions

- **Merge-ready** verdict with zero critical, zero important, and zero actionable minor findings. Any remaining minor findings must be explicitly deferred under the policy above.
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
Final severity: critical=<X> important=<Y> actionable_minor=<Z> deferred_minor=<N>

Outstanding deferred minor findings:
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
- Hostname is anything else (Forgejo / Gitea instance) -> require exposed Forgejo MCP tools. If they are not callable, stop and report that Forgejo MCP is unavailable.

The reviewer subagent inherits this detection via the prompt — tell it which forge and where to find the token, don't make it re-derive.
