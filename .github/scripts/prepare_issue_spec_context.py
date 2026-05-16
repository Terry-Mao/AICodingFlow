#!/usr/bin/env python3
"""Prepare stable GitHub issue context for spec generation."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any


def run_gh_json(args: list[str]) -> Any:
    result = subprocess.run(
        ["gh", *args],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    return json.loads(result.stdout)


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
    event = json.loads(Path(event_path).read_text(encoding="utf-8"))
    issue = event.get("issue")
    if issue and issue.get("number"):
        return int(issue["number"])
    raise SystemExit("could not determine issue number from event")


def author_login(item: dict[str, Any]) -> str:
    user = item.get("user") or {}
    return user.get("login") or ""


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
    if pages and all(isinstance(page, list) for page in pages):
        return [comment for page in pages for comment in page]
    if isinstance(pages, list):
        return pages
    raise SystemExit("unexpected gh api comments response")


def fetch_default_branch(repo: str) -> str:
    repository = run_gh_json(["repo", "view", repo, "--json", "defaultBranchRef"])
    default_branch = (repository.get("defaultBranchRef") or {}).get("name")
    if not default_branch:
        raise SystemExit("could not determine default branch")
    return default_branch


def label_names(issue: dict[str, Any]) -> list[str]:
    return [label.get("name", "") for label in issue.get("labels", []) if label.get("name")]


def assignee_logins(issue: dict[str, Any]) -> list[str]:
    return [assignee.get("login", "") for assignee in issue.get("assignees", []) if assignee.get("login")]


def load_event(event_path: str | None) -> dict[str, Any]:
    if not event_path:
        return {}
    return json.loads(Path(event_path).read_text(encoding="utf-8"))


def event_action(event: dict[str, Any]) -> str:
    return event.get("action") or ""


def event_label_name(event: dict[str, Any]) -> str:
    label = event.get("label") or {}
    return label.get("name") or ""


def event_assignee_login(event: dict[str, Any]) -> str:
    assignee = event.get("assignee") or {}
    return assignee.get("login") or ""


def event_comment_body(event_path: str | None) -> str:
    event = load_event(event_path)
    comment = event.get("comment") or {}
    return comment.get("body") or ""


def is_pull_request_issue_event(event: dict[str, Any]) -> bool:
    issue = event.get("issue") or {}
    return bool(issue.get("pull_request"))


def comment_mentions_login(comment: str, login: str) -> bool:
    if not login:
        return False
    visible_lines = [line for line in comment.splitlines() if not line.lstrip().startswith(">")]
    visible_comment = "\n".join(visible_lines)
    pattern = re.compile(rf"(?<![A-Za-z0-9-])@{re.escape(login)}(?![A-Za-z0-9-])")
    return bool(pattern.search(visible_comment))


def triggering_comment(event_path: str | None) -> dict[str, Any] | None:
    event = load_event(event_path)
    comment = event.get("comment")
    if not comment:
        return None
    return {
        "id": comment.get("id"),
        "author": author_login(comment),
        "body": comment.get("body") or "",
        "created_at": comment.get("created_at") or "",
        "url": comment.get("html_url") or "",
    }


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
    lines: list[str] = []
    for comment in comments:
        lines.extend(
            [
                f"Author: {author_login(comment)}",
                f"Created: {comment.get('created_at') or ''}",
                "",
                comment.get("body") or "",
                "",
                "---",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_github_output(path: str | None, values: dict[str, str]) -> None:
    if not path:
        return
    with Path(path).open("a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def main() -> None:
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
    args = parser.parse_args()

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

    Path(args.output).write_text(json.dumps(context, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
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


if __name__ == "__main__":
    main()
