#!/usr/bin/env python3
"""Describe the review round across published reviews of one PR."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

import build_pr_diff
from artifact_contracts import write_github_output


MARKER = re.compile(r"<!-- aicodingflow-review base=([0-9a-f]{40}) head=([0-9a-f]{40}) -->")


def review_history(reviews: list[dict[str, Any]], bot_login: str) -> list[tuple[str, str]]:
    history: list[tuple[str, str]] = []
    seen: set[str] = set()
    for review in reviews:
        user = review.get("user") or {}
        if not isinstance(user, dict) or str(user.get("login", "")).lower() != bot_login.lower():
            continue
        if review.get("state") == "PENDING":
            continue
        sha = review.get("commit_id")
        if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha) or sha in seen:
            continue
        marker = MARKER.search(str(review.get("body") or ""))
        base_sha = marker.group(1) if marker and marker.group(2) == sha else ""
        history.append((sha, base_sha))
        seen.add(sha)
    return history


def round_context(history: list[tuple[str, str]], head_sha: str, base_sha: str, ancestor: bool) -> dict[str, Any]:
    heads = [sha for sha, _ in history]
    current_seen = head_sha in heads
    round_number = heads.index(head_sha) + 1 if current_seen else len(heads) + 1
    previous = next(((sha, base) for sha, base in reversed(history) if sha != head_sha), None)
    incremental = bool(
        round_number >= 4 and not current_seen and previous and previous[1] == base_sha and ancestor
    )
    return {
        "round": round_number,
        "mode": "incremental" if incremental else "full",
        "previous_head_sha": previous[0] if incremental and previous else "",
        "base_sha": base_sha,
        "head_sha": head_sha,
        "architecture_review_required": round_number >= 4,
    }


def fetch_reviews(repo: str, pr_number: int) -> list[dict[str, Any]]:
    raw = subprocess.check_output(
        ["gh", "api", f"repos/{repo}/pulls/{pr_number}/reviews?per_page=100", "--paginate", "--slurp"],
        text=True,
    )
    pages = json.loads(raw)
    if not isinstance(pages, list) or any(not isinstance(page, list) for page in pages):
        raise SystemExit("GitHub review pages were invalid")
    return [review for page in pages for review in page if isinstance(review, dict)]


def is_ancestor(previous: str, head: str, worktree: Path) -> bool:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", previous, head],
        cwd=worktree,
        check=False,
        capture_output=True,
    )
    return result.returncode == 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--pr-number", type=int, required=True)
    parser.add_argument("--head-sha", required=True)
    parser.add_argument("--base-sha", default="")
    parser.add_argument("--bot-login", default="github-actions[bot]")
    parser.add_argument("--worktree", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--incremental-diff", type=Path)
    parser.add_argument("--check-existing", action="store_true")
    parser.add_argument("--github-output", default="")
    args = parser.parse_args()

    history = review_history(fetch_reviews(args.repo, args.pr_number), args.bot_login)
    if args.check_existing:
        write_github_output(args.github_output, {"already_reviewed": str(any(sha == args.head_sha for sha, _ in history)).lower()})
        return
    if not all((args.base_sha, args.worktree, args.output, args.incremental_diff)):
        raise SystemExit("--base-sha, --worktree, --output and --incremental-diff are required")
    previous = next((sha for sha, _ in reversed(history) if sha != args.head_sha), "")
    ancestor = bool(previous and is_ancestor(previous, args.head_sha, args.worktree))
    context = round_context(history, args.head_sha, args.base_sha, ancestor)
    if context["mode"] == "incremental":
        lines = subprocess.run(
            ["git", "diff", "--no-color", "--no-ext-diff", "--unified=3", "--find-renames", previous, args.head_sha],
            cwd=args.worktree,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        args.incremental_diff.write_text(build_pr_diff.convert(lines), encoding="utf-8")
    args.output.write_text(json.dumps(context, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
