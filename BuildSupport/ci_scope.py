"""Select the smallest safe local CI scope for the current Git checkout."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from typing import Iterable


def is_documentation_only(paths: Iterable[str]) -> bool:
    """Return whether every changed path is documentation."""
    changed_paths = tuple(paths)
    return bool(changed_paths) and all(
        path == "LICENSE"
        or path.endswith(".md")
        or path.startswith("Docs/")
        for path in changed_paths
    )


def _git_lines(repository: Path, *arguments: str) -> set[str]:
    result = subprocess.run(
        ("git", *arguments),
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )
    return {line for line in result.stdout.splitlines() if line}


def _default_upstream(repository: Path) -> str | None:
    """Return the upstream/default branch if a remote branch is available."""
    for command in (
        ("git", "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"),
        ("git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"),
    ):
        result = subprocess.run(
            command,
            cwd=repository,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            value = result.stdout.strip()
            if value:
                return value.removeprefix("origin/")

    remote_show = subprocess.run(
        ("git", "remote", "show", "origin"),
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
    )
    if remote_show.returncode == 0:
        for line in remote_show.stdout.splitlines():
            stripped = line.strip()
            if stripped.startswith("HEAD branch:"):
                return stripped.split(":", 1)[1].strip()

    return None


def changed_paths(repository: Path) -> set[str]:
    """Return committed, staged, unstaged, and untracked local changes."""
    paths = _git_lines(
        repository,
        "diff",
        "--name-only",
        "--diff-filter=ACMRTUXB",
        "HEAD",
    )
    paths |= _git_lines(repository, "ls-files", "--others", "--exclude-standard")

    upstream = _default_upstream(repository)
    if upstream is not None:
        paths |= _git_lines(
            repository,
            "diff",
            "--name-only",
            "--diff-filter=ACMRTUXB",
            f"{upstream}...HEAD",
        )

    return paths


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    arguments = parser.parse_args()
    paths = changed_paths(arguments.repository.resolve())
    print("documentation" if is_documentation_only(paths) else "full")


if __name__ == "__main__":
    main()
