"""Shared stable context snapshot helpers."""

from __future__ import annotations

from typing import Any

from github_event import actor_login


def flatten_pages(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list) and value and all(isinstance(page, list) for page in value):
        return [item for page in value for item in page]
    if isinstance(value, list):
        return value
    raise SystemExit("unexpected GitHub API response")


def remove_triggering_comment(
    comments: list[dict[str, Any]],
    trigger_comment: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not trigger_comment:
        return comments
    trigger_id = trigger_comment.get("id")
    trigger_url = trigger_comment.get("url")
    filtered: list[dict[str, Any]] = []
    for comment in comments:
        if trigger_id is not None and comment.get("id") == trigger_id:
            continue
        if trigger_url and comment.get("html_url") == trigger_url:
            continue
        filtered.append(comment)
    return filtered


def format_issue_comments(comments: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for comment in comments:
        lines.extend(
            [
                f"Author: {actor_login(comment)}",
                f"Created: {comment.get('created_at') or ''}",
                "",
                comment.get("body") or "",
                "",
                "---",
                "",
            ]
        )
    return "\n".join(lines)
