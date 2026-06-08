#!/usr/bin/env python3
"""Validate that local review did not mutate repository files."""

from __future__ import annotations

import subprocess
import sys
import argparse
from pathlib import Path


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
        errors.append(f"unexpected file change during local review: {normalized}")
    return errors


def status_records_by_path(records: list[tuple[str, str, str]]) -> dict[str, tuple[str, str]]:
    result: dict[str, tuple[str, str]] = {}
    for index_status, worktree_status, path in records:
        normalized = Path(path).as_posix()
        result[normalized] = (index_status, worktree_status)
    return result


def validate_records_against_baseline(
    records: list[tuple[str, str, str]], baseline_records: list[tuple[str, str, str]]
) -> list[str]:
    errors: list[str] = []
    current_status = status_records_by_path(records)
    baseline_status = status_records_by_path(baseline_records)

    for path in sorted(set(current_status) - set(baseline_status)):
        errors.append(f"unexpected file change during local review: {path}")
    for path in sorted(set(baseline_status) - set(current_status)):
        errors.append(f"baseline file state changed during local review: {path}")
    for path in sorted(set(current_status) & set(baseline_status)):
        if current_status[path] != baseline_status[path]:
            errors.append(f"baseline file state changed during local review: {path}")
    return errors


def git_status_records() -> list[tuple[str, str, str]]:
    result = subprocess.run(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        check=True,
        stdout=subprocess.PIPE,
    )
    return parse_status_records(result.stdout)


def read_baseline_records(path: str) -> list[tuple[str, str, str]]:
    return parse_status_records(Path(path).read_bytes())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-status", default="")
    args = parser.parse_args()

    records = git_status_records()
    if args.baseline_status:
        errors = validate_records_against_baseline(records, read_baseline_records(args.baseline_status))
        Path(args.baseline_status).unlink(missing_ok=True)
    else:
        errors = validate_records(records)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
