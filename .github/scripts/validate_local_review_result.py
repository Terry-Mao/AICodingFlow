#!/usr/bin/env python3
"""Validate that local review did not mutate repository files."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ALLOWED_PATHS = {
    "pr_description.txt",
    "pr_diff.txt",
    "spec_context.md",
    "review.json",
}


def parse_status_records(raw: bytes) -> list[tuple[str, str, str]]:
    parts = raw.decode("utf-8", errors="replace").split("\0")
    records: list[tuple[str, str, str]] = []
    index = 0
    while index < len(parts):
        entry = parts[index]
        index += 1
        if not entry:
            continue
        status = entry[:2]
        path = entry[3:]
        if ("R" in status or "C" in status) and index < len(parts):
            # porcelain v1 -z emits destination first, then source.
            index += 1
        records.append((status[0], status[1], path))
    return records


def validate_records(records: list[tuple[str, str, str]]) -> list[str]:
    errors: list[str] = []
    for index_status, worktree_status, path in records:
        normalized = Path(path).as_posix()
        if index_status != " " and index_status != "?":
            errors.append(f"staged change is not allowed during local review: {normalized}")
            continue
        if normalized not in ALLOWED_PATHS:
            errors.append(f"unexpected file change during local review: {normalized}")
            continue
        if worktree_status == "D":
            errors.append(f"local review output was deleted unexpectedly: {normalized}")
    return errors


def git_status_records() -> list[tuple[str, str, str]]:
    result = subprocess.run(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        check=True,
        stdout=subprocess.PIPE,
    )
    return parse_status_records(result.stdout)


def main() -> int:
    errors = validate_records(git_status_records())
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
