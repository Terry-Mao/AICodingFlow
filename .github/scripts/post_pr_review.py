#!/usr/bin/env python3
"""Post review.json as a GitHub pull request review."""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


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


def normalize_comments(comments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for comment in comments:
        item = dict(comment)
        if "start_line" in item and "start_side" not in item:
            item["start_side"] = item["side"]
        normalized.append(item)
    return normalized


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review", default="review.json")
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
    comments = normalize_comments(review.get("comments") or [])
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
