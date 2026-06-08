#!/usr/bin/env python3
"""Commit spec files and create or update the spec pull request."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from artifact_contracts import write_github_output
from github_api import flatten_gh_pages as flatten_pages
from github_api import run_gh_json


def run(args: list[str], *, capture: bool = False, check: bool = True) -> str:
    result = subprocess.run(
        args,
        check=check,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
        text=True,
    )
    return result.stdout.rstrip("\n") if capture else ""


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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


def edit_pr(repo: str, pr_number: int, title: str, body: str) -> str:
    run(["gh", "pr", "edit", str(pr_number), "--repo", repo, "--title", title, "--body", body])
    pr = run_gh_json(["pr", "view", str(pr_number), "--repo", repo, "--json", "url"])
    return str(pr["url"])


def create_pr(repo: str, base: str, head: str, title: str, body: str) -> str:
    return run(
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
        ],
        capture=True,
    ).strip()


def staged_paths() -> list[str]:
    output = run(["git", "diff", "--cached", "--name-only"], capture=True)
    return [line for line in output.splitlines() if line]


def configure_git(author_name: str, author_email: str) -> None:
    run(["git", "config", "user.name", author_name])
    run(["git", "config", "user.email", author_email])


def commit_and_push_specs(context: dict[str, Any], metadata: dict[str, Any], author_name: str, author_email: str) -> str:
    branch = str(metadata["branch_name"]).strip()
    title = str(metadata["pr_title"]).strip()
    default_branch = str(context["default_branch"]).strip()
    product_spec = str(context["product_spec"]).strip()
    tech_spec = str(context["tech_spec"]).strip()

    configure_git(author_name, author_email)
    run(["git", "fetch", "origin", f"+refs/heads/{branch}:refs/remotes/origin/{branch}"], check=False)
    run(["git", "fetch", "origin", f"+refs/heads/{default_branch}:refs/remotes/origin/{default_branch}"])
    run(["git", "switch", "-C", branch, f"origin/{default_branch}"])
    run(["git", "add", product_spec, tech_spec])
    if not staged_paths():
        return ""
    run(["git", "commit", "-m", title])
    run(["git", "push", "--force-with-lease", "origin", branch])
    return run(["git", "rev-parse", "HEAD"], capture=True)


def create_or_update_pr(repo: str, context: dict[str, Any], metadata: dict[str, Any]) -> str:
    branch = str(metadata["branch_name"]).strip()
    title = str(metadata["pr_title"]).strip()
    body = str(metadata["pr_summary"])
    existing = open_pr_for_branch(repo, branch)
    if existing:
        return edit_pr(repo, int(existing["number"]), title, body)
    return create_pr(repo, str(context["default_branch"]), branch, title, body)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--context", default="issue_context.json")
    parser.add_argument("--metadata", default="pr-metadata.json")
    parser.add_argument("--author-name", default="github-actions[bot]")
    parser.add_argument("--author-email", default="41898282+github-actions[bot]@users.noreply.github.com")
    parser.add_argument("--github-output", default="")
    args = parser.parse_args()

    context = load_json(Path(args.context))
    metadata = load_json(Path(args.metadata))
    sha = commit_and_push_specs(context, metadata, args.author_name, args.author_email)
    pr_url = create_or_update_pr(args.repo, context, metadata) if sha else ""
    if pr_url:
        print(pr_url)
    write_github_output(args.github_output, {"changed": "true" if sha else "false", "sha": sha, "pr_url": pr_url})


if __name__ == "__main__":
    main()
