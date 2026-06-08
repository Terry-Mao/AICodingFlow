#!/usr/bin/env python3
"""Write the update-triage pull request body from environment data."""

from __future__ import annotations

import argparse
import os
from pathlib import Path


def build_body(reason: str, days: str, issue: str, repo: str, changed_files: str) -> str:
    files = [line.strip() for line in changed_files.splitlines() if line.strip()]
    file_lines = [f"- {path}" for path in files] or ["- Not captured"]
    return "\n".join(
        [
            "Updates repo-local triage guidance from recent maintainer triage corrections.",
            "",
            "Evidence summary:",
            reason,
            "",
            "Source:",
            f"- days: {days}",
            f"- issue: {issue}",
            f"- repo: {repo}",
            "",
            "Changed files:",
            *file_lines,
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    body = build_body(
        reason=os.environ["GUIDANCE_REASON"],
        days=os.environ["SOURCE_DAYS"],
        issue=os.environ["SOURCE_ISSUE"],
        repo=os.environ["SOURCE_REPO"],
        changed_files=os.environ.get("CHANGED_FILES", ""),
    )
    Path(args.output).write_text(body, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
