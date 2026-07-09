ROOT ?= $(CURDIR)/skills/session-historian

.PHONY: smoke-session-historian smoke-codex-automation-recommender smoke-pr-loop smoke-multi-axis-review install-codex-links install-claude-links install-gemini-links

smoke-session-historian:
	test -d "$(ROOT)/scripts"
	python3 -B "$(ROOT)/scripts/list_sessions.py" --source all --days 30 --limit 2 >/tmp/agent-skills-session-historian.json
	test -s /tmp/agent-skills-session-historian.json
	@echo "session-historian smoke test ok"

smoke-codex-automation-recommender:
	test -f "$(CURDIR)/skills/codex-automation-recommender/SKILL.md"
	grep -q '^name: codex-automation-recommender$$' "$(CURDIR)/skills/codex-automation-recommender/SKILL.md"
	grep -q 'Phase 2 presents a numbered recommendation menu and stops for user selection' "$(CURDIR)/skills/codex-automation-recommender/SKILL.md"
	grep -q 'Phase 3 implements only the selected recommendations' "$(CURDIR)/skills/codex-automation-recommender/SKILL.md"
	test -f "$(CURDIR)/skills/codex-automation-recommender/references/skills-reference.md"
	test -f "$(CURDIR)/skills/codex-automation-recommender/references/plugins-reference.md"
	test -f "$(CURDIR)/skills/codex-automation-recommender/references/hooks-and-rules.md"
	test -f "$(CURDIR)/skills/codex-automation-recommender/references/subagent-and-automation-patterns.md"
	! test -f "$(CURDIR)/skills/codex-automation-recommender/references/codex-surfaces.md"
	! test -f "$(CURDIR)/skills/codex-automation-recommender/references/recommendation-patterns.md"
	grep -q 'codex-automation-recommender' "$(CURDIR)/README.md"
	@echo "codex-automation-recommender smoke test ok"

smoke-pr-loop:
	test -f "$(CURDIR)/skills/pr-loop/SKILL.md"
	grep -q '^name: pr-loop$$' "$(CURDIR)/skills/pr-loop/SKILL.md"
	grep -q 'Codex' "$(CURDIR)/skills/pr-loop/SKILL.md"
	grep -q 'Claude Code' "$(CURDIR)/skills/pr-loop/SKILL.md"
	grep -q 'Gemini CLI' "$(CURDIR)/skills/pr-loop/SKILL.md"
	! test -d "$(CURDIR)/skills/codex-pr-loop"
	! test -d "$(CURDIR)/skills/claude-pr-loop"
	grep -q 'skills/pr-loop' "$(CURDIR)/README.md"
	! grep -q 'codex-pr-loop' "$(CURDIR)/README.md"
	! grep -q 'claude-pr-loop' "$(CURDIR)/README.md"
	! grep -R -E -q 'codex-pr-loop|claude-pr-loop|gemini-pr-loop' "$(CURDIR)/skills" "$(CURDIR)/README.md"
	grep -q 'rm -f "$$(HOME)/.agents/skills/codex-pr-loop"' "$(CURDIR)/Makefile"
	grep -q 'rm -f "$$(HOME)/.claude/skills/claude-pr-loop"' "$(CURDIR)/Makefile"
	@echo "pr-loop smoke test ok"

smoke-multi-axis-review:
	test -f "$(CURDIR)/skills/multi-axis-review/SKILL.md"
	grep -q '^name: multi-axis-review$$' "$(CURDIR)/skills/multi-axis-review/SKILL.md"
	grep -qi 'holistic gate' "$(CURDIR)/skills/multi-axis-review/SKILL.md"
	grep -q 'Blocked-reason: <approach | incomplete>' "$(CURDIR)/skills/multi-axis-review/SKILL.md"
	grep -q 'multi-axis-review' "$(CURDIR)/README.md"
	@echo "multi-axis-review smoke test ok"

install-codex-links:
	mkdir -p "$(HOME)/.agents/skills"
	rm -f "$(HOME)/.agents/skills/codex-pr-loop"
	ln -sfn "$(CURDIR)/skills/pr-loop" "$(HOME)/.agents/skills/pr-loop"
	ln -sfn "$(CURDIR)/skills/multi-axis-review" "$(HOME)/.agents/skills/multi-axis-review"
	ln -sfn "$(CURDIR)/skills/forgejo-pr" "$(HOME)/.agents/skills/forgejo-pr"
	ln -sfn "$(CURDIR)/skills/handoff" "$(HOME)/.agents/skills/handoff"
	ln -sfn "$(CURDIR)/skills/session-historian" "$(HOME)/.agents/skills/session-historian"
	ln -sfn "$(CURDIR)/skills/codex-automation-recommender" "$(HOME)/.agents/skills/codex-automation-recommender"

install-claude-links:
	mkdir -p "$(HOME)/.claude/skills"
	rm -f "$(HOME)/.claude/skills/claude-pr-loop"
	ln -sfn "$(CURDIR)/skills/pr-loop" "$(HOME)/.claude/skills/pr-loop"
	ln -sfn "$(CURDIR)/skills/multi-axis-review" "$(HOME)/.claude/skills/multi-axis-review"
	ln -sfn "$(CURDIR)/skills/forgejo-pr" "$(HOME)/.claude/skills/forgejo-pr"
	ln -sfn "$(CURDIR)/skills/handoff" "$(HOME)/.claude/skills/handoff"
	ln -sfn "$(CURDIR)/skills/session-historian" "$(HOME)/.claude/skills/session-historian"

install-gemini-links:
	mkdir -p "$(HOME)/.agents/skills"
	ln -sfn "$(CURDIR)/skills/pr-loop" "$(HOME)/.agents/skills/pr-loop"
	ln -sfn "$(CURDIR)/skills/multi-axis-review" "$(HOME)/.agents/skills/multi-axis-review"
	ln -sfn "$(CURDIR)/skills/forgejo-pr" "$(HOME)/.agents/skills/forgejo-pr"
