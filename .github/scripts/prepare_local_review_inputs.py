#!/usr/bin/env python3
"""Prepare root-level review snapshots for local PR review skills."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

import build_pr_diff  # noqa: E402
import select_review_skill  # noqa: E402
import write_pr_description  # noqa: E402
import write_spec_context  # noqa: E402


TEMP_REVIEW_PATHS = (
    Path("pr_description.txt"),
    Path("pr_diff.txt"),
    Path("spec_context.md"),
    Path("review.json"),
)


def run(args: list[str]) -> str:
    result = subprocess.run(args, check=True, stdout=subprocess.PIPE, text=True)
    return result.stdout.strip()


def optional_git(args: list[str]) -> str:
    try:
        return run(["git", *args])
    except subprocess.CalledProcessError:
        return ""


def remove_stale_review_files() -> None:
    for path in TEMP_REVIEW_PATHS:
        if path.exists():
            path.unlink()


def require_clean_worktree() -> None:
    status = subprocess.run(
        ["git", "status", "--porcelain=v1", "-z"],
        check=True,
        stdout=subprocess.PIPE,
    ).stdout
    if status:
        raise SystemExit("working tree must be clean before local review")


def resolve_ref(ref: str) -> str:
    return run(["git", "rev-parse", ref])


def default_base() -> str:
    for ref in ("upstream/main", "origin/main", "main"):
        if optional_git(["rev-parse", "--verify", "--quiet", ref]):
            return ref
    raise SystemExit("could not resolve default review base; pass --base")


def display_base_ref(base: str) -> str:
    if "/" in base and not base.startswith(("refs/", ".")):
        return base.split("/", 1)[1]
    return base


def remote_repo_from_url(url: str) -> str:
    patterns = [
        r"github\.com[:/](?P<repo>[^/]+/[^/]+?)(?:\.git)?$",
        r"github\.com/(?P<repo>[^/]+/[^/]+?)(?:\.git)?$",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group("repo")
    return ""


def default_repo() -> str:
    env_repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if env_repo:
        return env_repo
    for remote in ("upstream", "origin"):
        url = optional_git(["remote", "get-url", remote])
        repo = remote_repo_from_url(url)
        if repo:
            return repo
    raise SystemExit("could not determine GitHub repository; pass --repo")


def current_branch() -> str:
    return optional_git(["branch", "--show-current"]) or "HEAD"


def current_author() -> str:
    return optional_git(["config", "user.name"]) or optional_git(["config", "user.email"]) or ""


def local_pr_event(repo: str, base: str, base_sha: str, head_sha: str) -> dict[str, Any]:
    branch = current_branch()
    return {
        "pull_request": {
            "number": "",
            "state": "open",
            "draft": False,
            "title": optional_git(["log", "-1", "--pretty=%s"]),
            "body": "",
            "html_url": "",
            "user": {"login": current_author()},
            "base": {
                "ref": display_base_ref(base),
                "sha": base_sha,
                "repo": {"full_name": repo, "default_branch": display_base_ref(base)},
            },
            "head": {
                "ref": branch,
                "sha": head_sha,
                "repo": {"full_name": repo},
            },
        }
    }


def write_diff(base_sha: str, head_sha: str, output: Path) -> str:
    diff_text = build_pr_diff.convert(build_pr_diff.run_git_diff(base_sha, head_sha, 3))
    output.write_text(diff_text, encoding="utf-8")
    return diff_text


def write_spec_context_if_needed(repo: str, event: dict[str, Any], pr_diff_text: str, needs_spec_context: bool) -> None:
    output = Path("spec_context.md")
    if not needs_spec_context:
        if output.exists():
            output.unlink()
        return

    changed_files = write_spec_context.changed_files_from_diff_text(pr_diff_text)
    context = write_spec_context.resolve_spec_context(repo, event, changed_files)
    if context.get("spec_entries"):
        output.write_text(write_spec_context.format_spec_context_text(context), encoding="utf-8")
    elif output.exists():
        output.unlink()


def write_github_output(path: str | None, values: dict[str, str]) -> None:
    if not path:
        return
    with Path(path).open("a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default="")
    parser.add_argument("--base", default="")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--expected-skill", choices=[select_review_skill.CODE_REVIEW_SKILL, select_review_skill.SPEC_REVIEW_SKILL])
    parser.add_argument("--github-output", default=os.environ.get("GITHUB_OUTPUT", ""))
    args = parser.parse_args()

    remove_stale_review_files()
    require_clean_worktree()

    repo = args.repo or default_repo()
    base = args.base or default_base()
    base_sha = resolve_ref(base)
    head_sha = resolve_ref(args.head)
    event = local_pr_event(repo, base, base_sha, head_sha)

    Path("pr_description.txt").write_text(write_pr_description.format_pr_description(event), encoding="utf-8")
    pr_diff_text = write_diff(base_sha, head_sha, Path("pr_diff.txt"))
    skill = select_review_skill.select_skill(pr_diff_text)
    if args.expected_skill and skill != args.expected_skill:
        raise SystemExit(f"local review selected {skill}; expected {args.expected_skill}")

    needs_spec_context = select_review_skill.needs_spec_context(skill)
    write_spec_context_if_needed(repo, event, pr_diff_text, needs_spec_context)

    values = {
        "skill": skill,
        "needs_spec_context": "true" if needs_spec_context else "false",
        "base": base,
        "base_sha": base_sha,
        "head_sha": head_sha,
    }
    write_github_output(args.github_output, values)
    for key, value in values.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
