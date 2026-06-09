#!/usr/bin/env python3
"""Write the update-triage pull request body from environment data."""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path


CLOSING_KEYWORD_RE = re.compile(
    r"\b(close[sd]?|fix(?:e[sd])?|resolve[sd]?)(\s+)(?="
    r"(?:https?://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/issues/\d+"
    r"|[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+#\d+"
    r"|#\d+))",
    flags=re.IGNORECASE,
)


def neutralize_closing_keywords(text: str) -> str:
    return CLOSING_KEYWORD_RE.sub(r"\1 issue ", text)


def build_body(reason: str, days: str, issue: str, repo: str, changed_files: str) -> str:
    files = [line.strip() for line in changed_files.splitlines() if line.strip()]
    file_lines = [f"- {path}" for path in files] or ["- Not captured"]
    safe_reason = neutralize_closing_keywords(reason)
    return "\n".join(
        [
            "Updates repo-local triage guidance from recent maintainer triage corrections.",
            "",
            "Evidence summary:",
            safe_reason,
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
