#!/usr/bin/env python3
"""Write a stable pull request description snapshot from GITHUB_EVENT_PATH."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def format_pr_description(event: dict) -> str:
    if "pull_request" not in event:
        raise SystemExit("event payload is missing pull_request")
    pr = event["pull_request"]
    base = pr["base"]
    head = pr["head"]

    return "\n".join(
        [
            f"Title: {pr.get('title') or ''}",
            f"Number: {pr.get('number')}",
            f"Author: {pr.get('user', {}).get('login') or ''}",
            f"Base: {base.get('ref')} @ {base.get('sha')}",
            f"Head: {head.get('ref')} @ {head.get('sha')}",
            f"URL: {pr.get('html_url') or ''}",
            "",
            "Body:",
            pr.get("body") or "",
            "",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event-path", default="")
    parser.add_argument("--output", default="pr_description.txt")
    args = parser.parse_args()

    event_path = args.event_path or os.environ.get("PR_EVENT_PATH") or os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        raise SystemExit("--event-path, PR_EVENT_PATH, or GITHUB_EVENT_PATH is required")

    text = format_pr_description(json.loads(Path(event_path).read_text(encoding="utf-8")))

    Path(args.output).write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
