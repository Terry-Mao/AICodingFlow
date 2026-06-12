#!/usr/bin/env python3
"""Validate update-triage writes stayed in allowed runtime output targets."""

from __future__ import annotations

import argparse
import subprocess
import sys


ALLOWED_FILES = (
    ".github/skills/triage-issue-repo/SKILL.md",
    ".github/issue-triage/config.json",
)


def run_git(args: list[str]) -> list[str]:
    result = subprocess.run(["git", *args], check=True, capture_output=True, text=True)
    return [line for line in result.stdout.splitlines() if line]


def changed_paths() -> list[str]:
    tracked = run_git(["diff", "--name-only", "HEAD", "--"])
    untracked = run_git(["ls-files", "--others", "--exclude-standard"])
    return sorted(set(tracked + untracked))


def path_allowed(path: str) -> bool:
    return path in ALLOWED_FILES


def invalid_paths(paths: list[str]) -> list[str]:
    return [path for path in paths if not path_allowed(path)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--path",
        action="append",
        dest="paths",
        help="Path to validate instead of reading git changes. Repeat for tests/debugging.",
    )
    args = parser.parse_args()

    paths = sorted(set(args.paths)) if args.paths else changed_paths()
    invalid = invalid_paths(paths)

    if invalid:
        print("update-triage write surface violation:", file=sys.stderr)
        for path in invalid:
            print(f"- {path}", file=sys.stderr)
        print("\nAllowed files:", file=sys.stderr)
        for path in ALLOWED_FILES:
            print(f"- {path}", file=sys.stderr)
        return 1

    print("update-triage write surface OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
