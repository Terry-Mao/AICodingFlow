#!/usr/bin/env python3
"""Fetch GitHub issue and PR context with provenance markers."""

from __future__ import annotations

import argparse
import json
import subprocess
from typing import Any


TRUSTED_ASSOCIATIONS = {"OWNER", "MEMBER", "COLLABORATOR"}


def run_gh_json(args: list[str]) -> Any:
    result = subprocess.run(["gh", *args], check=True, stdout=subprocess.PIPE, text=True)
    return json.loads(result.stdout)


def flatten_pages(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list) and value and all(isinstance(page, list) for page in value):
        return [item for page in value for item in page]
    if isinstance(value, list):
        return value
    raise SystemExit("unexpected GitHub API response")


def author_login(item: dict[str, Any]) -> str:
    user = item.get("user") or item.get("author") or {}
    return user.get("login") or ""


def association(item: dict[str, Any]) -> str:
    return item.get("author_association") or item.get("authorAssociation") or ""


def section_header(kind: str, author: str, assoc: str, created: str = "", **metadata: object) -> str:
    trust = " trust=TRUSTED" if assoc in TRUSTED_ASSOCIATIONS else ""
    created_text = f" created_at={created}" if created else ""
    metadata_text = "".join(
        f" {key}={value}"
        for key, value in metadata.items()
        if value is not None and str(value) != ""
    )
    return f"--- source={kind}{metadata_text} author={author} author_association={assoc or 'UNKNOWN'}{trust}{created_text} ---"


def print_section(kind: str, item: dict[str, Any], body: str) -> None:
    print(section_header(kind, author_login(item), association(item), item.get("created_at") or ""))
    print(body or "")
    print()


def print_review_comment(comment: dict[str, Any]) -> None:
    print(
        section_header(
            "pr_review_comment",
            author_login(comment),
            association(comment),
            comment.get("created_at") or "",
            id=comment.get("id"),
            review_id=comment.get("pull_request_review_id"),
            path=comment.get("path"),
            line=comment.get("line") or comment.get("original_line"),
            side=comment.get("side") or comment.get("original_side"),
        )
    )
    print(comment.get("body") or "")
    print()


def fetch_issue(repo: str, number: int) -> None:
    issue = run_gh_json(
        [
            "api",
            f"repos/{repo}/issues/{number}",
        ]
    )
    print_section("issue_body", issue, issue.get("body") or "")
    comments = flatten_pages(
        run_gh_json(
            [
                "api",
                f"repos/{repo}/issues/{number}/comments?per_page=100",
                "--paginate",
                "--slurp",
            ]
        )
    )
    for comment in comments:
        print_section("issue_comment", comment, comment.get("body") or "")


def fetch_pr(repo: str, number: int, include_diff: bool) -> None:
    pr = run_gh_json(["api", f"repos/{repo}/pulls/{number}"])
    print_section("pr_body", pr, pr.get("body") or "")
    comments = flatten_pages(
        run_gh_json(
            [
                "api",
                f"repos/{repo}/issues/{number}/comments?per_page=100",
                "--paginate",
                "--slurp",
            ]
        )
    )
    for comment in comments:
        print_section("pr_comment", comment, comment.get("body") or "")
    reviews = flatten_pages(
        run_gh_json(
            [
                "api",
                f"repos/{repo}/pulls/{number}/reviews?per_page=100",
                "--paginate",
                "--slurp",
            ]
        )
    )
    for review in reviews:
        print_section("pr_review", review, review.get("body") or "")
    review_comments = flatten_pages(
        run_gh_json(
            [
                "api",
                f"repos/{repo}/pulls/{number}/comments?per_page=100",
                "--paginate",
                "--slurp",
            ]
        )
    )
    for comment in review_comments:
        print_review_comment(comment)
    if include_diff:
        fetch_pr_diff(repo, number)


def fetch_pr_diff(repo: str, number: int) -> None:
    result = subprocess.run(
        ["gh", "pr", "diff", str(number), "--repo", repo],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    print(section_header("pr_diff", "", ""))
    print(result.stdout)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    subparsers = parser.add_subparsers(dest="kind", required=True)

    issue_parser = subparsers.add_parser("issue")
    issue_parser.add_argument("--number", required=True, type=int)

    pr_parser = subparsers.add_parser("pr")
    pr_parser.add_argument("--number", required=True, type=int)
    pr_parser.add_argument("--include-diff", action="store_true")

    pr_diff_parser = subparsers.add_parser("pr-diff")
    pr_diff_parser.add_argument("--number", required=True, type=int)

    args = parser.parse_args()
    if args.kind == "issue":
        fetch_issue(args.repo, args.number)
    elif args.kind == "pr":
        fetch_pr(args.repo, args.number, args.include_diff)
    elif args.kind == "pr-diff":
        fetch_pr_diff(args.repo, args.number)


if __name__ == "__main__":
    main()
