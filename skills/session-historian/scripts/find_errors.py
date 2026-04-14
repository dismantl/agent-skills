#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys

sys.dont_write_bytecode = True

from session_historian_lib import build_error_report, filter_sessions, load_sessions, parse_args_common


def main() -> None:
    parser = argparse.ArgumentParser()
    parse_args_common(parser)
    args = parser.parse_args()

    sessions = filter_sessions(load_sessions(args.source), project=args.project, days=args.days)
    print(json.dumps(build_error_report(sessions), indent=2))


if __name__ == "__main__":
    main()
