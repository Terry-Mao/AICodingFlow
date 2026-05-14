#!/usr/bin/env python3
"""Create or update a stable implementation progress comment."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


MARKER = "<!-- aicodingflow:create-implementation-from-issue -->"


def run_gh_json(args: list[str]) -> Any:
    result = subprocess.run(["gh", *args], check=True, stdout=subprocess.PIPE, text=True)
    return json.loads(result.stdout)


def flatten_pages(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list) and value and all(isinstance(page, list) for page in value):
        return [item for page in value for item in page]
    if isinstance(value, list):
        return value
    raise SystemExit("unexpected GitHub API response")


def find_progress_comment(repo: str, issue_number: int) -> dict[str, Any] | None:
    pages = run_gh_json(
        [
            "api",
            f"repos/{repo}/issues/{issue_number}/comments?per_page=100",
            "--paginate",
            "--slurp",
        ]
    )
    comments = flatten_pages(pages)
    for comment in comments:
        if MARKER in (comment.get("body") or ""):
            return comment
    return None


def build_body(context: dict[str, Any], status: str, message: str, pr_url: str = "") -> str:
    lines = [
        MARKER,
        f"Implementation status for issue #{context['issue_number']}: **{status}**.",
    ]
    if message:
        lines.extend(["", message])
    if pr_url:
        lines.extend(["", f"Pull request: {pr_url}"])
    return "\n".join(lines).rstrip() + "\n"


def upsert_progress_comment(repo: str, issue_number: int, body: str) -> None:
    existing = find_progress_comment(repo, issue_number)
    if existing:
        subprocess.run(
            ["gh", "api", f"repos/{repo}/issues/comments/{existing['id']}", "-X", "PATCH", "-f", f"body={body}"],
            check=True,
        )
        return
    subprocess.run(
        ["gh", "api", f"repos/{repo}/issues/{issue_number}/comments", "-f", f"body={body}"],
        check=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--context", default="issue_context.json")
    parser.add_argument("--status", required=True)
    parser.add_argument("--message", default="")
    parser.add_argument("--message-file", default="")
    parser.add_argument("--pr-url", default="")
    args = parser.parse_args()

    context = json.loads(Path(args.context).read_text(encoding="utf-8"))
    message = args.message
    if args.message_file:
        message = Path(args.message_file).read_text(encoding="utf-8").strip()
    body = build_body(context, args.status, message, args.pr_url)
    upsert_progress_comment(args.repo, int(context["issue_number"]), body)


if __name__ == "__main__":
    main()
