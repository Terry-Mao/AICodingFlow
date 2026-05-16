#!/usr/bin/env python3
"""Resolve a pull request event payload for AI review workflows."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def fetch_pr(repo: str, pr_number: str) -> dict[str, Any]:
    return json.loads(
        subprocess.check_output(
            ["gh", "api", f"repos/{repo}/pulls/{pr_number}"],
            text=True,
        )
    )


def resolve_event(repo: str, event_name: str, event_path: Path, pr_number: str) -> dict[str, Any]:
    if event_name == "pull_request":
        event = load_json(event_path)
        if "pull_request" not in event:
            raise SystemExit("pull_request event payload is missing pull_request")
        return event

    if event_name == "issue_comment":
        event = load_json(event_path)
        issue = event.get("issue") or {}
        if not issue.get("pull_request"):
            raise SystemExit("issue_comment event is not for a pull request")
        number = issue.get("number")
        if not number:
            raise SystemExit("issue_comment event payload is missing issue number")
        return {"pull_request": fetch_pr(repo, str(number))}

    if event_name == "workflow_dispatch":
        if not pr_number:
            raise SystemExit("pr_number is required for workflow_dispatch")
        return {"pull_request": fetch_pr(repo, pr_number)}

    raise SystemExit(f"unsupported event_name: {event_name}")


def review_state(event: dict[str, Any], repo: str, event_name: str = "") -> dict[str, str]:
    pr = event["pull_request"]
    head = pr.get("head") or {}
    base = pr.get("base") or {}
    head_repo = (head.get("repo") or {}).get("full_name") or ""
    draft = bool(pr.get("draft"))
    state = str(pr.get("state") or "").lower()
    manual_comment_trigger = event_name == "issue_comment"
    reviewable = (manual_comment_trigger or not draft) and state == "open"

    return {
        "number": str(pr.get("number") or ""),
        "state": state,
        "base_sha": str(base.get("sha") or ""),
        "head_sha": str(head.get("sha") or ""),
        "draft": str(draft).lower(),
        "head_repo": head_repo,
        "reviewable": str(reviewable).lower(),
    }


def write_github_output(path: str | None, values: dict[str, str]) -> None:
    if not path:
        return
    with Path(path).open("a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--event-name", required=True)
    parser.add_argument("--event-path", required=True)
    parser.add_argument("--pr-number", default="")
    parser.add_argument("--output", default="pr_event.json")
    parser.add_argument("--github-output", default="")
    args = parser.parse_args()

    output_path = Path(args.output).resolve()
    event = resolve_event(args.repo, args.event_name, Path(args.event_path), args.pr_number)
    output_path.write_text(json.dumps(event), encoding="utf-8")

    state = review_state(event, args.repo, args.event_name)
    state["event_path"] = str(output_path)
    write_github_output(args.github_output, state)


if __name__ == "__main__":
    main()
