#!/usr/bin/env python3
"""Prepare stable GitHub issue context for implementation generation."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from write_spec_context import (  # noqa: E402
    APPROVED_LABEL,
    collect_spec_entries,
    fetch_spec_prs,
    format_spec_context_text,
    label_names as pr_label_names,
    spec_file_paths,
    spec_pr_summary,
)


READY_LABEL = "ready-to-implement"
IMPLEMENT_BRANCH_PREFIX = "spec/implement-issue"


def run_gh_json(args: list[str]) -> Any:
    result = subprocess.run(["gh", *args], check=True, stdout=subprocess.PIPE, text=True)
    return json.loads(result.stdout)


def flatten_pages(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list) and value and all(isinstance(page, list) for page in value):
        return [item for page in value for item in page]
    if isinstance(value, list):
        return value
    raise SystemExit("unexpected GitHub API response")


def load_event(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    return json.loads(Path(path).read_text(encoding="utf-8"))


def author_login(item: dict[str, Any]) -> str:
    user = item.get("user") or item.get("author") or {}
    return user.get("login") or ""


def label_names(issue: dict[str, Any]) -> list[str]:
    return [label.get("name", "") for label in issue.get("labels", []) if label.get("name")]


def assignee_logins(issue: dict[str, Any]) -> list[str]:
    return [assignee.get("login", "") for assignee in issue.get("assignees", []) if assignee.get("login")]


def comment_mentions_login(comment: str, login: str) -> bool:
    if not login:
        return False
    visible_lines = [line for line in comment.splitlines() if not line.lstrip().startswith(">")]
    visible_comment = "\n".join(visible_lines)
    pattern = re.compile(rf"(?<![A-Za-z0-9-])@{re.escape(login)}(?![A-Za-z0-9-])")
    return bool(pattern.search(visible_comment))


def event_comment_body(event: dict[str, Any]) -> str:
    comment = event.get("comment") or {}
    return comment.get("body") or ""


def is_pull_request_issue_event(event: dict[str, Any]) -> bool:
    issue = event.get("issue") or {}
    return bool(issue.get("pull_request"))


def event_action(event: dict[str, Any]) -> str:
    return event.get("action") or ""


def event_label_name(event: dict[str, Any]) -> str:
    label = event.get("label") or {}
    return label.get("name") or ""


def event_assignee_login(event: dict[str, Any]) -> str:
    assignee = event.get("assignee") or {}
    return assignee.get("login") or ""


def triggering_comment(event: dict[str, Any]) -> dict[str, Any] | None:
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
    pages = run_gh_json(
        [
            "api",
            f"repos/{repo}/issues/{issue_number}/comments?per_page=100",
            "--paginate",
            "--slurp",
        ]
    )
    return flatten_pages(pages)


def fetch_default_branch(repo: str) -> str:
    repository = run_gh_json(["repo", "view", repo, "--json", "defaultBranchRef"])
    default_branch = (repository.get("defaultBranchRef") or {}).get("name")
    if not default_branch:
        raise SystemExit("could not determine default branch")
    return default_branch


def extract_issue_number(args_issue: str, event: dict[str, Any]) -> int:
    if args_issue:
        return int(args_issue.lstrip("#"))
    issue = event.get("issue")
    if issue and issue.get("number"):
        return int(issue["number"])
    raise SystemExit("could not determine issue number from input")


def should_run(args: argparse.Namespace, event: dict[str, Any], issue: dict[str, Any]) -> tuple[bool, str]:
    if args.event_name == "issue_comment" and is_pull_request_issue_event(event):
        return False, "PR comments are handled by review-pr workflow"

    labels = set(label_names(issue))
    if READY_LABEL not in labels:
        return False, f"issue is missing {READY_LABEL}"

    agent_login = args.agent_login.strip()
    if not agent_login:
        return False, "agent login is not configured"

    assignees = set(assignee_logins(issue))

    if args.event_name == "issues":
        action = event_action(event)
        if action == "labeled":
            if event_label_name(event) != READY_LABEL:
                return False, f"issue label event is not {READY_LABEL}"
            if agent_login not in assignees:
                return False, f"{READY_LABEL} issue is not assigned to {agent_login}"
            return True, f"{READY_LABEL} label added to issue assigned to {agent_login}"
        if action == "assigned":
            if event_assignee_login(event) != agent_login:
                return False, f"issue assignment event is not for {agent_login}"
            return True, f"{READY_LABEL} issue assigned to {agent_login}"
        return False, f"issue event action is not an implementation trigger: {action or 'unknown'}"

    if args.event_name == "workflow_dispatch" and agent_login in assignees:
        return True, f"{READY_LABEL} assigned to {agent_login}"

    if args.event_name == "issue_comment" and comment_mentions_login(event_comment_body(event), agent_login):
        return True, f"{READY_LABEL} comment mentioned @{agent_login}"

    return False, f"{READY_LABEL} issue is not assigned to or mentioning the configured agent"


def implementation_target_branch(issue_number: int) -> str:
    return f"{IMPLEMENT_BRANCH_PREFIX}-{issue_number}"


def resolve_implementation_spec_context(repo: str, issue_number: int, default_branch: str) -> dict[str, Any]:
    paths = spec_file_paths(issue_number)
    spec_prs = fetch_spec_prs(repo, issue_number)
    approved = [spec_pr_summary(pr, paths) for pr in spec_prs if APPROVED_LABEL in pr_label_names(pr)]
    unapproved = [spec_pr_summary(pr, paths) for pr in spec_prs if APPROVED_LABEL not in pr_label_names(pr)]
    approved.sort(key=lambda item: item["updated_at"], reverse=True)
    unapproved.sort(key=lambda item: item["updated_at"], reverse=True)
    context: dict[str, Any] = {
        "issue_number": issue_number,
        "spec_context_source": "",
        "selected_spec_pr": None,
        "approved_spec_prs": approved,
        "unapproved_spec_prs": unapproved,
        "spec_entries": [],
        "changed_files": [],
        "pr_files": [],
    }

    if approved:
        selected = approved[0]
        entries = collect_spec_entries(
            selected["head_repo_full_name"],
            paths,
            selected["head_ref_name"],
        )
        if entries:
            context["spec_context_source"] = "approved-pr"
            context["selected_spec_pr"] = selected
            context["spec_entries"] = entries
            return context

    entries = collect_spec_entries(repo, paths, default_branch)
    if entries:
        context["spec_context_source"] = "directory"
        context["spec_entries"] = entries
    return context


def has_existing_implementation_pr(repo: str, branch_name: str) -> bool:
    owner = repo.split("/", 1)[0]
    pages = run_gh_json(
        [
            "api",
            f"repos/{repo}/pulls?state=open&head={owner}:{branch_name}&per_page=100",
            "--paginate",
            "--slurp",
        ]
    )
    return bool(flatten_pages(pages))


def best_effort_assign(repo: str, issue_number: int, agent_login: str) -> str:
    if not agent_login:
        return ""
    try:
        subprocess.run(
            ["gh", "issue", "edit", str(issue_number), "--repo", repo, "--add-assignee", agent_login],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        return (exc.stderr or str(exc)).strip()
    return ""


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


def build_skipped_context(reason: str) -> dict[str, Any]:
    return {
        "owner": "",
        "repo": "",
        "repository": "",
        "issue_number": None,
        "requester": "",
        "issue_title": "",
        "issue_labels": [],
        "issue_assignees": [],
        "issue_url": "",
        "default_branch": "",
        "target_branch": "",
        "implementation_branch_prefix": "",
        "spec_context_source": "",
        "selected_spec_pr_number": None,
        "selected_spec_pr_url": "",
        "selected_spec_pr": None,
        "approved_spec_prs": [],
        "unapproved_spec_prs": [],
        "spec_entries": [],
        "spec_context_text": "",
        "has_existing_implementation_pr": False,
        "comments_count": 0,
        "historical_comments_count": 0,
        "triggering_comment": None,
        "coauthor_directives": [],
        "skill_paths": [
            ".agents/skills/implement-specs/SKILL.md",
            ".agents/skills/spec-driven-implementation/SKILL.md",
            ".agents/skills/implement-issue/SKILL.md",
        ],
        "progress_start_line": "",
        "should_run": False,
        "should_noop": False,
        "skip_reason": reason,
        "noop_reason": "",
        "trigger_reason": "",
        "assignment_warning": "",
    }


def write_skipped_outputs(args: argparse.Namespace, reason: str) -> None:
    Path(args.output).write_text(json.dumps(build_skipped_context(reason), indent=2) + "\n", encoding="utf-8")
    Path(args.comments_output).write_text("", encoding="utf-8")
    spec_output = Path(args.spec_context_output)
    if spec_output.exists():
        spec_output.unlink()
    write_github_output(
        args.github_output,
        {
            "should_run": "false",
            "should_noop": "false",
            "skip_reason": reason,
            "noop_reason": "",
            "issue_number": "",
            "default_branch": "",
            "target_branch": "",
            "spec_context_source": "",
            "selected_spec_pr_number": "",
            "has_existing_implementation_pr": "false",
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--issue", default="")
    parser.add_argument("--event-path", default=os.environ.get("GITHUB_EVENT_PATH", ""))
    parser.add_argument("--event-name", default=os.environ.get("GITHUB_EVENT_NAME", ""))
    parser.add_argument("--agent-login", default="")
    parser.add_argument("--output", default="issue_context.json")
    parser.add_argument("--comments-output", default="issue_comments.txt")
    parser.add_argument("--spec-context-output", default="spec_context.md")
    parser.add_argument("--github-output", default=os.environ.get("GITHUB_OUTPUT", ""))
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    event = load_event(args.event_path)

    issue_number = extract_issue_number(args.issue, event)
    issue = fetch_issue(args.repo, issue_number)
    comments = fetch_comments(args.repo, issue_number)
    default_branch = fetch_default_branch(args.repo)
    run, reason = should_run(args, event, issue)
    trigger_comment = triggering_comment(event)
    historical_comments = remove_triggering_comment(comments, trigger_comment)
    spec_context = resolve_implementation_spec_context(args.repo, issue_number, default_branch)
    spec_context_text = format_spec_context_text(spec_context) if spec_context.get("spec_entries") else ""
    selected_spec_pr = spec_context.get("selected_spec_pr") or {}
    target_branch = selected_spec_pr.get("head_ref_name") or implementation_target_branch(issue_number)
    noop = bool(spec_context.get("unapproved_spec_prs")) and not spec_context.get("spec_entries")
    noop_reason = (
        "linked spec PR(s) exist for this issue but none are labeled plan-approved"
        if noop
        else ""
    )
    assignment_warning = best_effort_assign(args.repo, issue_number, args.agent_login.strip()) if run else ""
    coauthor_directives = collect_coauthor_directives(
        issue.get("body") or "",
        *(comment.get("body") or "" for comment in comments),
    )
    existing_pr = has_existing_implementation_pr(args.repo, target_branch) if run and not selected_spec_pr else False

    context = {
        "owner": args.repo.split("/", 1)[0],
        "repo": args.repo.split("/", 1)[1] if "/" in args.repo else args.repo,
        "repository": args.repo,
        "issue_number": issue_number,
        "requester": author_login(issue),
        "issue_title": issue.get("title") or "",
        "issue_labels": label_names(issue),
        "issue_assignees": assignee_logins(issue),
        "issue_url": issue.get("url") or "",
        "default_branch": default_branch,
        "target_branch": target_branch,
        "implementation_branch_prefix": implementation_target_branch(issue_number),
        "spec_context_source": spec_context.get("spec_context_source") or "",
        "selected_spec_pr_number": selected_spec_pr.get("number"),
        "selected_spec_pr_url": selected_spec_pr.get("url") or "",
        "selected_spec_pr": spec_context.get("selected_spec_pr"),
        "approved_spec_prs": spec_context.get("approved_spec_prs") or [],
        "unapproved_spec_prs": spec_context.get("unapproved_spec_prs") or [],
        "spec_entries": spec_context.get("spec_entries") or [],
        "spec_context_text": spec_context_text,
        "has_existing_implementation_pr": existing_pr,
        "comments_count": len(comments),
        "historical_comments_count": len(historical_comments),
        "triggering_comment": trigger_comment,
        "coauthor_directives": coauthor_directives,
        "skill_paths": [
            ".agents/skills/implement-specs/SKILL.md",
            ".agents/skills/spec-driven-implementation/SKILL.md",
            ".agents/skills/implement-issue/SKILL.md",
        ],
        "progress_start_line": f"Implementation run started for issue #{issue_number}.",
        "should_run": run,
        "should_noop": noop,
        "skip_reason": "" if run else reason,
        "noop_reason": noop_reason,
        "trigger_reason": reason if run else "",
        "assignment_warning": assignment_warning,
    }

    Path(args.output).write_text(json.dumps(context, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_comments(Path(args.comments_output), historical_comments)
    spec_output = Path(args.spec_context_output)
    if spec_context_text:
        spec_output.write_text(spec_context_text, encoding="utf-8")
    elif spec_output.exists():
        spec_output.unlink()
    write_github_output(
        args.github_output,
        {
            "should_run": "true" if run else "false",
            "should_noop": "true" if noop else "false",
            "skip_reason": "" if run else reason,
            "noop_reason": noop_reason,
            "issue_number": str(issue_number),
            "default_branch": default_branch,
            "target_branch": target_branch,
            "spec_context_source": str(context["spec_context_source"]),
            "selected_spec_pr_number": str(context["selected_spec_pr_number"] or ""),
            "has_existing_implementation_pr": "true" if existing_pr else "false",
        },
    )


if __name__ == "__main__":
    main()
