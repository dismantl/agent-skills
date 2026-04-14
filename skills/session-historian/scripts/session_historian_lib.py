#!/usr/bin/env python3

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


CODEX_ROOT = Path.home() / ".codex" / "sessions"
CLAUDE_ROOT = Path.home() / ".claude" / "projects"


@dataclass
class SessionRecord:
    source: str
    session_id: str
    file_path: Path
    start_time: str | None
    end_time: str | None
    cwd: str | None
    git_branch: str | None
    tool_calls: int
    tools_used: list[str]
    error_count: int
    summary: str | None
    messages: int
    raw_events: list[dict[str, Any]]


def parse_args_common(parser) -> None:
    parser.add_argument("--source", choices=["all", "codex", "claude"], default="all")
    parser.add_argument("--project", help="Match cwd or encoded project path by substring")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--limit", type=int, default=20)


def to_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    value = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def within_days(ts: str | None, days: int) -> bool:
    if days <= 0:
        return True
    dt = to_iso(ts)
    if dt is None:
        return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt >= datetime.now(timezone.utc) - timedelta(days=days)


def iter_jsonl(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    try:
        with path.open() as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return []
    return events


def collect_codex_sessions() -> list[SessionRecord]:
    sessions: list[SessionRecord] = []
    if not CODEX_ROOT.exists():
        return sessions

    for path in sorted(CODEX_ROOT.rglob("*.jsonl")):
        events = iter_jsonl(path)
        if not events:
            continue

        session_meta = next((e for e in events if e.get("type") == "session_meta"), None)
        payload = session_meta.get("payload", {}) if session_meta else {}
        session_id = payload.get("id") or path.stem
        cwd = payload.get("cwd")
        git_branch = None
        tool_names: list[str] = []
        error_count = 0
        messages = 0
        summary = None
        timestamps: list[str] = []

        for event in events:
            ts = event.get("timestamp")
            if ts:
                timestamps.append(ts)

            etype = event.get("type")
            if etype == "response_item":
                payload = event.get("payload", {})
                ptype = payload.get("type")
                if ptype == "message":
                    messages += 1
                if ptype == "function_call":
                    tool_names.append(payload.get("name", "unknown"))
            elif etype == "event_msg":
                payload = event.get("payload", {})
                ptype = payload.get("type")
                if ptype == "agent_message":
                    messages += 1
                elif ptype == "exec_command_end":
                    tool_names.append("exec_command")
                    if payload.get("exit_code", 0) != 0:
                        error_count += 1
                    if not git_branch:
                        git_branch = payload.get("git_branch")
            elif etype == "turn_context":
                messages += 1

        if not summary:
            msg = next(
                (
                    e.get("payload", {}).get("message")
                    for e in events
                    if e.get("type") == "event_msg"
                    and e.get("payload", {}).get("type") == "agent_message"
                ),
                None,
            )
            if isinstance(msg, str):
                summary = msg.splitlines()[0][:160]

        sessions.append(
            SessionRecord(
                source="codex",
                session_id=session_id,
                file_path=path,
                start_time=timestamps[0] if timestamps else payload.get("timestamp"),
                end_time=timestamps[-1] if timestamps else payload.get("timestamp"),
                cwd=cwd,
                git_branch=git_branch,
                tool_calls=len(tool_names),
                tools_used=sorted(set(tool_names)),
                error_count=error_count,
                summary=summary,
                messages=messages,
                raw_events=events,
            )
        )

    return sessions


def collect_claude_sessions() -> list[SessionRecord]:
    sessions: list[SessionRecord] = []
    if not CLAUDE_ROOT.exists():
        return sessions

    for path in sorted(CLAUDE_ROOT.rglob("*.jsonl")):
        events = iter_jsonl(path)
        if not events:
            continue

        first = events[0]
        session_id = first.get("sessionId") or path.stem
        cwd = None
        git_branch = None
        tool_names: list[str] = []
        error_count = 0
        messages = 0
        summary = None
        timestamps: list[str] = []

        for event in events:
            ts = event.get("timestamp")
            if ts:
                timestamps.append(ts)

            cwd = cwd or event.get("cwd")
            git_branch = git_branch or event.get("gitBranch")
            etype = event.get("type")
            if etype in {"user", "assistant", "summary"}:
                messages += 1
            message = event.get("message", {})
            if isinstance(message, dict):
                content = message.get("content", [])
                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "tool_use":
                            tool_names.append(item.get("name", "unknown"))
                        if isinstance(item, dict) and item.get("type") == "text" and not summary:
                            text = item.get("text")
                            if isinstance(text, str) and text.strip():
                                summary = text.splitlines()[0][:160]

            tool_result = event.get("toolUseResult")
            if tool_result:
                if isinstance(tool_result, str) and "error" in tool_result.lower():
                    error_count += 1
                elif isinstance(tool_result, dict) and tool_result.get("stderr"):
                    error_count += 1

        sessions.append(
            SessionRecord(
                source="claude",
                session_id=session_id,
                file_path=path,
                start_time=timestamps[0] if timestamps else None,
                end_time=timestamps[-1] if timestamps else None,
                cwd=cwd,
                git_branch=git_branch,
                tool_calls=len(tool_names),
                tools_used=sorted(set(tool_names)),
                error_count=error_count,
                summary=summary,
                messages=messages,
                raw_events=events,
            )
        )

    return sessions


def load_sessions(source: str) -> list[SessionRecord]:
    sessions: list[SessionRecord] = []
    if source in {"all", "codex"}:
        sessions.extend(collect_codex_sessions())
    if source in {"all", "claude"}:
        sessions.extend(collect_claude_sessions())
    return sessions


def filter_sessions(
    sessions: list[SessionRecord],
    *,
    project: str | None = None,
    days: int = 7,
) -> list[SessionRecord]:
    result = [s for s in sessions if within_days(s.start_time, days)]
    if project:
        needle = project.lower()
        result = [
            s
            for s in result
            if needle in (s.cwd or "").lower() or needle in str(s.file_path).lower()
        ]
    result.sort(key=lambda s: s.start_time or "", reverse=True)
    return result


def session_to_dict(session: SessionRecord) -> dict[str, Any]:
    duration_minutes = None
    start = to_iso(session.start_time)
    end = to_iso(session.end_time)
    if start and end:
        duration_minutes = round((end - start).total_seconds() / 60.0, 1)

    return {
        "source": session.source,
        "session_id": session.session_id,
        "start_time": session.start_time,
        "end_time": session.end_time,
        "duration_minutes": duration_minutes,
        "cwd": session.cwd,
        "git_branch": session.git_branch,
        "tool_calls": session.tool_calls,
        "tools_used": session.tools_used,
        "error_count": session.error_count,
        "messages": session.messages,
        "summary": session.summary,
        "file_path": str(session.file_path),
    }


def find_session_by_id(session_id: str, source: str) -> SessionRecord | None:
    for session in load_sessions(source):
        if session.session_id == session_id or session.file_path.stem == session_id:
            return session
    return None


def extract_texts(event: dict[str, Any]) -> list[str]:
    texts: list[str] = []
    payload = event.get("payload")
    if isinstance(payload, dict):
        message = payload.get("message")
        if isinstance(message, str):
            texts.append(message)
    message = event.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str):
            texts.append(content)
        elif isinstance(content, list):
            for item in content:
                if isinstance(item, dict):
                    for key in ("text", "content"):
                        value = item.get(key)
                        if isinstance(value, str):
                            texts.append(value)
    return texts


def event_mentions_text(event: dict[str, Any], needle: str) -> bool:
    haystacks = extract_texts(event)
    for text in haystacks:
        if needle in text.lower():
            return True
    return False


def event_tools(event: dict[str, Any]) -> list[str]:
    names: list[str] = []
    if event.get("type") == "response_item":
        payload = event.get("payload", {})
        if payload.get("type") == "function_call":
            name = payload.get("name")
            if isinstance(name, str):
                names.append(name)
    if event.get("type") == "event_msg":
        payload = event.get("payload", {})
        if payload.get("type") == "exec_command_end":
            names.append("exec_command")
    message = event.get("message", {})
    if isinstance(message, dict):
        content = message.get("content", [])
        if isinstance(content, list):
            for item in content:
                if isinstance(item, dict) and item.get("type") == "tool_use":
                    name = item.get("name")
                    if isinstance(name, str):
                        names.append(name)
    return names


def summarize_session(session: SessionRecord) -> dict[str, Any]:
    timeline: list[dict[str, Any]] = []
    commands: list[str] = []
    files_touched: list[str] = []

    for event in session.raw_events:
        ts = event.get("timestamp")
        label = event.get("type")
        detail = None

        if event.get("type") == "event_msg":
            payload = event.get("payload", {})
            if payload.get("type") == "exec_command_end":
                cmd = payload.get("aggregated_output") or " ".join(payload.get("command", []))
                if isinstance(cmd, str):
                    commands.append(cmd[:200])
                    detail = cmd[:200]
        elif event.get("type") == "response_item":
            payload = event.get("payload", {})
            if payload.get("type") == "function_call":
                detail = payload.get("name")
        elif event.get("type") in {"user", "assistant"}:
            texts = extract_texts(event)
            if texts:
                detail = texts[0][:200]

        if detail:
            timeline.append({"timestamp": ts, "type": label, "detail": detail})

        text_blob = "\n".join(extract_texts(event))
        for match in re.findall(r"(/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+)", text_blob):
            files_touched.append(match)

    return {
        "status": "success",
        "session": session_to_dict(session),
        "timeline": timeline[:200],
        "commands_run": commands[:200],
        "files_touched": sorted(set(files_touched))[:200],
    }


def search_sessions(
    sessions: list[SessionRecord],
    *,
    text: str | None = None,
    tool: str | None = None,
    has_errors: bool = False,
) -> list[SessionRecord]:
    result = sessions
    if text:
        needle = text.lower()
        result = [s for s in result if any(event_mentions_text(e, needle) for e in s.raw_events)]
    if tool:
        needle = tool.lower()
        result = [s for s in result if any(needle == t.lower() for e in s.raw_events for t in event_tools(e))]
    if has_errors:
        result = [s for s in result if s.error_count > 0]
    return result


def build_error_report(sessions: list[SessionRecord]) -> dict[str, Any]:
    total_errors = sum(s.error_count for s in sessions)
    sessions_with_errors = [s for s in sessions if s.error_count > 0]
    return {
        "status": "success",
        "total_sessions": len(sessions),
        "sessions_with_errors": len(sessions_with_errors),
        "error_rate": round((len(sessions_with_errors) / len(sessions)) * 100, 1) if sessions else 0.0,
        "total_errors": total_errors,
        "affected_sessions": [session_to_dict(s) for s in sessions_with_errors[:50]],
    }


def build_cross_session_analysis(sessions: list[SessionRecord], focus: str) -> dict[str, Any]:
    if focus == "tools":
        counter = Counter(tool for session in sessions for tool in session.tools_used)
        return {"status": "success", "focus": focus, "tools": counter.most_common(20)}
    if focus == "failures":
        return build_error_report(sessions) | {"focus": focus}
    if focus == "duration":
        durations = [
            session_to_dict(s)["duration_minutes"]
            for s in sessions
            if session_to_dict(s)["duration_minutes"] is not None
        ]
        if not durations:
            return {"status": "success", "focus": focus, "durations": None}
        return {
            "status": "success",
            "focus": focus,
            "count": len(durations),
            "min": min(durations),
            "max": max(durations),
            "avg": round(sum(durations) / len(durations), 1),
            "median": sorted(durations)[len(durations) // 2],
        }
    if focus == "commands":
        counter = Counter()
        for session in sessions:
            summary = summarize_session(session)
            counter.update(summary["commands_run"])
        return {"status": "success", "focus": focus, "commands": counter.most_common(20)}
    raise ValueError(f"unsupported focus: {focus}")
