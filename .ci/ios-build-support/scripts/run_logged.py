#!/usr/bin/env python3
"""Minimal local replacement for the shared ios-build-support runner logger.

This repository's build scripts expect a checkout under SHARED_IOS_SUPPORT_DIR
with scripts/run_logged.py. GitHub-hosted CI does not provide that external
checkout, so this shim keeps the workflow self-contained while preserving the
expected CLI contract used by the project scripts.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a command while logging output to a file")
    parser.add_argument("--log", required=True, type=Path)
    parser.add_argument("--label", required=True)
    parser.add_argument("--timeout", required=True, type=float)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    command = args.command
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        print("error: no command provided", file=sys.stderr)
        return 2

    args.log.parent.mkdir(parents=True, exist_ok=True)

    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=args.timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        message = f"{args.label}: command timed out after {args.timeout} seconds\n"
        args.log.write_text(message, encoding="utf-8")
        print(message.strip(), file=sys.stderr)
        return 124
    except OSError as exc:
        args.log.write_text(f"{args.label}: failed to execute command: {exc}\n", encoding="utf-8")
        print(str(exc), file=sys.stderr)
        return 1

    output = result.stdout or ""
    args.log.write_text(output, encoding="utf-8")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
