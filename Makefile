ROOT ?= $(CURDIR)/skills/session-historian

.PHONY: smoke-session-historian smoke-pr-loop install-codex-links install-claude-links install-gemini-links

smoke-session-historian:
	test -d "$(ROOT)/scripts"
	python3 -B "$(ROOT)/scripts/list_sessions.py" --source all --days 30 --limit 2 >/tmp/agent-skills-session-historian.json
	test -s /tmp/agent-skills-session-historian.json
	@echo "session-historian smoke test ok"

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

install-codex-links:
	mkdir -p "$(HOME)/.agents/skills"
	rm -f "$(HOME)/.agents/skills/codex-pr-loop"
	ln -sfn "$(CURDIR)/skills/pr-loop" "$(HOME)/.agents/skills/pr-loop"
	ln -sfn "$(CURDIR)/skills/multi-axis-review" "$(HOME)/.agents/skills/multi-axis-review"
	ln -sfn "$(CURDIR)/skills/forgejo-pr" "$(HOME)/.agents/skills/forgejo-pr"
	ln -sfn "$(CURDIR)/skills/handoff" "$(HOME)/.agents/skills/handoff"
	ln -sfn "$(CURDIR)/skills/session-historian" "$(HOME)/.agents/skills/session-historian"

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
