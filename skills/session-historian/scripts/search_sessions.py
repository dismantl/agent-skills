#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys

sys.dont_write_bytecode = True

from session_historian_lib import filter_sessions, load_sessions, parse_args_common, search_sessions, session_to_dict


def main() -> None:
    parser = argparse.ArgumentParser()
    parse_args_common(parser)
    parser.add_argument("--text")
    parser.add_argument("--tool")
    parser.add_argument("--has-errors", action="store_true")
    args = parser.parse_args()

    sessions = filter_sessions(load_sessions(args.source), project=args.project, days=args.days)
    sessions = search_sessions(sessions, text=args.text, tool=args.tool, has_errors=args.has_errors)
    print(json.dumps({"status": "success", "sessions": [session_to_dict(s) for s in sessions[: args.limit]]}, indent=2))


if __name__ == "__main__":
    main()
