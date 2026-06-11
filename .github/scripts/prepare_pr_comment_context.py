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

from artifact_contracts import write_github_output  # noqa: E402
from github_api import fetch_default_branch, flatten_gh_pages as flatten_pages, run_gh_json  # noqa: E402
from prepare_issue_implementation_context import collect_coauthor_directives  # noqa: E402
from resolve_pr_event import comment_has_fix_command  # noqa: E402


AUTHORIZED_ASSOCIATIONS = {"OWNER", "MEMBER", "COLLABORATOR"}
AUTHORIZED_PRIVATE_CONTRIBUTOR_PERMISSIONS = {"admin", "maintain", "write"}
FALLBACK_BRANCH_PREFIX = "spec/respond-pr"
PAGE_SIZE = 100
PAGE_INFO = "pageInfo { hasNextPage endCursor }"


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


def fetch_collaborator_permission(repo: str, login: str) -> str:
    if not login:
        return ""
    try:
        permission = run_gh_json(["api", f"repos/{repo}/collaborators/{login}/permission"])
    except subprocess.CalledProcessError:
        return ""
    return str(permission.get("permission") or "").lower()


def fetch_trigger_item(repo: str, trigger: dict[str, Any]) -> dict[str, Any]:
    kind = trigger.get("trigger_kind")
    comment_id = trigger.get("trigger_comment_id")
    if kind == "conversation" and comment_id:
        return run_gh_json(["api", f"repos/{repo}/issues/comments/{comment_id}"])
    if kind == "review" and comment_id:
        return run_gh_json(["api", f"repos/{repo}/pulls/comments/{comment_id}"])
    if kind == "review_body" and comment_id:
        return run_gh_json(["api", f"repos/{repo}/pulls/{trigger['pr_number']}/reviews/{comment_id}"])
    return {}


def fill_trigger_author_metadata(repo: str, trigger: dict[str, Any]) -> dict[str, Any]:
    association_value = str(trigger.get("trigger_actor_association") or "").upper()
    if trigger.get("trigger_actor") and association_value and association_value != "NONE":
        return trigger

    try:
        item = fetch_trigger_item(repo, trigger)
    except subprocess.CalledProcessError:
        return trigger

    enriched = dict(trigger)
    if not enriched.get("trigger_actor"):
        enriched["trigger_actor"] = author_login(item)
    enriched_association = str(enriched.get("trigger_actor_association") or "").upper()
    if not enriched_association or enriched_association == "NONE":
        enriched["trigger_actor_association"] = association(item)
    return enriched


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


def fetch_review_threads_page(owner: str, name: str, number: int, after: str | None = None) -> dict[str, Any]:
    after_variable = ", $after: String!" if after else ""
    after_argument = ", after: $after" if after else ""
    query = f"""
      query($owner: String!, $name: String!, $number: Int!{after_variable}) {{
        repository(owner: $owner, name: $name) {{
          pullRequest(number: $number) {{
            reviewThreads(first: {PAGE_SIZE}{after_argument}) {{
              {PAGE_INFO}
              nodes {{
                id
                isResolved
                isOutdated
                comments(first: {PAGE_SIZE}) {{
                  {PAGE_INFO}
                  nodes {{ databaseId }}
                }}
              }}
            }}
          }}
        }}
      }}
    """
    args = [
        "api",
        "graphql",
        "-f",
        f"query={query}",
        "-F",
        f"owner={owner}",
        "-F",
        f"name={name}",
        "-F",
        f"number={number}",
    ]
    if after:
        args.extend(["-F", f"after={after}"])
    data = run_gh_json(args)
    return data["data"]["repository"]["pullRequest"]["reviewThreads"]


def fetch_thread_comments_page(thread_id: str, after: str) -> dict[str, Any]:
    query = f"""
      query($id: ID!, $after: String!) {{
        node(id: $id) {{
          ... on PullRequestReviewThread {{
            comments(first: {PAGE_SIZE}, after: $after) {{
              {PAGE_INFO}
              nodes {{ databaseId }}
            }}
          }}
        }}
      }}
    """
    data = run_gh_json(["api", "graphql", "-f", f"query={query}", "-F", f"id={thread_id}", "-F", f"after={after}"])
    return data["data"]["node"]["comments"]


def paginate_thread_comments(thread: dict[str, Any]) -> None:
    connection = thread.get("comments") or {}
    page_info = connection.get("pageInfo") or {}
    while page_info.get("hasNextPage"):
        page = fetch_thread_comments_page(str(thread["id"]), str(page_info["endCursor"]))
        connection.setdefault("nodes", []).extend(page.get("nodes") or [])
        connection["pageInfo"] = page.get("pageInfo") or {}
        page_info = connection["pageInfo"]


def fetch_review_threads(repo: str, number: int) -> list[dict[str, Any]]:
    owner, name = repo.split("/", 1)
    connection = fetch_review_threads_page(owner, name, number)
    threads = connection.get("nodes") or []
    page_info = connection.get("pageInfo") or {}
    while page_info.get("hasNextPage"):
        page = fetch_review_threads_page(owner, name, number, str(page_info["endCursor"]))
        threads.extend(page.get("nodes") or [])
        page_info = page.get("pageInfo") or {}
    for thread in threads:
        paginate_thread_comments(thread)
    return threads


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


def base_repo_is_private(pr: dict[str, Any]) -> bool:
    base = pr.get("base") or {}
    base_repo = base.get("repo") or {}
    return bool(base_repo.get("private"))


def trigger_authorization(repo: str, pr: dict[str, Any], trigger: dict[str, Any]) -> dict[str, Any]:
    assoc = trigger["trigger_actor_association"]
    actor = trigger["trigger_actor"]
    is_private = base_repo_is_private(pr)
    permission = ""

    if assoc in AUTHORIZED_ASSOCIATIONS:
        return {
            "authorized": True,
            "permission": permission,
            "private_repo": is_private,
            "skip_reason": "",
        }
    if assoc != "CONTRIBUTOR":
        return {
            "authorized": False,
            "permission": permission,
            "private_repo": is_private,
            "skip_reason": f"trigger actor association {assoc or 'UNKNOWN'} is not authorized",
        }
    if not is_private:
        return {
            "authorized": False,
            "permission": permission,
            "private_repo": is_private,
            "skip_reason": "trigger actor association CONTRIBUTOR is not authorized for public repositories",
        }

    permission = fetch_collaborator_permission(repo, actor)
    if permission in AUTHORIZED_PRIVATE_CONTRIBUTOR_PERMISSIONS:
        return {
            "authorized": True,
            "permission": permission,
            "private_repo": is_private,
            "skip_reason": "",
        }
    return {
        "authorized": False,
        "permission": permission,
        "private_repo": is_private,
        "skip_reason": (
            f"trigger actor association CONTRIBUTOR has repository permission "
            f"{permission or 'unknown'}, not write/maintain/admin"
        ),
    }


def review_thread_state_by_comment(threads: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    states: dict[int, dict[str, Any]] = {}
    for thread in threads:
        comments = (thread.get("comments") or {}).get("nodes") or []
        for comment in comments:
            database_id = comment.get("databaseId")
            if isinstance(database_id, int):
                states[database_id] = {
                    "review_thread_node_id": thread.get("id") or "",
                    "is_resolved": bool(thread.get("isResolved")),
                    "is_outdated": bool(thread.get("isOutdated")),
                }
    return states


def review_comment_index(comments: list[dict[str, Any]], threads: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    thread_states = review_thread_state_by_comment(threads or [])
    items: list[dict[str, Any]] = []
    for comment in comments:
        comment_id = comment.get("id")
        if comment_id is None:
            continue
        thread_state = thread_states.get(comment_id, {})
        items.append(
            {
                "comment_id": comment_id,
                "thread_id": comment.get("pull_request_review_id"),
                "review_thread_node_id": thread_state.get("review_thread_node_id") or "",
                "is_resolved": thread_state.get("is_resolved"),
                "is_outdated": thread_state.get("is_outdated"),
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


def run_decision(
    *,
    agent_login: str,
    has_command: bool,
    auth: dict[str, Any],
    pr_state: str,
    strategy: dict[str, Any],
) -> tuple[bool, str]:
    authorized = bool(auth["authorized"])
    should_run = has_command and authorized and pr_state == "open" and strategy["branch_strategy"] != "blocked"
    if not agent_login:
        return should_run, "agent login is not configured"
    if not has_command:
        return should_run, "missing valid @AGENT_LOGIN /fix command"
    if not authorized:
        return should_run, str(auth["skip_reason"])
    if pr_state != "open":
        return should_run, f"pull request is {pr_state or 'not open'}"
    if strategy["branch_strategy"] == "blocked":
        return should_run, "no writable branch strategy is available"
    return should_run, ""


def build_pr_comment_context_payload(
    repo: str,
    *,
    trigger: dict[str, Any],
    pr: dict[str, Any],
    default_branch: str,
    strategy: dict[str, Any],
    auth: dict[str, Any],
    has_command: bool,
    should_run: bool,
    skip_reason: str,
) -> dict[str, Any]:
    head = pr.get("head") or {}
    base = pr.get("base") or {}
    head_repo = (head.get("repo") or {}).get("full_name") or ""
    base_repo = (base.get("repo") or {}).get("full_name") or repo
    owner, name = repo.split("/", 1)
    return {
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
        "trigger_actor_is_authorized": bool(auth["authorized"]),
        "trigger_actor_repository_permission": auth["permission"],
        "base_repo_private": auth["private_repo"],
        "trigger_command_present": has_command,
        "has_spec_context": False,
        "coauthor_directives": collect_coauthor_directives(trigger["body"], pr.get("body") or ""),
        "skill_paths": [
            ".github/skills/implement-specs/SKILL.md",
            ".agents/skills/spec-driven-implementation/SKILL.md",
            ".github/skills/implement-issue/SKILL.md",
        ],
        "should_run": should_run,
        "should_noop": False,
        "skip_reason": skip_reason,
    }


def build_context(repo: str, event_name: str, event: dict[str, Any], agent_login: str) -> tuple[dict[str, Any], dict[str, Any]]:
    trigger = fill_trigger_author_metadata(repo, event_trigger(event_name, event))
    pr = fetch_pr(repo, trigger["pr_number"])
    default_branch = fetch_default_branch(repo)
    has_command = comment_has_fix_command(trigger["body"], agent_login)
    auth = trigger_authorization(repo, pr, trigger)
    authorized = bool(auth["authorized"])
    state = str(pr.get("state") or "").lower()
    strategy = branch_strategy(repo, pr, authorized)
    should_run, skip_reason = run_decision(
        agent_login=agent_login,
        has_command=has_command,
        auth=auth,
        pr_state=state,
        strategy=strategy,
    )
    context = build_pr_comment_context_payload(
        repo,
        trigger=trigger,
        pr=pr,
        default_branch=default_branch,
        strategy=strategy,
        auth=auth,
        has_command=has_command,
        should_run=should_run,
        skip_reason=skip_reason,
    )
    return context, pr


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--event-path", default=os.environ.get("GITHUB_EVENT_PATH", ""))
    parser.add_argument("--event-name", default=os.environ.get("GITHUB_EVENT_NAME", ""))
    parser.add_argument("--agent-login", default="")
    parser.add_argument("--output", default="pr_comment_context.json")
    parser.add_argument("--pr-event-output", default="pr_event.json")
    parser.add_argument("--review-comment-ids-output", default="review_comment_ids.json")
    parser.add_argument("--github-output", default=os.environ.get("GITHUB_OUTPUT", ""))
    return parser.parse_args(argv)


def run(args: argparse.Namespace) -> None:
    event = load_event(args.event_path)
    context, pr = build_context(args.repo, args.event_name, event, args.agent_login.strip())
    comments = fetch_review_comments(args.repo, int(context["pr_number"]))
    threads = fetch_review_threads(args.repo, int(context["pr_number"]))
    ids = review_comment_index(comments, threads)

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


def main() -> None:
    run(parse_args())


if __name__ == "__main__":
    main()
