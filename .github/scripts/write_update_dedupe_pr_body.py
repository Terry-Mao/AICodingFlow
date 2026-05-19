#!/usr/bin/env python3
"""Write the update-dedupe pull request body from environment data."""

from __future__ import annotations

import argparse
import os
from pathlib import Path


def build_body(reason: str, days: str, issue: str, repo: str) -> str:
    return "\n".join(
        [
            "Updates repo-local dedupe guidance from recent maintainer duplicate closures.",
            "",
            "Evidence summary:",
            reason,
            "",
            "Source:",
            f"- days: {days}",
            f"- issue: {issue}",
            f"- repo: {repo}",
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
    )
    Path(args.output).write_text(body, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
