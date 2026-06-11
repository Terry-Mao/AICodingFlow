#!/usr/bin/env python3
"""Validate update-dedupe writes stayed in the dedupe companion skill."""

from __future__ import annotations

import argparse
import subprocess
import sys


ALLOWED_PREFIXES = (".github/skills/dedupe-issue-repo/",)


def run_git(args: list[str]) -> list[str]:
    result = subprocess.run(["git", *args], check=True, capture_output=True, text=True)
    return [line for line in result.stdout.splitlines() if line]


def changed_paths() -> list[str]:
    tracked = run_git(["diff", "--name-only", "HEAD", "--"])
    untracked = run_git(["ls-files", "--others", "--exclude-standard"])
    return sorted(set(tracked + untracked))


def invalid_paths(paths: list[str], allowed_prefixes: tuple[str, ...] = ALLOWED_PREFIXES) -> list[str]:
    return [path for path in paths if not path.startswith(allowed_prefixes)]


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
        print("update-dedupe write surface violation:", file=sys.stderr)
        for path in invalid:
            print(f"- {path}", file=sys.stderr)
        print("\nAllowed prefixes:", file=sys.stderr)
        for prefix in ALLOWED_PREFIXES:
            print(f"- {prefix}", file=sys.stderr)
        return 1

    print("update-dedupe write surface OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
