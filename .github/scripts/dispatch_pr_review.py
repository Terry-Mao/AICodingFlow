#!/usr/bin/env python3
"""Dispatch review for a non-draft PR created by another workflow."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
from urllib.parse import quote, urlparse

from github_api import run_gh_json


def find_pr(repo: str, *, pr_url: str = "", head_branch: str = "") -> dict:
    if pr_url:
        parsed = urlparse(pr_url)
        server = urlparse(os.environ.get("GITHUB_SERVER_URL", "https://github.com"))
        match = re.fullmatch(r"/([^/]+/[^/]+)/pull/([1-9][0-9]*)", parsed.path)
        if parsed.scheme != server.scheme or parsed.netloc != server.netloc or not match or match.group(1) != repo:
            raise SystemExit("PR URL does not belong to this repository")
        return run_gh_json(["api", f"repos/{repo}/pulls/{match.group(2)}"])

    owner = repo.split("/", 1)[0]
    head = quote(f"{owner}:{head_branch}", safe="")
    prs = run_gh_json(["api", f"repos/{repo}/pulls?state=open&head={head}&per_page=100"])
    if len(prs) != 1:
        raise SystemExit(f"expected one open PR for branch {head_branch}, found {len(prs)}")
    return prs[0]


def dispatch(repo: str, *, pr_url: str = "", head_branch: str = "", allow_draft: bool = False) -> bool:
    pr = find_pr(repo, pr_url=pr_url, head_branch=head_branch)
    if pr.get("state") != "open":
        raise SystemExit("cannot dispatch review for a closed PR")
    head_repo = (pr.get("head") or {}).get("repo") or {}
    if head_repo.get("full_name") != repo:
        raise SystemExit("cannot auto-dispatch review for a fork PR")
    if pr.get("draft") and not allow_draft:
        print(f"PR #{pr['number']} is draft; skipping AI review dispatch")
        return False
    subprocess.run(
        ["gh", "workflow", "run", "review-pr.yml", "--repo", repo, "-f", f"pr_number={pr['number']}"],
        check=True,
    )
    print(f"Dispatched AI review for PR #{pr['number']}")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--pr-url")
    target.add_argument("--head-branch")
    parser.add_argument("--allow-draft", action="store_true")
    args = parser.parse_args()
    dispatch(args.repo, pr_url=args.pr_url or "", head_branch=args.head_branch or "", allow_draft=args.allow_draft)


if __name__ == "__main__":
    main()
