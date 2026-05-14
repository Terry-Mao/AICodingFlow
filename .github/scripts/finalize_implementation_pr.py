#!/usr/bin/env python3
"""Create or update the pull request for an implementation run."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


def run_gh_json(args: list[str]) -> Any:
    result = subprocess.run(["gh", *args], check=True, stdout=subprocess.PIPE, text=True)
    return json.loads(result.stdout)


def flatten_pages(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list) and value and all(isinstance(page, list) for page in value):
        return [item for page in value for item in page]
    if isinstance(value, list):
        return value
    raise SystemExit("unexpected GitHub API response")


def open_pr_for_branch(repo: str, branch_name: str) -> dict[str, Any] | None:
    owner = repo.split("/", 1)[0]
    pages = run_gh_json(
        [
            "api",
            f"repos/{repo}/pulls?state=open&head={owner}:{branch_name}&per_page=100",
            "--paginate",
            "--slurp",
        ]
    )
    prs = flatten_pages(pages)
    return prs[0] if prs else None


def edit_pr(repo: str, pr_number_or_branch: str, title: str, body: str) -> str:
    subprocess.run(
        [
            "gh",
            "pr",
            "edit",
            pr_number_or_branch,
            "--repo",
            repo,
            "--title",
            title,
            "--body",
            body,
        ],
        check=True,
    )
    pr = run_gh_json(["pr", "view", pr_number_or_branch, "--repo", repo, "--json", "url"])
    return pr["url"]


def create_pr(repo: str, base: str, head: str, title: str, body: str) -> str:
    result = subprocess.run(
        [
            "gh",
            "pr",
            "create",
            "--repo",
            repo,
            "--base",
            base,
            "--head",
            head,
            "--title",
            title,
            "--body",
            body,
            "--draft",
        ],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip()


def finalize(repo: str, context: dict[str, Any], metadata: dict[str, Any]) -> str:
    title = metadata["pr_title"]
    body = metadata["pr_summary"]
    branch_name = metadata["branch_name"]

    if context.get("spec_context_source") == "approved-pr" and context.get("selected_spec_pr_number"):
        return edit_pr(repo, str(context["selected_spec_pr_number"]), title, body)

    existing = open_pr_for_branch(repo, branch_name)
    if existing:
        return edit_pr(repo, str(existing["number"]), title, body)

    return create_pr(repo, str(context["default_branch"]), branch_name, title, body)


def write_github_output(path: str | None, values: dict[str, str]) -> None:
    if not path:
        return
    with Path(path).open("a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--context", default="issue_context.json")
    parser.add_argument("--metadata", default="pr-metadata.json")
    parser.add_argument("--github-output", default="")
    args = parser.parse_args()

    context = json.loads(Path(args.context).read_text(encoding="utf-8"))
    metadata = json.loads(Path(args.metadata).read_text(encoding="utf-8"))
    pr_url = finalize(args.repo, context, metadata)
    print(pr_url)
    write_github_output(args.github_output, {"pr_url": pr_url})


if __name__ == "__main__":
    main()
