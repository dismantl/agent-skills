ROOT ?= $(CURDIR)/skills/session-historian

.PHONY: smoke-session-historian install-codex-links install-claude-links

smoke-session-historian:
	test -d "$(ROOT)/scripts"
	python3 -B "$(ROOT)/scripts/list_sessions.py" --source all --days 30 --limit 2 >/tmp/agent-skills-session-historian.json
	test -s /tmp/agent-skills-session-historian.json
	@echo "session-historian smoke test ok"

install-codex-links:
	mkdir -p "$(HOME)/.agents/skills"
	ln -sfn "$(CURDIR)/skills/forgejo-pr" "$(HOME)/.agents/skills/forgejo-pr"
	ln -sfn "$(CURDIR)/skills/handoff" "$(HOME)/.agents/skills/handoff"
	ln -sfn "$(CURDIR)/skills/session-historian" "$(HOME)/.agents/skills/session-historian"

install-claude-links:
	mkdir -p "$(HOME)/.claude/skills"
	ln -sfn "$(CURDIR)/skills/forgejo-pr" "$(HOME)/.claude/skills/forgejo-pr"
	ln -sfn "$(CURDIR)/skills/handoff" "$(HOME)/.claude/skills/handoff"
	ln -sfn "$(CURDIR)/skills/session-historian" "$(HOME)/.claude/skills/session-historian"
