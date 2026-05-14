#!/usr/bin/env python3
"""Read a GitHub branch head SHA and expose it as a workflow output."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


def run_gh_json(args: list[str]) -> Any | None:
    try:
        result = subprocess.run(["gh", *args], check=True, stdout=subprocess.PIPE, text=True)
    except subprocess.CalledProcessError:
        return None
    return json.loads(result.stdout)


def read_branch_sha(repo: str, branch: str) -> str:
    ref = run_gh_json(["api", f"repos/{repo}/git/ref/heads/{branch}"])
    if not isinstance(ref, dict):
        return ""
    obj = ref.get("object") or {}
    return obj.get("sha") or ""


def metadata_branch(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        metadata = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ""
    if not isinstance(metadata, dict):
        return ""
    branch = metadata.get("branch_name")
    return branch.strip() if isinstance(branch, str) else ""


def write_github_output(path: str | None, values: dict[str, str]) -> None:
    if not path:
        return
    with Path(path).open("a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True)
    parser.add_argument("--branch", required=True)
    parser.add_argument("--metadata", default="")
    parser.add_argument("--github-output", default="")
    args = parser.parse_args()

    branch = metadata_branch(Path(args.metadata)) if args.metadata else ""
    if not branch:
        branch = args.branch
    sha = read_branch_sha(args.repo, branch)
    print(sha)
    write_github_output(args.github_output, {"branch": branch, "sha": sha})


if __name__ == "__main__":
    main()
