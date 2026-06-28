---
name: multi-axis-review
description: "Use when reviewing a pull request, a diff, or a chunk of recently written code — phrases like \"review this PR\", \"review the diff\", \"code review this\", \"is this ready to merge\", or any request to assess code quality before it lands. Produces a structured, severity-rated review across correctness, readability, architecture, security, performance, tests, comments, error handling, and maintainability / tech-debt. Tool-agnostic: works in Codex, Claude Code, or any agent that can read a diff."
---

# Code Review

Multi-axis review of a code change, producing a structured verdict that downstream loops, humans, or merge-bot tooling can consume without further parsing.

This skill is the *thinking framework and output contract*. It does not post comments, fetch diffs, or push fixes — those live with the caller (e.g. a PR loop, an interactive session, a CI hook). Hand the reviewer a diff and any repo guidance; the reviewer returns the structured output described in [Output Contract](#output-contract).

## When to use

- Before merging any PR or change.
- When a fresh-context reviewer is needed (PR loops spawn one of these per round).
- After completing a feature, fixing a bug, or generating code with another agent.
- When a single-axis review (just security, just tests) is wanted — invoke this skill and restrict the axes.

For continuous "review then fix until merge-ready" loops, see `pr-loop`. That skill uses this one as the per-round reviewer.

## Approval philosophy

Approve when the change definitely improves overall code health, even if it isn't perfect. Perfect code does not exist. Don't block a change because it isn't how you would have written it. If it improves the codebase and follows project conventions, approve it.

Don't rubber-stamp either. "LGTM" without evidence helps no one. Push back on real issues directly, propose alternatives, and accept override gracefully when the author has full context.

## The holistic gate (first pass)

Before reviewing a single line, make one judgment about the change *as a whole*: is this the right solution to the problem it solves, or does the approach itself need to be reconsidered? A senior engineer asks "should this exist in this form at all?" *before* "is line 42 correct?" This gate is that question, run first.

**Run it in the same pass — do not spin up a separate pre-reviewer.** You read the diff and stated intent once; make this judgment on that read, and only if it passes do you continue into the detailed axes over the same material. A separate gate agent would re-read everything and cost more on the common case (good PRs) than it ever saves on the rare block.

**Two outcomes:**

- **Block** — the approach is wrong in a way that makes line-level review moot. Return `Verdict: blocked` with `Blocked-reason: approach` (see [Output Contract](#output-contract)), state the objection in the summary, and **stop — do not enumerate line-level findings.** They would describe code that should not exist.
- **Proceed** — the approach is sound, or merely imperfect. Continue to the detailed axes. **This is the default.**

**The bar to block is high. Block only when you can name all three:**

1. **A concrete fatal flaw in the *approach*** — not a line bug, the strategy: solving at the wrong layer, reinventing a well-tested stdlib / framework / library feature, depending on private or internal APIs that break on a routine upstream bump, fighting an existing repo convention without justification, or adding a new mechanic where the repo already has one that fits.
2. **A concrete, repo-compatible alternative** — a specific better path that uses this codebase's existing patterns and tools. "Configure retries once in the existing client factory" — *not* "do it more cleanly."
3. **Why detailed review would be moot** — if (1) holds and (2) is taken, the changed code is replaced wholesale, so reviewing its lines is wasted effort. A change can carry a real line-level bug *and* still be blocked here, because the buggy code disappears under the rewrite.

If you cannot fill all three, **proceed — do not block.** A change that merely isn't how you'd have written it, that has a fixable bug on a sound approach, where you suspect-but-cannot-name a better way, or whose problem is an accumulation of small issues rather than one fatal flaw — all go through normal review. Don't aggregate nits into a block. When in doubt, proceed.

**This is the Approval philosophy at verdict altitude, not a contradiction of it.** The skill already refuses "I'd have written it differently" as a *finding* (see [What you do NOT flag](#what-you-do-not-flag)); the same rule governs the gate. Block only on a demonstrable approach flaw with a named alternative — never on preference, taste, or style. A false block is costlier than a false finding: it halts the pipeline, and a gate that cries wolf trains authors to override it on sight.

## Inputs

- **Diff** — the changed lines plus enough surrounding context to assess data flow. Sources include `git diff`, `git diff --cached`, `gh pr diff <N>`, or Forgejo MCP diff tooling supplied by the caller.
- **PR metadata** (when applicable) — title, description, author, base branch.
- **Repo guidance** — any `CLAUDE.md`, `AGENTS.md`, `README`, style guide, or `CONTRIBUTING.md` the change must conform to. Conventions in those files override generic best practices.
- **Optional axis filter** — restrict the review to specific axes (e.g. `security` only, `tests + errors`). Default is all applicable axes.

## The axes

Every review evaluates the change across these dimensions, but **only run an axis when the diff can actually trigger it**. Walking every axis on every PR wastes time and tokens, dilutes signal, and produces noise findings that get rationalized into "important." Decide axis applicability *before* reviewing, using [Axis applicability](#axis-applicability) below.

### 1. Correctness

Does the code do what it claims to do?

- Matches the spec or task requirements.
- Edge cases handled (null, empty, boundary values, off-by-one).
- Error paths handled, not just the happy path.
- Tests actually exercise the behavior, not implementation details.
- No race conditions, state inconsistencies, or unhandled async failures.

### 2. Readability and simplicity

Can another engineer (or agent) understand this without the author explaining it?

- Names descriptive and consistent with project conventions (no `temp`, `data`, `result` without context).
- Control flow is straightforward (avoid nested ternaries, deep callbacks).
- Code organized logically (related code grouped, clear module boundaries).
- "Clever" tricks justified or simplified.
- Could this be done in fewer lines without losing clarity?
- Abstractions earn their complexity (don't generalize until the third use case).
- Comments clarify *why*, not *what*. Obvious code shouldn't be commented.
- No dead-code artifacts: no-op variables (`_unused`), backwards-compat shims, `// removed` tombstones.

### 3. Architecture

Does the change fit the system's design?

- Follows existing patterns or introduces a new one *with justification*.
- Maintains clean module boundaries.
- Code duplication that should be shared.
- Dependencies flow in the right direction (no circular deps).
- Abstraction level appropriate (not over-engineered, not too coupled).

### 4. Security

Real, exploitable issues only — not theoretical risks or best-practice nitpicks. Reason internally about exploitability × impact, then map to the [canonical severities](#severity-vocabulary) for the output contract.

Look for:

- **Injection / input handling**: SQL injection (raw concatenation), command injection (unsanitized shell input), XSS (unescaped user input in HTML/templates), path traversal, SSRF (user URLs to HTTP clients without allowlist), template injection, unsafe deserialization.
- **Auth / authz**: missing or bypassable authentication, broken access control (IDOR, horizontal/vertical escalation), hardcoded credentials/keys/secrets, weak session management, missing CSRF on state-changing operations, JWT issues (missing signature verification, algorithm confusion, weak secrets).
- **Crypto / secrets**: broken algorithms (MD5, SHA1, DES, RC4, ECB) for security purposes, hardcoded keys/IVs, weak key derivation, non-cryptographic randomness for security-sensitive tokens, secrets in logs / errors / client bundles.
- **Data exposure**: sensitive data in logs (passwords, tokens, PII), verbose error messages leaking internals, missing rate limiting on auth or sensitive endpoints, unencrypted transit/storage, overly permissive CORS.
- **Logic / config**: TOCTOU races in security-critical paths, missing validation at trust boundaries, insecure defaults (debug mode, permissive perms, open redirects), dependency vulnerabilities affecting the actual usage pattern, missing security headers in new endpoint code (CSP, HSTS, X-Frame-Options).

For each finding, internally rate **exploitability** (High / Medium / Low — how easy to exploit?) and **impact** (Critical / High / Medium / Low — what happens if exploited?), then map:

- **High exploitability + Critical/High impact** → `critical`
- **Medium+ exploitability + High impact**, or **High exploitability + Medium impact** → `important`
- **Medium exploitability + Medium impact**, or anything with real but lower risk → `minor`

If you cite a CVE, name the version and confirm the usage pattern is actually affected.

### 5. Performance

Real bottlenecks only. Quantify when possible.

- N+1 query patterns.
- Unbounded loops or unconstrained data fetching.
- Synchronous operations that should be async.
- Unnecessary re-renders in UI components.
- Missing pagination on list endpoints.
- Large allocations in hot paths.

"This N+1 query will add ~50ms per item in the list" beats "this could be slow."

### 6. Tests

- Tests exist for the change.
- They test behavior, not implementation details.
- Edge cases covered (the same ones flagged under Correctness).
- Bug-fix PRs include a regression test.
- Test names describe what they verify.
- The tests would actually catch a regression if the code changed.

### 7. Comments and documentation

- Comments accurate vs the code they describe (no comment rot).
- Public APIs documented at the boundary.
- Non-obvious *why* explained; obvious *what* not commented.
- Docstrings match parameter names and return types.
- Removed code's comments also removed (no orphaned references).

### 8. Error handling

No silent failures. Catch blocks that swallow errors are defects.

- Every error path either logs (with context) or surfaces to the user actionably.
- Catch blocks don't `return null` / `return false` / no-op without explanation.
- Fallback behavior is explicit and bounded; "fallback to whatever" is a smell.
- Errors carry context so callers can debug without adding instrumentation.
- Language-specific: Go errors wrapped with `fmt.Errorf("doing X: %w", err)`; Python exceptions chained with `from`; JS rejections not lost in fire-and-forget promises.

### 9. Type design

- Types express invariants — illegal states unrepresentable where practical.
- Encapsulation: internals not leaked; mutation paths controlled.
- Useful: actually constrains the code that uses them, vs being a synonym for `any`.
- Enforced: invariants checked at the boundary, not assumed.

### 10. Maintainability and future change cost

What will this code cost the next engineer who has to change it? The lens here is *cost of the next edit*, not immediate comprehension (Readability) or system fit (Architecture).

The framing matters because AI-assisted output without a maintainability check trades a one-time throughput win for compounding maintenance debt. If a change doubles the code you ship, it has to roughly halve the per-line cost of future change to come out ahead — otherwise the team is borrowing capacity from its future self. Flag patterns that look fine in isolation but multiply across edits.

Look for:

- **Change amplification**: one conceptual change requires edits across many unrelated places — the abstraction is missing or wrong.
- **Implicit contracts**: behavior callers depend on that isn't expressed in types, tests, or comments. The next refactor will silently break it.
- **Magic constants and environment assumptions**: hardcoded values, machine-specific paths, "works on my box" defaults buried in code.
- **Copy-paste with drift potential**: near-duplicate code that will diverge as it gets edited. Some duplication is safer than premature DRY — flag the cases where divergence is the more likely failure mode.
- **Reinvented stdlib / framework features**: handrolled date parsing, custom logger, ad-hoc retry loop where the language or framework already ships a well-tested one. Each handrolled wheel is permanent maintenance.
- **Hidden coupling**: modules that talk through global state, ambient context, or "just happen to be called in the right order." The next person won't know not to rearrange them.
- **Discoverability gaps**: code in unexpected locations, names that don't match what the code does, undocumented entry points. A maintainer who can't find the code can't safely change it.
- **Brittle tests**: tests that break on unrelated refactors, mock internals, or re-implement the system-under-test. These actively raise the cost of every future change.
- **TODOs without an owner or follow-up**: deferred work that quietly becomes permanent. Either link to an issue or do the work.
- **AI-generated boilerplate without provenance**: large blocks of plausible-looking code where it's unclear which lines are load-bearing vs filler. If the author can't say what each section does, the next maintainer won't either.
- **Vendored or pinned-old dependencies**: outdated libraries embedded for short-term convenience that someone will inherit upgrading.

The question to ask on every flag: "Six months from now, when someone has to extend or fix this, what will slow them down?" If the answer is "nothing specific" don't flag it. If the answer is concrete — a name they'll misread, a contract they'll miss, a duplicate they'll forget to update — flag it.

### 11. Change-level concerns

- **Size**: ~100 LOC is good, ~300 LOC acceptable for a single logical change, ~1000 LOC is too large — flag for splitting unless it's an automated refactor or wholesale deletion.
- **Scope**: one logical change per change. Refactors mixed with feature work should be split.
- **Description**: PR/commit message stands alone in version control history. Imperative first line, body explains *why*, links to issues/benchmarks/design docs. Anti-patterns: "Fix bug", "Phase 1", "Moving code from A to B".
- **Dependencies added**: prefer stdlib; new deps need justification (size, maintenance, license, vulnerabilities).

## Axis applicability

The [holistic gate](#the-holistic-gate-first-pass) runs *before* this table — it is not an axis. Only changes that clear the gate reach axis selection at all.

Decide which axes apply *before* reviewing. Skipping inapplicable axes is the point — a single-mind reviewer that dutifully walks all ten on a docs-only PR will manufacture noise.

| Axis | Always run | Skip when... |
|---|---|---|
| Correctness | yes | — |
| Readability | yes | (skip only on a pure mechanical rename / generated-file diff) |
| Architecture | usually | diff is docs-only, config-only, or a pure rename |
| **Security** | usually | diff is docs-only or comments-only with no executable paths added/changed |
| Performance | conditional | no hot paths, queries, loops, network calls, or rendering touched |
| **Tests** | conditional | the diff *is* the tests, or it's docs/config-only with no behavior change |
| Comments | conditional | no comments or docstrings added, modified, or made stale by code changes |
| **Error handling** | conditional | no `try`/`catch`/`except`/error-return paths added or changed |
| Type design | conditional | no types, structs, classes, interfaces, or schemas added or modified |
| Maintainability | usually | diff is docs-only, generated-file regeneration, or a pure mechanical rename with no semantic changes |
| Change-level | yes | — |

"Conditional" axes are the ones the toolkit-style review treats as opt-in specialists. The single-mind reviewer follows the same rule: if the diff doesn't touch the axis surface area, don't review it. Don't manufacture findings to justify having checked.

A docs-only PR typically runs Correctness (does the doc match the code?), Readability, Comments, and Change-level — and skips the rest. A pure dependency-version bump runs Correctness, Security (CVE check on the new version), Maintainability (is the upgrade path worse than the version we're on?), and Change-level. A test-only PR runs Correctness, Readability, Tests (is the new test useful and well-named?), Maintainability (will this test be brittle?), and Change-level.

When you skip an axis, **don't list it as a finding-free section** — just don't mention it. The Output Contract's empty-section rule already handles this.

In the [optional fan-out](#optional-fan-out-subagent-capable-runtimes) path, the same applicability table determines which specialists to dispatch. Don't dispatch a security specialist for a docs-only PR.

## Severity vocabulary

Use these three at the verdict level — the output contract depends on them and downstream loops parse them:

| Severity | Meaning |
|---|---|
| **critical** | Blocks merge. Security vulnerability, data loss, broken functionality, exploitable bug. |
| **important** | Should fix before merge. Real defect, architectural problem, missing test for new logic, silent failure. |
| **minor** | Nice to fix; safe to defer. Style, clarity nit, optional refactor, low-impact perf, FYI. |

### Disposition tags (required on `minor` findings)

`minor` is a wide bucket — a one-line style nit and a "real but defer-to-followup" issue both land there. Every minor finding must carry exactly one disposition tag so the author can triage at a glance:

| Tag | Meaning |
|---|---|
| `nit:` | Style or clarity, no behavior impact. Drive-by fix or skip. |
| `consider:` | Design judgment call. Author should weigh; not a defect. |
| `defer:` | Real but small. File a follow-up issue, don't block merge. |
| `fyi:` | Informational only. No action expected. |

Tags appear inline in the finding text, e.g. `foo.go:42 — nit: variable name 'data' is non-descriptive`.

The **counts in the output contract still use only `critical / important / minor`** — downstream loops such as `pr-loop` parse those tokens. Dispositions are for human triage, not machine parsing.

`critical` and `important` findings do not take dispositions — those are by definition "fix before merge" and the disposition would be redundant.

## What you do NOT flag

To keep signal high:

- Issues a linter, type checker, or SAST tool would catch (assume those run in CI).
- Pre-existing issues in unchanged code, unless the diff makes them newly exploitable / reachable.
- Theoretical timing attacks without a realistic exploitation path.
- Dependencies with CVEs that don't affect the usage pattern in this code.
- Generic "you should add rate limiting" without evidence of an actual abuse vector.
- Missing security headers on non-web endpoints.
- Code style preferences dressed up as substantive concerns.
- Suggestions whose only justification is "I would have written it differently."

## Process

1. **Read the context.** PR title, description, linked issue, and any repo guidance (`CLAUDE.md`, `AGENTS.md`, `CONTRIBUTING.md`). The change's *intent* shapes how you weight findings.
2. **Run the holistic gate.** On that first read, judge the approach as a whole (see [The holistic gate](#the-holistic-gate-first-pass)). If it fails the three-part bar, return `Verdict: blocked` / `Blocked-reason: approach` with the objection in the summary and **stop here** — skip the remaining steps; no line-level findings. Otherwise proceed.
3. **Read the tests first.** Tests reveal intent and coverage. A change with well-named, behavior-focused tests is easier to assess.
4. **Walk the diff with all axes in mind**, file by file. Don't single-pass for one axis at a time unless the user asked for that — issues cluster, and missing context across axes is how false positives happen.
5. **Follow data flows from changed code into existing code** when needed to assess risk (especially for security and correctness). Don't audit the whole codebase; do trace what the diff touches.
6. **Categorize each finding** as `critical`, `important`, or `minor`. Group by severity in the output, critical first.
7. **Quantify when possible.** "Adds ~50ms per item, list pages typically have 200 items" beats "could be slow."
8. **Verify the verification.** Did tests run? Did the build pass? Was a UI change actually loaded in a browser? If the author claims "tested manually," is there a screenshot or a description?
9. **Assemble the output** per [Output Contract](#output-contract).

## Output Contract

The reviewer's final message must follow this exact structure. Loops parse it; downstream tooling depends on it.

```
Verdict: <merge-ready | needs-work | blocked>
Severity: critical=<N> important=<N> minor=<N>
Blocked-reason: <approach | incomplete>   # present only when Verdict is blocked

Critical findings:
- <path/to/file>:<line> — <one-line description>
- ...

Important findings:
- <path/to/file>:<line> — <one-line description>
- ...

Minor findings:
- <path/to/file>:<line> — <disposition>: <one-line description>
- ...

Summary:
<1–3 sentences: overall assessment, biggest themes, next step.>
```

Rules:

- Omit a findings section entirely if the count for that severity is zero. Do not write "Critical findings: none" — just leave the section out and let the count speak.
- `Verdict: merge-ready` requires `critical=0` and `important=0`. Minor findings are allowed at merge-ready.
- `Verdict: needs-work` is the default when at least one critical or important finding exists.
- `Verdict: blocked` halts review and escalates to a human. It always carries a `Blocked-reason`:
  - `approach` — the holistic gate rejected the change's approach (see [The holistic gate](#the-holistic-gate-first-pass)). The detailed axes were intentionally skipped, so severity counts are normally `critical=0 important=0 minor=0`. List **no** line-level findings; the Summary carries the objection and names all three of: the fatal flaw, the repo-compatible alternative, and why line review is moot.
  - `incomplete` — the review couldn't be performed (diff unreadable, repo guidance missing, ambiguous intent that needs a human). Use sparingly.
- File:line references are required for every finding. If a finding spans a region, use the start line.
- Every `minor` finding must carry exactly one disposition tag (`nit:`, `consider:`, `defer:`, `fyi:`) immediately after the em-dash. See [Disposition tags](#disposition-tags-required-on-minor-findings).
- The summary is human-facing and short. Detail goes in the per-finding lines.

For each finding, when posting an inline review comment to the PR (this skill doesn't post; the caller does), include:

- **Severity**: critical / important / minor
- **Disposition** (minor only): nit / consider / defer / fyi
- **Category**: e.g. SQL injection, missing test, dead code, N+1 query
- **What**: the issue in plain language
- **Why it matters**: the consequence (exploit scenario for security, performance impact with numbers, regression risk for tests)
- **Fix**: a concrete code change or approach
- **Repo guidance**: if `CLAUDE.md` / `AGENTS.md` / style guide says something relevant, cite it

A clean report is a good report. If nothing is wrong, return `Verdict: merge-ready`, zero counts, and a one-sentence summary noting what you checked.

## Optional fan-out (subagent-capable runtimes)

Run the [holistic gate](#the-holistic-gate-first-pass) yourself, in the aggregating context, *before* dispatching any specialists. If the gate blocks on approach, return `blocked` / `approach` and dispatch nothing — every specialist finding would describe code slated for wholesale replacement.

If the runtime exposes subagent tools to the reviewer, active policy permits using them, and the caller has not forbidden an extra context tier, the reviewer may dispatch per-axis specialists in parallel and aggregate, instead of reviewing single-mind. Examples include Claude Code's `Agent` tool and Codex's `spawn_agent` tool when available in the current context. **Use [Axis applicability](#axis-applicability) to decide which specialists to dispatch** — don't fan out to all of them on every PR. A docs-only PR doesn't need a security or types specialist; dispatching them anyway costs time and tokens for guaranteed-empty reports.

If a caller requires a two-context review loop, such as `pr-loop`, do not use this optional fan-out. Review single-mind inside the fresh reviewer so the caller's architecture remains intact.

Specialists that map cleanly:

| Axis | Specialist focus |
|---|---|
| Security | OWASP Top 10, exploitability/impact rating, low false-positive bias |
| Tests | Behavioral coverage, regression-test presence on bug fixes, test quality |
| Errors | Silent failures, swallowed catches, missing context propagation |
| Comments | Comment rot, accuracy vs code, documentation completeness |
| Types | Encapsulation, invariant expression, enforcement |
| Maintainability | Change amplification, hidden coupling, reinvented stdlib, brittle tests, AI-boilerplate provenance |
| Code (general) | Project-convention compliance per `CLAUDE.md`, miscellaneous quality |

The aggregated output must still satisfy the [Output Contract](#output-contract). Don't surface raw per-specialist sub-reports as the final message — the loop and downstream tools expect the canonical format.

In any environment where fan-out is unavailable or not permitted, review single-mind across all axes. Both produce equally valid output; fan-out is a speed optimization, not a correctness requirement.

## Honesty

- Don't soften real issues. "This might be a minor concern" when it's a critical bug is dishonest.
- Don't accept "I'll clean it up later." Experience shows deferred cleanup rarely happens. Require cleanup before merge unless it's a genuine emergency, and ask for a follow-up issue with self-assignment.
- Push back on approaches with clear problems. Sycophancy is a failure mode in reviews.
- Comment on code, not people. Reframe personal critiques to focus on the code.
- Accept override gracefully when the author has full context and disagrees.

## Disagreement resolution

When the author pushes back on a finding:

1. **Technical facts and data** override opinions and preferences.
2. **Repo guidance and style guides** are authoritative on style matters.
3. **Engineering principles** are the basis for design disagreements, not personal taste.
4. **Codebase consistency** is acceptable if it doesn't degrade overall health.

If a finding survives one fix attempt and is re-raised in a fresh-context review, the loop's deadlock detection will surface it; see `pr-loop`.

## Common rationalizations

| Rationalization | Reality |
|---|---|
| "It works, that's good enough" | Working but unreadable / insecure / architecturally wrong code creates compounding debt. |
| "I wrote it, so I know it's correct" | Authors are blind to their own assumptions. |
| "We'll clean it up later" | Later rarely comes. The review is the gate. |
| "AI-generated code is probably fine" | AI code needs more scrutiny, not less — confident and plausible even when wrong. |
| "The tests pass, so it's good" | Tests are necessary but not sufficient. They don't catch architecture or security issues. |
| "It's a small change, light review is fine" | Small changes can carry critical bugs. The axes still apply. |
| "We're moving fast with AI, we'll pay down the debt later" | Throughput without a maintainability check is a loan against future capacity. The review *is* when you decide whether the loan is worth taking. |
| "This isn't how I'd have built it, so I'll block the approach" | A [gate](#the-holistic-gate-first-pass) block needs a named fatal flaw *and* a concrete repo-compatible alternative *and* moot line review. Can't name all three? Proceed and review normally. |

## Red flags in your own review

- You wrote "LGTM" without evidence of having walked the diff.
- All findings are nits; no axis was actually exercised.
- Security-sensitive change reviewed without a security pass.
- Large change ("too big to review properly") accepted as-is — split it instead.
- A bug-fix PR with no regression test, accepted without flagging.
- Missing severity labels — author can't tell what's required vs optional.
- You returned `blocked` / `approach` without naming a concrete, repo-compatible alternative — that's preference dressed up as a gate.
- You blocked on approach but the changed code would mostly survive your proposed alternative — line review wasn't actually moot, so it should have proceeded.

## Verification

After producing the review:

- If `Verdict: blocked`, a `Blocked-reason` (`approach` or `incomplete`) is present; it is absent otherwise.
- If `Blocked-reason: approach`, the Summary names all three — fatal flaw, concrete repo-compatible alternative, why line review is moot — and **no** line-level findings are listed.
- All findings have a `path:line` reference.
- Every `minor` finding carries exactly one disposition tag (`nit:`, `consider:`, `defer:`, `fyi:`).
- Verdict matches the severity counts (`merge-ready` only when `critical=0` and `important=0`).
- Summary is 1–3 sentences and reflects the findings.
- No section is left as "none" — omit empty sections instead.
