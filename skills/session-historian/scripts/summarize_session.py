#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys

sys.dont_write_bytecode = True

from session_historian_lib import find_session_by_id, summarize_session


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--source", choices=["all", "codex", "claude"], default="all")
    args = parser.parse_args()

    session = find_session_by_id(args.session_id, args.source)
    if session is None:
        print(json.dumps({"status": "error", "error": f"session not found: {args.session_id}"}))
        sys.exit(1)

    print(json.dumps(summarize_session(session), indent=2))


if __name__ == "__main__":
    main()
