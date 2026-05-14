#!/usr/bin/env python3
"""Commit and push implementation changes produced by Codex."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


TEMP_WORKFLOW_PATHS = {
    "issue_context.json",
    "issue_comments.txt",
    "spec_context.md",
    "branch-start-shas.json",
    "implementation_summary.md",
    "pr-metadata.json",
    "validation-output.txt",
    "validation-error.txt",
}


def run(args: list[str], *, capture: bool = False, check: bool = True) -> str:
    result = subprocess.run(
        args,
        check=check,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
        text=True,
    )
    return result.stdout.strip() if capture else ""


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def status_paths() -> list[str]:
    output = run(["git", "status", "--porcelain=v1", "--untracked-files=all", "-z"], capture=True)
    if not output:
        return []
    entries = output.split("\0")
    paths: list[str] = []
    index = 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if not entry:
            continue
        status = entry[:2]
        path = entry[3:]
        if status[0] == "R" or status[0] == "C":
            if index < len(entries) and entries[index]:
                index += 1
        if path:
            paths.append(path)
    return paths


def implementation_paths(paths: list[str]) -> list[str]:
    return sorted(path for path in paths if path not in TEMP_WORKFLOW_PATHS)


def has_remote_branch(branch: str) -> bool:
    result = subprocess.run(
        ["git", "ls-remote", "--exit-code", "--heads", "origin", branch],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.returncode == 0


def switch_to_branch(branch: str, base_ref: str) -> None:
    if has_remote_branch(branch):
        run(["git", "fetch", "origin", f"+refs/heads/{branch}:refs/remotes/origin/{branch}"])
        run(["git", "switch", "-C", branch, f"origin/{branch}"])
    else:
        run(["git", "switch", "-C", branch, base_ref])


def stash_worktree() -> bool:
    output = run(
        [
            "git",
            "stash",
            "push",
            "--include-untracked",
            "-m",
            "implementation workflow handoff",
        ],
        capture=True,
    )
    return "No local changes to save" not in output


def restore_stash() -> None:
    run(["git", "stash", "pop"])


def configure_git(author_name: str, author_email: str) -> None:
    run(["git", "config", "user.name", author_name])
    run(["git", "config", "user.email", author_email])


def commit_and_push(context_path: Path, metadata_path: Path, author_name: str, author_email: str) -> dict[str, str]:
    context = load_json(context_path)
    metadata = load_json(metadata_path)
    branch = metadata["branch_name"].strip()
    title = metadata["pr_title"].strip()
    default_branch = str(context.get("default_branch") or "main")

    paths = implementation_paths(status_paths())
    if not paths:
        return {"changed": "false", "branch": branch, "sha": ""}

    if not stash_worktree():
        return {"changed": "false", "branch": branch, "sha": ""}

    run(["git", "fetch", "origin", default_branch])
    switch_to_branch(branch, "HEAD")
    restore_stash()
    paths = implementation_paths(status_paths())
    if not paths:
        return {"changed": "false", "branch": branch, "sha": ""}

    configure_git(author_name, author_email)
    run(["git", "add", "--", *paths])
    staged = run(["git", "diff", "--cached", "--name-only"], capture=True)
    if not staged:
        return {"changed": "false", "branch": branch, "sha": ""}

    run(["git", "commit", "-m", title])
    run(["git", "push", "-u", "origin", branch])
    sha = run(["git", "rev-parse", "HEAD"], capture=True)
    return {"changed": "true", "branch": branch, "sha": sha}


def write_github_output(path: str | None, values: dict[str, str]) -> None:
    if not path:
        return
    with Path(path).open("a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", default="issue_context.json")
    parser.add_argument("--metadata", default="pr-metadata.json")
    parser.add_argument("--author-name", default="github-actions[bot]")
    parser.add_argument("--author-email", default="41898282+github-actions[bot]@users.noreply.github.com")
    parser.add_argument("--github-output", default="")
    args = parser.parse_args()

    result = commit_and_push(Path(args.context), Path(args.metadata), args.author_name, args.author_email)
    print(result["sha"])
    write_github_output(args.github_output, result)


if __name__ == "__main__":
    main()
