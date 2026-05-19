#!/usr/bin/env python3
"""Prepare stable PR comment response context."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from prepare_issue_implementation_context import collect_coauthor_directives  # noqa: E402
from resolve_pr_event import comment_has_fix_command  # noqa: E402


AUTHORIZED_ASSOCIATIONS = {"OWNER", "MEMBER", "COLLABORATOR"}
FALLBACK_BRANCH_PREFIX = "spec/respond-pr"


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


def association(item: dict[str, Any]) -> str:
    return str(item.get("author_association") or item.get("authorAssociation") or "")


def fetch_pr(repo: str, number: int) -> dict[str, Any]:
    return run_gh_json(["api", f"repos/{repo}/pulls/{number}"])


def fetch_default_branch(repo: str) -> str:
    repository = run_gh_json(["repo", "view", repo, "--json", "defaultBranchRef"])
    default_branch = (repository.get("defaultBranchRef") or {}).get("name")
    if not default_branch:
        raise SystemExit("could not determine default branch")
    return default_branch


def fetch_review_comments(repo: str, number: int) -> list[dict[str, Any]]:
    pages = run_gh_json(
        [
            "api",
            f"repos/{repo}/pulls/{number}/comments?per_page=100",
            "--paginate",
            "--slurp",
        ]
    )
    return flatten_pages(pages)


def issue_is_pr(event: dict[str, Any]) -> bool:
    issue = event.get("issue") or {}
    return bool(issue.get("pull_request"))


def event_trigger(event_name: str, event: dict[str, Any]) -> dict[str, Any]:
    if event_name == "issue_comment":
        if not issue_is_pr(event):
            raise SystemExit("issue_comment event is not for a pull request")
        comment = event.get("comment") or {}
        issue = event.get("issue") or {}
        return {
            "pr_number": int(issue["number"]),
            "trigger_kind": "conversation",
            "trigger_comment_id": comment.get("id"),
            "review_reply_target_id": 0,
            "body": comment.get("body") or "",
            "trigger_actor": author_login(comment),
            "trigger_actor_association": association(comment),
            "trigger_created_at": comment.get("created_at") or "",
            "trigger_url": comment.get("html_url") or "",
        }
    if event_name == "pull_request_review_comment":
        comment = event.get("comment") or {}
        pr = event.get("pull_request") or {}
        return {
            "pr_number": int(pr["number"]),
            "trigger_kind": "review",
            "trigger_comment_id": comment.get("id"),
            "review_reply_target_id": comment.get("id"),
            "body": comment.get("body") or "",
            "trigger_actor": author_login(comment),
            "trigger_actor_association": association(comment),
            "trigger_created_at": comment.get("created_at") or "",
            "trigger_url": comment.get("html_url") or "",
        }
    if event_name == "pull_request_review":
        review = event.get("review") or {}
        pr = event.get("pull_request") or {}
        return {
            "pr_number": int(pr["number"]),
            "trigger_kind": "review_body",
            "trigger_comment_id": review.get("id"),
            "review_reply_target_id": 0,
            "body": review.get("body") or "",
            "trigger_actor": author_login(review),
            "trigger_actor_association": association(review),
            "trigger_created_at": review.get("submitted_at") or "",
            "trigger_url": review.get("html_url") or "",
        }
    if event_name == "workflow_dispatch":
        raise SystemExit("workflow_dispatch requires real PR comment event metadata for respond-to-pr-comment")
    raise SystemExit(f"unsupported event_name: {event_name}")


def branch_strategy(repo: str, pr: dict[str, Any], authorized: bool) -> dict[str, Any]:
    head = pr.get("head") or {}
    base = pr.get("base") or {}
    head_repo = (head.get("repo") or {}).get("full_name") or ""
    base_repo = (base.get("repo") or {}).get("full_name") or repo
    head_branch = head.get("ref") or ""
    pr_number = pr.get("number")
    same_repo = bool(head_repo and head_repo == base_repo)
    can_push_head = bool(authorized and same_repo and head_branch)
    fallback_branch = f"{FALLBACK_BRANCH_PREFIX}-{pr_number}"

    if can_push_head:
        return {
            "branch_strategy": "push-head",
            "can_push_to_head_branch": True,
            "agent_push_repo_full_name": head_repo,
            "agent_push_branch": head_branch,
            "target_branch": head_branch,
        }
    if authorized and base_repo == repo:
        return {
            "branch_strategy": "fallback-pr-to-fork",
            "can_push_to_head_branch": False,
            "agent_push_repo_full_name": base_repo,
            "agent_push_branch": fallback_branch,
            "target_branch": fallback_branch,
        }
    return {
        "branch_strategy": "blocked",
        "can_push_to_head_branch": False,
        "agent_push_repo_full_name": "",
        "agent_push_branch": "",
        "target_branch": "",
    }


def review_comment_index(comments: list[dict[str, Any]]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for comment in comments:
        comment_id = comment.get("id")
        if comment_id is None:
            continue
        items.append(
            {
                "comment_id": comment_id,
                "thread_id": comment.get("pull_request_review_id"),
                "path": comment.get("path") or "",
                "line": comment.get("line") or comment.get("original_line"),
                "author": author_login(comment),
                "author_association": association(comment),
                "body": comment.get("body") or "",
                "diff_hunk": comment.get("diff_hunk") or "",
                "url": comment.get("html_url") or "",
            }
        )
    return {"review_comments": items}


def build_context(repo: str, event_name: str, event: dict[str, Any], agent_login: str) -> tuple[dict[str, Any], dict[str, Any]]:
    trigger = event_trigger(event_name, event)
    pr = fetch_pr(repo, trigger["pr_number"])
    default_branch = fetch_default_branch(repo)
    assoc = trigger["trigger_actor_association"]
    has_command = comment_has_fix_command(trigger["body"], agent_login)
    authorized = assoc in AUTHORIZED_ASSOCIATIONS
    state = str(pr.get("state") or "").lower()
    strategy = branch_strategy(repo, pr, authorized)

    should_run = has_command and authorized and state == "open" and strategy["branch_strategy"] != "blocked"
    if not agent_login:
        skip_reason = "agent login is not configured"
    elif not has_command:
        skip_reason = "missing valid @AGENT_LOGIN /fix command"
    elif not authorized:
        skip_reason = f"trigger actor association {assoc or 'UNKNOWN'} is not authorized"
    elif state != "open":
        skip_reason = f"pull request is {state or 'not open'}"
    elif strategy["branch_strategy"] == "blocked":
        skip_reason = "no writable branch strategy is available"
    else:
        skip_reason = ""

    head = pr.get("head") or {}
    base = pr.get("base") or {}
    head_repo = (head.get("repo") or {}).get("full_name") or ""
    base_repo = (base.get("repo") or {}).get("full_name") or repo
    owner, name = repo.split("/", 1)
    context = {
        "owner": owner,
        "repo": name,
        "repository": repo,
        "pr_number": trigger["pr_number"],
        "pr_url": pr.get("html_url") or "",
        "pr_title": pr.get("title") or "",
        "default_branch": default_branch,
        "head_branch": head.get("ref") or "",
        "head_sha": head.get("sha") or "",
        "head_repo_full_name": head_repo,
        "base_branch": base.get("ref") or "",
        "base_sha": base.get("sha") or "",
        "base_repo_full_name": base_repo,
        "is_cross_repository": bool(head_repo and head_repo != base_repo),
        "maintainer_can_modify": bool(pr.get("maintainer_can_modify")),
        **strategy,
        **{key: value for key, value in trigger.items() if key != "body"},
        "trigger_body": trigger["body"],
        "trigger_actor_is_authorized": authorized,
        "trigger_command_present": has_command,
        "has_spec_context": False,
        "coauthor_directives": collect_coauthor_directives(trigger["body"], pr.get("body") or ""),
        "skill_paths": [
            ".agents/skills/implement-specs/SKILL.md",
            ".agents/skills/spec-driven-implementation/SKILL.md",
            ".agents/skills/implement-issue/SKILL.md",
        ],
        "should_run": should_run,
        "should_noop": False,
        "skip_reason": skip_reason,
    }
    return context, pr


def write_github_output(path: str | None, values: dict[str, str]) -> None:
    if not path:
        return
    with Path(path).open("a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--event-path", default=os.environ.get("GITHUB_EVENT_PATH", ""))
    parser.add_argument("--event-name", default=os.environ.get("GITHUB_EVENT_NAME", ""))
    parser.add_argument("--agent-login", default="")
    parser.add_argument("--output", default="pr_comment_context.json")
    parser.add_argument("--pr-event-output", default="pr_event.json")
    parser.add_argument("--review-comment-ids-output", default="review_comment_ids.json")
    parser.add_argument("--github-output", default=os.environ.get("GITHUB_OUTPUT", ""))
    args = parser.parse_args()

    event = load_event(args.event_path)
    context, pr = build_context(args.repo, args.event_name, event, args.agent_login.strip())
    comments = fetch_review_comments(args.repo, int(context["pr_number"]))
    ids = review_comment_index(comments)

    Path(args.output).write_text(json.dumps(context, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(args.pr_event_output).write_text(json.dumps({"pull_request": pr}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path(args.review_comment_ids_output).write_text(json.dumps(ids, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_github_output(
        args.github_output,
        {
            "should_run": "true" if context["should_run"] else "false",
            "should_noop": "false",
            "skip_reason": str(context["skip_reason"]),
            "branch_strategy": str(context["branch_strategy"]),
            "agent_push_repo_full_name": str(context["agent_push_repo_full_name"]),
            "agent_push_branch": str(context["agent_push_branch"]),
            "target_branch": str(context["target_branch"]),
            "head_sha": str(context["head_sha"]),
            "base_sha": str(context["base_sha"]),
            "head_repo": str(context["head_repo_full_name"]),
            "base_branch": str(context["base_branch"]),
            "pr_number": str(context["pr_number"]),
        },
    )


if __name__ == "__main__":
    main()
