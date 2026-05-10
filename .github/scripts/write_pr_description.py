#!/usr/bin/env python3
"""Write a stable pull request description snapshot from GITHUB_EVENT_PATH."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="pr_description.txt")
    args = parser.parse_args()

    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        raise SystemExit("GITHUB_EVENT_PATH is not set")

    event = json.loads(Path(event_path).read_text(encoding="utf-8"))
    pr = event["pull_request"]
    base = pr["base"]
    head = pr["head"]

    text = "\n".join(
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

    Path(args.output).write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
