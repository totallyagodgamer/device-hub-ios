#!/usr/bin/env python3
"""Repo-local Xcode SDK validation for GitHub-hosted CI.

This replaces the missing external ios-build-support helper used by the project
scripts. It validates that the selected Xcode and iPhoneOS SDK meet the minimum
requirements expected by the app build scripts.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


def parse_version(value: str) -> tuple[int, ...]:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("empty version")
    parts = re.findall(r"\d+", cleaned)
    if not parts:
        raise ValueError(f"cannot parse version from {value!r}")
    return tuple(int(part) for part in parts)


def version_at_least(actual: str, minimum: str) -> bool:
    actual_tuple = parse_version(actual)
    minimum_tuple = parse_version(minimum)
    max_len = max(len(actual_tuple), len(minimum_tuple))
    actual_tuple += (0,) * (max_len - len(actual_tuple))
    minimum_tuple += (0,) * (max_len - len(minimum_tuple))
    return actual_tuple >= minimum_tuple


def run_capture(command: list[str]) -> str:
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    text = (completed.stdout or "") + (completed.stderr or "")
    if completed.returncode != 0:
        raise RuntimeError(f"command failed ({completed.returncode}): {' '.join(command)}\n{text}")
    return text.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Xcode and iOS SDK versions")
    parser.add_argument("--minimum-xcode", required=True)
    parser.add_argument("--minimum-ios-sdk", required=True)
    args = parser.parse_args()

    try:
        developer_dir = Path(run_capture(["/usr/bin/xcode-select", "-p"]))
        if not developer_dir.is_dir():
            raise RuntimeError(f"Xcode developer directory does not exist: {developer_dir}")

        xcode_version_output = run_capture(["/usr/bin/xcodebuild", "-version"])
        xcode_version = None
        match = re.search(r"Xcode\s+([0-9]+(?:\.[0-9]+)+)", xcode_version_output)
        if match:
            xcode_version = match.group(1)
        else:
            match = re.search(r"Xcode\s+([0-9]+)", xcode_version_output)
            if match:
                xcode_version = match.group(1)
        if xcode_version is None:
            raise RuntimeError(f"unable to parse Xcode version from:\n{xcode_version_output}")

        if not version_at_least(xcode_version, args.minimum_xcode):
            raise RuntimeError(
                f"selected Xcode {xcode_version} is below minimum required {args.minimum_xcode}"
            )

        sdk_output = run_capture(["/usr/bin/xcodebuild", "-showsdks"])
        sdk_versions = []
        for line in sdk_output.splitlines():
            match = re.search(r"iphoneos([0-9]+(?:\.[0-9]+)*)", line, flags=re.IGNORECASE)
            if match:
                sdk_versions.append(match.group(1))

        if not sdk_versions:
            raise RuntimeError(f"no iPhoneOS SDKs were found in:\n{sdk_output}")

        if not any(version_at_least(version, args.minimum_ios_sdk) for version in sdk_versions):
            raise RuntimeError(
                f"no installed iPhoneOS SDK meets minimum {args.minimum_ios_sdk}; found: {', '.join(sorted(set(sdk_versions)))}"
            )

        print(f"Xcode {xcode_version} OK")
        print(f"iPhoneOS SDK versions: {', '.join(sorted(set(sdk_versions)))}")
        return 0
    except Exception as exc:  # pragma: no cover - simple CLI for build scripts
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
