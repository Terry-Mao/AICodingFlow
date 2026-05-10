#!/usr/bin/env python3
"""Post review.json as a GitHub pull request review."""

from __future__ import annotations

import argparse
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


FILE_RE = re.compile(r"^FILE\s+(.+?)\s*$")
LINE_RE = re.compile(r"^(LEFT|RIGHT|BOTH)\s+(\d+)\s+\|")


def load_event() -> dict[str, Any]:
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        raise SystemExit("GITHUB_EVENT_PATH is not set")
    return json.loads(Path(event_path).read_text(encoding="utf-8"))


def request_json(url: str, token: str, payload: dict[str, Any]) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"GitHub API request failed: {exc.code} {detail}") from exc


def parse_diff_positions(path: Path) -> dict[tuple[str, str, int], int]:
    positions: dict[tuple[str, str, int], int] = {}
    current_file: str | None = None
    position = 0
    saw_hunk = False

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        file_match = FILE_RE.match(raw_line)
        if file_match:
            current_file = file_match.group(1).strip()
            position = 0
            saw_hunk = False
            continue

        if raw_line == "END_FILE":
            current_file = None
            saw_hunk = False
            continue

        if raw_line.startswith("HUNK "):
            if saw_hunk:
                position += 1
            saw_hunk = True
            continue

        line_match = LINE_RE.match(raw_line)
        if not line_match or current_file is None or not saw_hunk:
            continue

        position += 1
        side, number_text = line_match.groups()
        if side != "BOTH":
            positions[(current_file, side, int(number_text))] = position

    return positions


def normalize_comments(
    comments: list[dict[str, Any]],
    positions: dict[tuple[str, str, int], int],
) -> list[dict[str, Any]]:
    normalized = []
    for comment in comments:
        key = (comment["path"], comment["side"], comment["line"])
        position = positions.get(key)
        if position is None:
            raise SystemExit(f"comment target is missing from diff positions: {key[0]}/{key[1]}/{key[2]}")
        normalized.append(
            {
                "path": comment["path"],
                "position": position,
                "body": comment["body"],
            }
        )
    return normalized


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review", default="review.json")
    parser.add_argument("--diff", default="pr_diff.txt")
    args = parser.parse_args()

    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not token:
        raise SystemExit("GITHUB_TOKEN is not set")
    if not repo:
        raise SystemExit("GITHUB_REPOSITORY is not set")

    event = load_event()
    pr = event["pull_request"]
    review = json.loads(Path(args.review).read_text(encoding="utf-8"))

    body = review.get("body") or ""
    raw_comments = review.get("comments") or []
    comments = []
    if raw_comments:
        positions = parse_diff_positions(Path(args.diff))
        comments = normalize_comments(raw_comments, positions)
    if not body and not comments:
        print("review.json has no body or comments; skipping PR review")
        return

    payload = {
        "event": "COMMENT",
        "commit_id": pr["head"]["sha"],
        "body": body,
        "comments": comments,
    }
    url = f"https://api.github.com/repos/{repo}/pulls/{pr['number']}/reviews"
    response = request_json(url, token, payload)
    print(f"Posted PR review {response.get('id')}")


if __name__ == "__main__":
    main()
