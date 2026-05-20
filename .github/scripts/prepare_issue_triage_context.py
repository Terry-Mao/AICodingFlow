#!/usr/bin/env python3
"""Prepare stable GitHub issue context for issue triage."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


TRUSTED_COMMENT_ASSOCIATIONS = {"OWNER", "MEMBER", "COLLABORATOR"}
NEEDS_INFO_LABEL = "needs-info"


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


def extract_issue_number(args_issue: str, event: dict[str, Any]) -> int:
    if args_issue:
        return int(args_issue.lstrip("#"))
    issue = event.get("issue")
    if issue and issue.get("number"):
        return int(issue["number"])
    raise SystemExit("could not determine issue number from input")


def author_login(item: dict[str, Any]) -> str:
    user = item.get("user") or item.get("author") or {}
    return user.get("login") or ""


def is_automation_user(item: dict[str, Any]) -> bool:
    user = item.get("user") or item.get("author") or {}
    login = (user.get("login") or "").lower()
    user_type = (user.get("type") or "").lower()
    return user_type == "bot" or login.endswith("[bot]")


def label_names(issue: dict[str, Any]) -> list[str]:
    return [label.get("name", "") for label in issue.get("labels", []) if label.get("name")]


def assignee_logins(issue: dict[str, Any]) -> list[str]:
    return [assignee.get("login", "") for assignee in issue.get("assignees", []) if assignee.get("login")]


def is_pull_request_issue_event(event: dict[str, Any]) -> bool:
    issue = event.get("issue") or {}
    return "pull_request" in issue and issue.get("pull_request") is not None


def event_issue(event: dict[str, Any]) -> dict[str, Any]:
    issue = event.get("issue")
    return issue if isinstance(issue, dict) else {}


def event_comment(event: dict[str, Any]) -> dict[str, Any]:
    comment = event.get("comment")
    return comment if isinstance(comment, dict) else {}


def issue_has_label(issue: dict[str, Any], label: str) -> bool:
    return label in label_names(issue)


def comment_has_triage_command(comment: object, login: str) -> bool:
    if not isinstance(comment, str) or not comment.strip() or not login.strip():
        return False

    expected = f"@{login.strip()} /triage"
    in_fenced_code = False
    for line in comment.splitlines():
        stripped_left = line.lstrip()
        if stripped_left.startswith(">"):
            continue
        if stripped_left.startswith("```"):
            in_fenced_code = not in_fenced_code
            continue
        if in_fenced_code:
            continue

        stripped = line.strip()
        if stripped == expected or stripped.startswith(f"{expected} "):
            return True
    return False


def triggering_comment(event: dict[str, Any]) -> dict[str, Any] | None:
    comment = event_comment(event)
    if not comment:
        return None
    return {
        "id": comment.get("id"),
        "author": author_login(comment),
        "author_association": comment.get("author_association") or "",
        "body": comment.get("body") or "",
        "created_at": comment.get("created_at") or "",
        "url": comment.get("html_url") or "",
    }


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


def should_run(args: argparse.Namespace, event: dict[str, Any]) -> tuple[bool, str]:
    if args.event_name == "workflow_dispatch":
        return True, "manual workflow dispatch"

    issue = event_issue(event)
    if is_pull_request_issue_event(event):
        return False, "PR issue events are not issue triage targets"

    if args.event_name == "issues":
        action = event.get("action") or ""
        if action in {"opened", "reopened"}:
            if is_automation_user(issue):
                return False, "issue author is a bot or automation user"
            return True, f"issue {action}"
        return False, f"issue event action is not a triage trigger: {action or 'unknown'}"

    if args.event_name == "issue_comment":
        action = event.get("action") or ""
        if action != "created":
            return False, f"issue comment action is not a triage trigger: {action or 'unknown'}"
        comment = event_comment(event)
        if is_automation_user(comment):
            return False, "comment author is a bot or automation user"

        comment_author = author_login(comment)
        issue_author = author_login(issue)
        if (
            issue_has_label(issue, NEEDS_INFO_LABEL)
            and comment_author
            and issue_author
            and comment_author == issue_author
        ):
            return True, "needs-info issue author replied"

        agent_login = args.agent_login.strip()
        if not agent_login:
            return False, "agent login is not configured"
        association = comment.get("author_association") or ""
        if association not in TRUSTED_COMMENT_ASSOCIATIONS:
            return False, f"comment author association is not trusted: {association or 'unknown'}"
        if not comment_has_triage_command(comment.get("body") or "", agent_login):
            return False, f"issue comment did not contain @{agent_login} /triage command"
        return True, f"trusted issue comment requested @{agent_login} /triage"

    return False, f"event is not a triage trigger: {args.event_name or 'unknown'}"


def fetch_issue(repo: str, issue_number: int) -> dict[str, Any]:
    return run_gh_json(
        [
            "issue",
            "view",
            str(issue_number),
            "--repo",
            repo,
            "--json",
            "number,title,body,author,labels,assignees,url,state,createdAt",
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


def fetch_issue_candidates(repo: str, state: str, *, since: str = "") -> list[dict[str, Any]]:
    path = f"repos/{repo}/issues?state={state}&per_page=100"
    if since:
        path += f"&since={since}"
    pages = run_gh_json(["api", path, "--paginate", "--slurp"])
    return flatten_pages(pages)


def is_pull_request_item(item: dict[str, Any]) -> bool:
    return "pull_request" in item and item.get("pull_request") is not None


def normalize_candidate_issue(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "number": item.get("number"),
        "title": item.get("title") or "",
        "body": item.get("body") or "",
        "state": item.get("state") or "",
        "labels": label_names(item),
        "author": author_login(item),
        "created_at": item.get("created_at") or "",
        "updated_at": item.get("updated_at") or "",
        "closed_at": item.get("closed_at") or "",
        "url": item.get("html_url") or "",
    }


def recent_closed_since(now: datetime | None = None) -> str:
    current = now or datetime.now(timezone.utc)
    return (current - timedelta(days=7)).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_github_datetime(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def closed_within_window(item: dict[str, Any], since: datetime) -> bool:
    closed_at = parse_github_datetime(item.get("closed_at") or "")
    return closed_at is not None and closed_at >= since


def dedupe_candidates(repo: str, current_issue_number: int, *, now: datetime | None = None) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen: set[int] = set()
    for item in fetch_issue_candidates(repo, "open"):
        number = item.get("number")
        if number == current_issue_number or number in seen or is_pull_request_item(item):
            continue
        seen.add(number)
        candidates.append(normalize_candidate_issue(item))

    current = now or datetime.now(timezone.utc)
    closed_since = current - timedelta(days=7)
    for item in fetch_issue_candidates(repo, "closed", since=recent_closed_since(current)):
        number = item.get("number")
        if (
            number == current_issue_number
            or number in seen
            or is_pull_request_item(item)
            or not closed_within_window(item, closed_since)
        ):
            continue
        seen.add(number)
        candidates.append(normalize_candidate_issue(item))
    return candidates


def fetch_default_branch(repo: str) -> str:
    repository = run_gh_json(["repo", "view", repo, "--json", "defaultBranchRef"])
    default_branch = (repository.get("defaultBranchRef") or {}).get("name")
    if not default_branch:
        raise SystemExit("could not determine default branch")
    return default_branch


def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"labels": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def read_issue_templates(root: Path) -> list[dict[str, str]]:
    template_dir = root / ".github" / "ISSUE_TEMPLATE"
    if not template_dir.exists():
        return []
    templates: list[dict[str, str]] = []
    for path in sorted(template_dir.rglob("*")):
        if path.is_file():
            templates.append(
                {
                    "path": path.relative_to(root).as_posix(),
                    "body": path.read_text(encoding="utf-8"),
                }
            )
    return templates


def write_comments(path: Path, comments: list[dict[str, Any]]) -> None:
    lines: list[str] = []
    for comment in comments:
        lines.extend(
            [
                f"Author: {author_login(comment)}",
                f"Author-Association: {comment.get('author_association') or ''}",
                f"Created: {comment.get('created_at') or ''}",
                "",
                comment.get("body") or "",
                "",
                "---",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_templates(path: Path, templates: list[dict[str, str]]) -> None:
    lines: list[str] = []
    for template in templates:
        lines.extend(
            [
                f"Path: {template['path']}",
                "",
                template["body"],
                "",
                "---",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_dedupe_candidates(path: Path, candidates: list[dict[str, Any]]) -> None:
    path.write_text(json.dumps(candidates, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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
    parser.add_argument("--include-issue-body", action="store_true")
    parser.add_argument("--output", default="triage_context.json")
    parser.add_argument("--comments-output", default="issue_comments.txt")
    parser.add_argument("--templates-output", default="issue_templates.txt")
    parser.add_argument("--dedupe-output", default="dedupe_candidates.json")
    parser.add_argument("--github-output", default=os.environ.get("GITHUB_OUTPUT", ""))
    args = parser.parse_args()

    event = load_event(args.event_path)
    issue_number = extract_issue_number(args.issue, event)
    issue = fetch_issue(args.repo, issue_number)
    comments = fetch_comments(args.repo, issue_number)
    candidates = dedupe_candidates(args.repo, issue_number)
    default_branch = fetch_default_branch(args.repo)
    run, reason = should_run(args, event)
    trigger_comment = triggering_comment(event) if args.event_name == "issue_comment" else None
    historical_comments = remove_triggering_comment(comments, trigger_comment)
    root = Path.cwd()
    config = load_config(root / ".github" / "issue-triage" / "config.json")
    templates = read_issue_templates(root)

    context = {
        "owner": args.repo.split("/", 1)[0],
        "repo": args.repo.split("/", 1)[1] if "/" in args.repo else args.repo,
        "repository": args.repo,
        "checkout_path": str(root),
        "default_branch": default_branch,
        "issue": issue,
        "issue_number": issue_number,
        "issue_title": issue.get("title") or "",
        "issue_body": issue.get("body") or "",
        "original_report": issue.get("body") or "",
        "issue_labels": label_names(issue),
        "issue_assignees": assignee_logins(issue),
        "issue_author": author_login(issue),
        "issue_created_at": issue.get("createdAt") or "",
        "issue_state": issue.get("state") or "",
        "issue_url": issue.get("url") or "",
        "comments_count": len(comments),
        "historical_comments_count": len(historical_comments),
        "triggering_comment": trigger_comment,
        "trigger_reason": reason if run else "",
        "triage_config": config,
        "issue_template_paths": [template["path"] for template in templates],
        "dedupe_candidates_path": args.dedupe_output,
        "dedupe_candidates_count": len(candidates),
        "include_issue_body": args.include_issue_body,
        "expected_output": "triage_result.json",
        "skill_paths": [
            ".agents/skills/triage-issue/SKILL.md",
            ".agents/skills/dedupe-issue/SKILL.md",
        ],
        "optional_companion_skill_paths": [
            ".agents/skills/triage-issue-repo/SKILL.md",
            ".agents/skills/dedupe-issue-repo/SKILL.md",
            ".agents/skills/triage-issue-local/SKILL.md",
            ".agents/skills/dedupe-issue-local/SKILL.md",
        ],
        "should_run": run,
        "skip_reason": "" if run else reason,
    }

    Path(args.output).write_text(json.dumps(context, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_comments(Path(args.comments_output), historical_comments)
    write_templates(Path(args.templates_output), templates)
    write_dedupe_candidates(Path(args.dedupe_output), candidates)
    write_github_output(
        args.github_output,
        {
            "should_run": "true" if run else "false",
            "skip_reason": "" if run else reason,
            "issue_number": str(issue_number),
            "default_branch": default_branch,
            "include_issue_body": "true" if args.include_issue_body else "false",
        },
    )


if __name__ == "__main__":
    main()
