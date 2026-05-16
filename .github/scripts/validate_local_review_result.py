#!/usr/bin/env python3
"""Validate that local review did not mutate repository files."""

from __future__ import annotations

import subprocess
import sys
import argparse
from pathlib import Path


ALLOWED_PATHS = {
    "pr_description.txt",
    "pr_diff.txt",
    "spec_context.md",
    "review.json",
    ".local_review_baseline.status",
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


def business_records(records: list[tuple[str, str, str]]) -> dict[str, tuple[str, str]]:
    result: dict[str, tuple[str, str]] = {}
    for index_status, worktree_status, path in records:
        normalized = Path(path).as_posix()
        if normalized not in ALLOWED_PATHS:
            result[normalized] = (index_status, worktree_status)
    return result


def validate_records_against_baseline(
    records: list[tuple[str, str, str]], baseline_records: list[tuple[str, str, str]]
) -> list[str]:
    errors = validate_records([record for record in records if Path(record[2]).as_posix() in ALLOWED_PATHS])
    current_business = business_records(records)
    baseline_business = business_records(baseline_records)

    for path in sorted(set(current_business) - set(baseline_business)):
        errors.append(f"unexpected file change during local review: {path}")
    for path in sorted(set(baseline_business) - set(current_business)):
        errors.append(f"baseline file state changed during local review: {path}")
    for path in sorted(set(current_business) & set(baseline_business)):
        if current_business[path] != baseline_business[path]:
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
