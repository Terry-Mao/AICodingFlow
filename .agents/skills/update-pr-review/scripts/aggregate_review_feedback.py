#!/usr/bin/env python3
"""Aggregate recent GitHub PR review feedback for update-pr-review."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any


DEFAULT_AGENT_LOGIN = "github-actions[bot]"


def run_gh_json(args: list[str]) -> Any:
    result = subprocess.run(["gh", *args], check=True, capture_output=True, text=True)
    text = result.stdout.strip()
    return json.loads(text) if text else None


def default_repo() -> str:
    data = run_gh_json(["repo", "view", "--json", "nameWithOwner"])
    return data["nameWithOwner"]


def split_repo(repo: str) -> tuple[str, str]:
    if "/" not in repo:
        raise SystemExit("--repo must use owner/name")
    owner, name = repo.split("/", 1)
    if not owner or not name:
        raise SystemExit("--repo must use owner/name")
    return owner, name


def list_pr_numbers(repo: str, days: int, pr_number: int | None) -> list[int]:
    if pr_number is not None:
        return [pr_number]
    since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)).date().isoformat()
    prs = run_gh_json(
        [
            "pr",
            "list",
            "--repo",
            repo,
            "--state",
            "all",
            "--search",
            f"updated:>={since}",
            "--limit",
            "100",
            "--json",
            "number",
        ]
    )
    return [int(pr["number"]) for pr in prs]


def graphql_pr(owner: str, repo: str, number: int) -> dict[str, Any]:
    query = """
query($owner: String!, $repo: String!, $number: Int!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $number) {
      number
      title
      url
      state
      updatedAt
      author { __typename login }
      files(first: 100) { nodes { path } }
      comments(first: 100) {
        nodes { author { __typename login } body createdAt url }
      }
      reviewThreads(first: 100) {
        nodes {
          isResolved
          isOutdated
          path
          line
          comments(first: 100) {
            nodes {
              author { __typename login }
              body
              createdAt
              url
              path
              line
              pullRequestReview { author { __typename login } state }
            }
          }
        }
      }
      reviews(first: 100) {
        nodes {
          author { __typename login }
          state
          body
          submittedAt
          comments(first: 100) {
            nodes { author { __typename login } body path line url }
          }
        }
      }
    }
  }
}
"""
    data = run_gh_json(
        [
            "api",
            "graphql",
            "-f",
            f"query={query}",
            "-F",
            f"owner={owner}",
            "-F",
            f"repo={repo}",
            "-F",
            f"number={number}",
        ]
    )
    pr = data["data"]["repository"]["pullRequest"]
    if pr is None:
        raise SystemExit(f"PR not found: {number}")
    return pr


def author_login(node: dict[str, Any] | None) -> str | None:
    if not node:
        return None
    author = node.get("author")
    return author.get("login") if author else None


def author_type(node: dict[str, Any] | None) -> str | None:
    if not node:
        return None
    author = node.get("author")
    return author.get("__typename") if author else None


def is_agent_comment(node: dict[str, Any], agent_logins: set[str]) -> bool:
    login = author_login(node)
    return bool(login and login in agent_logins)


def is_human_comment(node: dict[str, Any], excluded_logins: set[str], include_bots: bool) -> bool:
    login = author_login(node)
    if not login or login in excluded_logins:
        return False
    if include_bots:
        return True
    return author_type(node) != "Bot"


def classify_review_type(files: list[str]) -> str:
    return "spec" if files and all(path.startswith("specs/") for path in files) else "code"


def severity(body: str) -> str | None:
    for label in ("CRITICAL", "IMPORTANT", "SUGGESTION", "NIT"):
        if f"[{label}]" in body:
            return label
    return None


def has_suggestion(body: str) -> bool:
    return "```suggestion" in body


def normalize_pr(pr: dict[str, Any], agent_logins: set[str], include_bots: bool) -> dict[str, Any]:
    files = [node["path"] for node in pr["files"]["nodes"]]
    threads = []
    agent_comments = []
    human_review_comments = []

    for thread in pr["reviewThreads"]["nodes"]:
        comments = []
        for comment in thread["comments"]["nodes"]:
            comment_login = author_login(comment) or ""
            item = {
                "author": comment_login,
                "author_type": author_type(comment),
                "body": comment.get("body") or "",
                "created_at": comment.get("createdAt"),
                "url": comment.get("url"),
                "path": comment.get("path") or thread.get("path"),
                "line": comment.get("line") or thread.get("line"),
                "is_agent": is_agent_comment(comment, agent_logins),
                "severity": severity(comment.get("body") or ""),
                "has_suggestion": has_suggestion(comment.get("body") or ""),
            }
            comments.append(item)
            if item["is_agent"]:
                agent_comments.append(item)
            elif is_human_comment(comment, agent_logins, include_bots):
                human_review_comments.append(item)
        threads.append(
            {
                "path": thread.get("path"),
                "line": thread.get("line"),
                "is_resolved": thread.get("isResolved"),
                "is_outdated": thread.get("isOutdated"),
                "comments": comments,
            }
        )

    conversation_comments = [
        {
            "author": author_login(comment) or "",
            "author_type": author_type(comment),
            "body": comment.get("body") or "",
            "created_at": comment.get("createdAt"),
            "url": comment.get("url"),
        }
        for comment in pr["comments"]["nodes"]
    ]

    reviews = [
        {
            "author": author_login(review) or "",
            "author_type": author_type(review),
            "state": review.get("state"),
            "body": review.get("body") or "",
            "submitted_at": review.get("submittedAt"),
            "comments": [
                {
                    "author": author_login(comment) or "",
                    "author_type": author_type(comment),
                    "body": comment.get("body") or "",
                    "path": comment.get("path"),
                    "line": comment.get("line"),
                    "url": comment.get("url"),
                }
                for comment in review["comments"]["nodes"]
            ],
        }
        for review in pr["reviews"]["nodes"]
    ]

    return {
        "number": pr["number"],
        "title": pr["title"],
        "url": pr["url"],
        "state": pr["state"],
        "updated_at": pr["updatedAt"],
        "author": author_login(pr) or "",
        "author_type": author_type(pr),
        "review_type": classify_review_type(files),
        "changed_files": files,
        "agent_comments": agent_comments,
        "human_review_comments": human_review_comments,
        "conversation_comments": conversation_comments,
        "review_threads": threads,
        "reviews": reviews,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--pr", type=int)
    parser.add_argument(
        "--agent-login",
        action="append",
        dest="agent_logins",
        help="Agent login to exclude from human feedback. Repeat for multiple agents.",
    )
    parser.add_argument("--include-bots", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args()

    repo = args.repo or default_repo()
    owner, name = split_repo(repo)
    numbers = list_pr_numbers(repo, args.days, args.pr)
    agent_logins = set(args.agent_logins or [DEFAULT_AGENT_LOGIN])
    prs = [
        normalize_pr(graphql_pr(owner, name, number), agent_logins, args.include_bots)
        for number in numbers
    ]
    payload = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "repo": repo,
        "days": args.days,
        "agent_logins": sorted(agent_logins),
        "include_bots": args.include_bots,
        "prs": prs,
    }

    if args.output:
        output = Path(args.output)
    else:
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        handle = tempfile.NamedTemporaryFile(
            prefix=f"update-pr-review-feedback-{stamp}-",
            suffix=".json",
            delete=False,
        )
        output = Path(handle.name)
        handle.close()
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
