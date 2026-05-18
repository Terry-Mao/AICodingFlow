#!/usr/bin/env python3
"""Apply validated issue triage output to GitHub."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


MARKER = "<!-- aicodingflow:triage-issue -->"
PROTECTED_LABELS = {"plan-approved", "ready-to-implement", "ready-to-spec"}


def run_gh_json(args: list[str]) -> Any:
    result = subprocess.run(["gh", *args], check=True, stdout=subprocess.PIPE, text=True)
    return json.loads(result.stdout)


def flatten_pages(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list) and value and all(isinstance(page, list) for page in value):
        return [item for page in value for item in page]
    if isinstance(value, list):
        return value
    raise SystemExit("unexpected GitHub API response")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def current_label_names(context: dict[str, Any]) -> set[str]:
    issue = context.get("issue") or {}
    labels = issue.get("labels") or []
    return {label.get("name", "") for label in labels if isinstance(label, dict) and label.get("name")}


def configured_label_names(context: dict[str, Any]) -> set[str]:
    config = context.get("triage_config") or {}
    labels = config.get("labels") or {}
    if not isinstance(labels, dict):
        raise SystemExit("triage_context.json field triage_config.labels must be an object")
    return {str(name) for name in labels}


def sync_labels(
    repo: str,
    issue_number: int,
    current_labels: set[str],
    desired_labels: list[str],
    managed_labels: set[str],
) -> None:
    desired = set(desired_labels) - PROTECTED_LABELS
    to_add = sorted(desired - current_labels)
    to_remove = sorted((current_labels & managed_labels) - desired)

    for label in to_add:
        subprocess.run(["gh", "issue", "edit", str(issue_number), "--repo", repo, "--add-label", label], check=True)
    for label in to_remove:
        subprocess.run(
            ["gh", "issue", "edit", str(issue_number), "--repo", repo, "--remove-label", label],
            check=True,
        )


def find_triage_comment(repo: str, issue_number: int) -> dict[str, Any] | None:
    pages = run_gh_json(
        [
            "api",
            f"repos/{repo}/issues/{issue_number}/comments?per_page=100",
            "--paginate",
            "--slurp",
        ]
    )
    for comment in flatten_pages(pages):
        if MARKER in (comment.get("body") or ""):
            return comment
    return None


def build_comment_body(context: dict[str, Any], result: dict[str, Any]) -> str:
    issue_body = (result.get("issue_body") or "").strip()
    if issue_body:
        body = issue_body
    else:
        body = f"### Triage summary\n\n{result.get('summary', '').strip()}"
    return f"{MARKER}\n{body.rstrip()}\n"


def upsert_triage_comment(repo: str, issue_number: int, body: str) -> None:
    existing = find_triage_comment(repo, issue_number)
    if existing:
        subprocess.run(
            ["gh", "api", f"repos/{repo}/issues/comments/{existing['id']}", "-X", "PATCH", "-f", f"body={body}"],
            check=True,
        )
        return
    subprocess.run(["gh", "api", f"repos/{repo}/issues/{issue_number}/comments", "-f", f"body={body}"], check=True)


def apply_result(repo: str, context: dict[str, Any], result: dict[str, Any], *, post_comment: bool) -> None:
    issue_number = int(context["issue_number"])
    managed_labels = configured_label_names(context) - PROTECTED_LABELS
    sync_labels(repo, issue_number, current_label_names(context), result.get("labels") or [], managed_labels)
    if post_comment and (result.get("issue_body") or result.get("summary")):
        upsert_triage_comment(repo, issue_number, build_comment_body(context, result))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--context", default="triage_context.json")
    parser.add_argument("--result", default="triage_result.json")
    parser.add_argument("--post-comment", action="store_true")
    args = parser.parse_args()

    apply_result(
        args.repo,
        load_json(Path(args.context)),
        load_json(Path(args.result)),
        post_comment=args.post_comment,
    )


if __name__ == "__main__":
    main()
