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


def comment_has_agent_command(
    body: object,
    agent_login: str,
    command: str,
    *,
    allow_trailing_text: bool = False,
) -> bool:
    if not isinstance(body, str) or not body.strip() or not agent_login.strip():
        return False

    normalized_command = command.strip()
    if not normalized_command.startswith("/"):
        normalized_command = f"/{normalized_command}"
    expected = f"@{agent_login.strip()} {normalized_command}"
    in_fenced_code = False

    for line in body.splitlines():
        stripped_left = line.lstrip()
        if stripped_left.startswith(">"):
            continue
        if stripped_left.startswith("```"):
            in_fenced_code = not in_fenced_code
            continue
        if in_fenced_code:
            continue
        stripped = line.strip()
        if stripped == expected:
            return True
        if allow_trailing_text and stripped.startswith(f"{expected} "):
            return True

    return False


def comment_has_review_command(body: object, agent_login: str) -> bool:
    return comment_has_agent_command(body, agent_login, "/review")


def comment_has_fix_command(body: object, agent_login: str) -> bool:
    return comment_has_agent_command(body, agent_login, "/fix", allow_trailing_text=True)


def resolve_event(
    repo: str,
    event_name: str,
    event_path: Path,
    pr_number: str,
    agent_login: str = "",
) -> dict[str, Any]:
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
        comment_body = (event.get("comment") or {}).get("body", "")
        return {
            "pull_request": fetch_pr(repo, str(number)),
            "comment": {"body": comment_body},
            "review_command": comment_has_review_command(comment_body, agent_login),
        }

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
    is_open = state == "open"
    is_comment_review = event_name == "issue_comment" and event.get("review_command") is True
    if event_name == "workflow_dispatch":
        reviewable = is_open
    elif event_name == "issue_comment":
        reviewable = is_open and not draft and is_comment_review
    else:
        reviewable = is_open and not draft

    if not is_open:
        skip_reason = "closed"
    elif draft and event_name != "workflow_dispatch":
        skip_reason = "draft"
    elif event_name == "issue_comment" and not is_comment_review:
        skip_reason = "missing valid @AGENT_LOGIN /review command"
    else:
        skip_reason = ""

    return {
        "number": str(pr.get("number") or ""),
        "state": state,
        "base_sha": str(base.get("sha") or ""),
        "head_sha": str(head.get("sha") or ""),
        "draft": str(draft).lower(),
        "head_repo": head_repo,
        "reviewable": str(reviewable).lower(),
        "skip_reason": skip_reason,
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
    parser.add_argument("--agent-login", default="")
    parser.add_argument("--output", default="pr_event.json")
    parser.add_argument("--github-output", default="")
    args = parser.parse_args()

    output_path = Path(args.output).resolve()
    event = resolve_event(args.repo, args.event_name, Path(args.event_path), args.pr_number, args.agent_login)
    output_path.write_text(json.dumps(event), encoding="utf-8")

    state = review_state(event, args.repo, args.event_name)
    state["event_path"] = str(output_path)
    write_github_output(args.github_output, state)


if __name__ == "__main__":
    main()
