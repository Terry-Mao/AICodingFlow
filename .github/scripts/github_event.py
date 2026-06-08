"""Shared GitHub event field helpers for workflow context scripts."""

from __future__ import annotations

from typing import Any


def actor_login(item: dict[str, Any]) -> str:
    user = item.get("user") or item.get("author") or {}
    if not isinstance(user, dict):
        return ""
    return user.get("login") or ""


def label_names(issue: dict[str, Any]) -> list[str]:
    return [label.get("name", "") for label in issue.get("labels", []) if isinstance(label, dict) and label.get("name")]


def assignee_logins(issue: dict[str, Any]) -> list[str]:
    return [
        assignee.get("login", "")
        for assignee in issue.get("assignees", [])
        if isinstance(assignee, dict) and assignee.get("login")
    ]


def event_action(event: dict[str, Any]) -> str:
    return event.get("action") or ""


def event_issue(event: dict[str, Any]) -> dict[str, Any]:
    issue = event.get("issue")
    return issue if isinstance(issue, dict) else {}


def event_comment(event: dict[str, Any]) -> dict[str, Any]:
    comment = event.get("comment")
    return comment if isinstance(comment, dict) else {}


def event_comment_body(event: dict[str, Any]) -> str:
    return event_comment(event).get("body") or ""


def event_label_name(event: dict[str, Any]) -> str:
    label = event.get("label") or {}
    if not isinstance(label, dict):
        return ""
    return label.get("name") or ""


def event_assignee_login(event: dict[str, Any]) -> str:
    assignee = event.get("assignee") or {}
    if not isinstance(assignee, dict):
        return ""
    return assignee.get("login") or ""


def is_pull_request_issue_event(event: dict[str, Any]) -> bool:
    issue = event_issue(event)
    return "pull_request" in issue and issue.get("pull_request") is not None


def triggering_comment_snapshot(event: dict[str, Any], *, include_author_association: bool = False) -> dict[str, Any] | None:
    comment = event_comment(event)
    if not comment:
        return None
    snapshot = {
        "id": comment.get("id"),
        "author": actor_login(comment),
        "body": comment.get("body") or "",
        "created_at": comment.get("created_at") or "",
        "url": comment.get("html_url") or "",
    }
    if include_author_association:
        snapshot["author_association"] = comment.get("author_association") or ""
    return snapshot
