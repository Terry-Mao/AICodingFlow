#!/usr/bin/env python3
"""Prepare stable GitHub issue context for spec generation."""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path
from typing import Any

from artifact_contracts import load_json, write_github_output, write_json
from context_snapshot import flatten_pages, format_issue_comments, remove_triggering_comment
from github_api import fetch_default_branch, run_gh_json
from github_event import (
    actor_login,
    assignee_logins,
    event_action,
    event_assignee_login,
    event_comment_body as event_comment_body_from_event,
    event_label_name,
    is_pull_request_issue_event,
    label_names,
    triggering_comment_snapshot,
)

def spec_paths(issue_number: int) -> dict[str, str]:
    spec_dir = f"specs/issue-{issue_number}"
    branch = f"spec/issue-{issue_number}"
    return {
        "spec_dir": spec_dir,
        "product_spec": f"{spec_dir}/product.md",
        "tech_spec": f"{spec_dir}/tech.md",
        "branch_name": branch,
        "target_branch": branch,
    }


def extract_issue_number(args_issue: str, event_path: str | None) -> int:
    if args_issue:
        return int(args_issue.lstrip("#"))
    if not event_path:
        raise SystemExit("--issue or --event-path is required")
    event = load_event(event_path)
    issue = event.get("issue")
    if issue and issue.get("number"):
        return int(issue["number"])
    raise SystemExit("could not determine issue number from event")


def author_login(item: dict[str, Any]) -> str:
    return actor_login(item)


def fetch_issue(repo: str, issue_number: int) -> dict[str, Any]:
    return run_gh_json(
        [
            "issue",
            "view",
            str(issue_number),
            "--repo",
            repo,
            "--json",
            "number,title,body,author,labels,assignees,url,state",
        ]
    )


def fetch_comments(repo: str, issue_number: int) -> list[dict[str, Any]]:
    owner_repo = repo.strip()
    pages = run_gh_json(
        [
            "api",
            f"repos/{owner_repo}/issues/{issue_number}/comments?per_page=100",
            "--paginate",
            "--slurp",
        ]
    )
    return flatten_pages(pages)


def load_event(event_path: str | None) -> dict[str, Any]:
    return load_json(event_path, default={})


def event_comment_body(event_path: str | None) -> str:
    return event_comment_body_from_event(load_event(event_path))


def comment_mentions_login(comment: str, login: str) -> bool:
    if not login:
        return False
    visible_lines: list[str] = []
    fence_char = ""
    fence_width = 0
    fence_container_indent = 0
    paragraph_open = False
    list_content_indent = 0
    thematic_pattern = r" {0,3}(?:(?:\*[ \t]*){3,}|(?:-[ \t]*){3,}|(?:_[ \t]*){3,})"
    for line in comment.splitlines():
        expanded = line.expandtabs(4)
        indent = len(expanded) - len(expanded.lstrip(" "))
        if fence_char:
            closing = rf"^ {{0,3}}{re.escape(fence_char)}{{{fence_width},}}[ \t]*$"
            if indent >= fence_container_indent and re.match(closing, expanded[fence_container_indent:]):
                fence_char = ""
            continue
        if not line.strip():
            paragraph_open = False
            visible_lines.append("")
            continue
        if line.lstrip().startswith(">"):
            paragraph_open = False
            list_content_indent = 0
            continue
        if re.fullmatch(thematic_pattern, expanded):
            paragraph_open = False
            list_content_indent = 0
            continue
        list_item = re.match(r"^( {0,3})([-+*]|[0-9]{1,9}[.)])( +)", expanded)
        if list_item and paragraph_open:
            marker = list_item.group(2)
            if marker[0].isdigit() and int(marker[:-1]) != 1:
                list_item = None
        if list_item:
            padding = len(list_item.group(3))
            if padding > 4 or not expanded[list_item.end():].strip():
                padding = 1
            list_content_indent = len(list_item.group(1)) + len(list_item.group(2)) + padding
        elif indent < list_content_indent:
            list_content_indent = 0
        container_indent = list_content_indent if list_item or indent >= list_content_indent else 0
        content = expanded[container_indent:]
        opening = re.match(r"^ {0,3}(`{3,}|~{3,})", content)
        if opening:
            fence_char = opening.group(1)[0]
            fence_width = len(opening.group(1))
            fence_container_indent = container_indent
            paragraph_open = False
            continue
        setext = paragraph_open and re.fullmatch(r" {0,3}(?:=+|-+)[ \t]*", content)
        thematic = re.fullmatch(thematic_pattern, content)
        if setext or thematic:
            paragraph_open = False
            continue
        if list_item and len(content) - len(content.lstrip(" ")) >= 4:
            paragraph_open = False
            continue
        if indent >= 4:
            if not paragraph_open and (not list_content_indent or indent >= list_content_indent + 4):
                continue
            paragraph_open = True
        else:
            paragraph_open = not bool(re.match(r"^ {0,3}#{1,6}(?:[ \t]|$)", content))
        visible_lines.append(line)

    visible_comment = "\n".join(visible_lines)
    visible_comment = re.sub(r"(?<!`)(`+)(?!`)[\s\S]*?(?<!`)\1(?!`)", " ", visible_comment)
    pattern = re.compile(rf"(?<![A-Za-z0-9-])@{re.escape(login)}(?![A-Za-z0-9-])")
    return bool(pattern.search(visible_comment))


def triggering_comment(event_path: str | None) -> dict[str, Any] | None:
    return triggering_comment_snapshot(load_event(event_path))


def collect_coauthor_directives(*texts: str) -> list[str]:
    directives: list[str] = []
    seen: set[str] = set()
    pattern = re.compile(r"^\s*Co-authored-by:\s*.+<[^<>]+>\s*$", re.IGNORECASE)
    for text in texts:
        for line in (text or "").splitlines():
            directive = line.strip()
            key = directive.lower()
            if pattern.match(directive) and key not in seen:
                seen.add(key)
                directives.append(directive)
    return directives


def should_run(args: argparse.Namespace, issue: dict[str, Any]) -> tuple[bool, str]:
    event = load_event(args.event_path)
    if args.event_name == "issue_comment" and is_pull_request_issue_event(event):
        return False, "PR comments are handled by review-pr workflow"

    if args.force:
        return True, "forced"

    labels = set(label_names(issue))
    if "ready-to-implement" in labels:
        return False, "issue is already ready-to-implement"
    if "ready-to-spec" not in labels:
        return False, "issue is missing ready-to-spec"

    agent_login = args.agent_login.strip()
    if not agent_login:
        return False, "agent login is not configured"

    assignees = set(assignee_logins(issue))

    if args.event_name == "issues":
        action = event_action(event)
        if action == "labeled":
            if event_label_name(event) != "ready-to-spec":
                return False, "issue label event is not ready-to-spec"
            if agent_login not in assignees:
                return False, f"ready-to-spec issue is not assigned to {agent_login}"
            return True, f"ready-to-spec label added to issue assigned to {agent_login}"
        if action == "assigned":
            if event_assignee_login(event) != agent_login:
                return False, f"issue assignment event is not for {agent_login}"
            return True, f"ready-to-spec issue assigned to {agent_login}"
        return False, f"issue event action is not a spec trigger: {action or 'unknown'}"

    if args.event_name == "workflow_dispatch" and agent_login in assignees:
        return True, f"ready-to-spec assigned to {agent_login}"

    comment = (event.get("comment") or {}).get("body") or ""
    if args.event_name == "issue_comment" and comment_mentions_login(comment, agent_login):
        return True, f"ready-to-spec comment mentioned @{agent_login}"

    return False, "ready-to-spec issue is not assigned to or mentioning the configured agent"


def write_comments(path: Path, comments: list[dict[str, Any]]) -> None:
    path.write_text(format_issue_comments(comments), encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--issue", default="")
    parser.add_argument("--event-path", default=os.environ.get("GITHUB_EVENT_PATH", ""))
    parser.add_argument("--event-name", default=os.environ.get("GITHUB_EVENT_NAME", ""))
    parser.add_argument("--agent-login", default="")
    parser.add_argument("--output", default="issue_context.json")
    parser.add_argument("--comments-output", default="issue_comments.txt")
    parser.add_argument("--github-output", default=os.environ.get("GITHUB_OUTPUT", ""))
    parser.add_argument("--force", action="store_true")
    return parser.parse_args(argv)


def run(args: argparse.Namespace) -> None:
    issue_number = extract_issue_number(args.issue, args.event_path)
    issue = fetch_issue(args.repo, issue_number)
    comments = fetch_comments(args.repo, issue_number)
    default_branch = fetch_default_branch(args.repo)
    paths = spec_paths(issue_number)
    run, reason = should_run(args, issue)
    trigger_comment = triggering_comment(args.event_path)
    historical_comments = remove_triggering_comment(comments, trigger_comment)
    coauthor_directives = collect_coauthor_directives(
        issue.get("body") or "",
        *(comment.get("body") or "" for comment in comments),
    )

    context = {
        "issue": issue,
        "comments_count": len(comments),
        "historical_comments_count": len(historical_comments),
        "triggering_comment": trigger_comment,
        "default_branch": default_branch,
        **paths,
        "coauthor_directives": coauthor_directives,
        "should_run": run,
        "skip_reason": "" if run else reason,
        "trigger_reason": reason if run else "",
    }

    write_json(args.output, context)
    write_comments(Path(args.comments_output), historical_comments)
    write_github_output(
        args.github_output,
        {
            "should_run": "true" if run else "false",
            "skip_reason": reason,
            "issue_number": str(issue_number),
            "spec_dir": paths["spec_dir"],
            "product_spec": paths["product_spec"],
            "tech_spec": paths["tech_spec"],
            "branch_name": paths["branch_name"],
            "target_branch": paths["target_branch"],
            "default_branch": default_branch,
        },
    )


def main() -> None:
    run(parse_args())


if __name__ == "__main__":
    main()
