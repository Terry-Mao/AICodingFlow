#!/usr/bin/env python3
"""Resolve a pull request event payload for AI review workflows."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from markdown_it import MarkdownIt

from artifact_contracts import write_github_output


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

    def matches_command(line: str) -> bool:
        return line == expected or (allow_trailing_text and line.startswith(f"{expected} "))

    source_lines = body.splitlines()
    container_depth = 0
    in_top_level_paragraph = False

    for block in MarkdownIt("commonmark").parse(body):
        if block.type in {"blockquote_open", "bullet_list_open", "ordered_list_open"}:
            container_depth += 1
        elif block.type in {"blockquote_close", "bullet_list_close", "ordered_list_close"}:
            container_depth -= 1
        elif block.type == "paragraph_open":
            in_top_level_paragraph = container_depth == 0
        elif block.type == "paragraph_close":
            in_top_level_paragraph = False
        elif block.type == "inline" and in_top_level_paragraph and block.map:
            visible_lines = [""]
            for inline in block.children or []:
                if inline.type == "text":
                    parts = inline.content.split("\n")
                    visible_lines[-1] += parts[0]
                    visible_lines.extend(parts[1:])
                elif inline.type in {"softbreak", "hardbreak"}:
                    visible_lines.append("")
                else:
                    visible_lines[-1] += "\0"
            paragraph_lines = source_lines[block.map[0] : block.map[1]]
            if len(visible_lines) != len(paragraph_lines):
                continue
            for source, visible in zip(paragraph_lines, visible_lines):
                indent = source[: len(source) - len(source.lstrip(" \t"))]
                if len(indent.expandtabs(4)) >= 4:
                    continue
                if matches_command(source.strip()) and matches_command(visible.strip()):
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
    if event_name in {"pull_request", "pull_request_target"}:
        event = load_json(event_path)
        if "pull_request" not in event:
            raise SystemExit(f"{event_name} event payload is missing pull_request")
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
    is_same_repo_entry = event_name not in {"pull_request_target", "issue_comment"} or head_repo == repo
    is_comment_review = event_name == "issue_comment" and event.get("review_command") is True
    if event_name == "workflow_dispatch":
        reviewable = is_open
    elif event_name == "issue_comment":
        reviewable = is_open and not draft and is_comment_review and is_same_repo_entry
    else:
        reviewable = is_open and not draft and is_same_repo_entry

    if not is_open:
        skip_reason = "closed"
    elif draft and event_name != "workflow_dispatch":
        skip_reason = "draft"
    elif event_name in {"pull_request_target", "issue_comment"} and not is_same_repo_entry:
        skip_reason = "head repository is not the current repository"
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
