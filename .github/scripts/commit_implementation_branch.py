#!/usr/bin/env python3
"""Commit and push implementation changes produced by Codex."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from implementation_file_filters import TEMP_WORKFLOW_PATHS, is_generated_path, is_github_workflow_path


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
    return sorted(path for path in paths if path not in TEMP_WORKFLOW_PATHS and not is_generated_path(path))


def intended_files(metadata: dict[str, Any]) -> list[str]:
    files = metadata.get("intended_files") or []
    return sorted(dict.fromkeys(path.strip() for path in files if isinstance(path, str) and path.strip()))


def staged_paths() -> list[str]:
    output = run(["git", "diff", "--cached", "--name-only"], capture=True)
    return [line for line in output.splitlines() if line]


def print_path_list(label: str, paths: list[str]) -> None:
    print(f"{label}:", flush=True)
    if not paths:
        print("  (none)", flush=True)
        return
    for path in paths:
        print(f"  {path}", flush=True)


def existing_temp_workflow_paths() -> list[str]:
    return sorted(path for path in TEMP_WORKFLOW_PATHS if Path(path).exists())


def stage_implementation_changes(paths: list[str]) -> None:
    run(["git", "add", "-A", "--", *paths])
    temp_paths = existing_temp_workflow_paths()
    if temp_paths:
        run(["git", "reset", "--", *temp_paths])


def validate_staged_paths(paths: list[str]) -> None:
    generated = sorted(path for path in paths if is_generated_path(path))
    if generated:
        raise SystemExit("refusing to commit generated files: " + ", ".join(generated))


def workflow_paths(paths: list[str]) -> list[str]:
    return sorted(path for path in paths if is_github_workflow_path(path))


def workflow_update_token() -> str:
    return os.environ.get("WORKFLOW_UPDATE_TOKEN", "").strip()


def github_token() -> str:
    return os.environ.get("GITHUB_TOKEN", "").strip()


def push_repo(context: dict[str, Any]) -> str:
    return str(context.get("agent_push_repo_full_name") or context.get("repository") or "").strip()


def validate_workflow_push_permissions(paths: list[str], token: str) -> None:
    workflows = sorted(path for path in paths if is_github_workflow_path(path))
    if workflows and not token:
        raise SystemExit(
            "implementation changes include GitHub workflow files: "
            + ", ".join(workflows)
            + ". Set the WORKFLOW_UPDATE_TOKEN repository secret to a token with workflow-file write permission."
        )


def configure_workflow_push_token(repo: str, token: str) -> None:
    if not token:
        return
    run(["git", "config", "--local", "--unset-all", "http.https://github.com/.extraheader"], check=False)
    include_keys = run(
        ["git", "config", "--local", "--name-only", "--get-regexp", r"^includeIf\..*\.path$"],
        capture=True,
        check=False,
    )
    for key in include_keys.splitlines():
        key = key.strip()
        if key:
            run(["git", "config", "--local", "--unset-all", key], check=False)
    run(["git", "remote", "set-url", "origin", f"https://x-access-token:{token}@github.com/{repo}.git"])


def validate_intended_files(candidate_paths: list[str], intended_paths: list[str]) -> None:
    candidate_set = set(candidate_paths)
    intended_set = set(intended_paths)
    missing = sorted(intended_set - candidate_set)
    unexpected = sorted(candidate_set - intended_set)
    if missing:
        raise SystemExit("intended_files contains files without implementation changes: " + ", ".join(missing))
    if unexpected:
        raise SystemExit("implementation changed files not listed in intended_files: " + ", ".join(unexpected))


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
    repo = push_repo(context)
    intended_paths = intended_files(metadata)
    print_path_list("metadata intended_files", intended_paths)

    paths = implementation_paths(status_paths())
    print_path_list("implementation candidate paths before branch switch", paths)
    if not paths:
        return {"changed": "false", "branch": branch, "sha": ""}

    if not stash_worktree():
        return {"changed": "false", "branch": branch, "sha": ""}

    configure_workflow_push_token(repo, github_token())
    run(["git", "fetch", "origin", default_branch])
    switch_to_branch(branch, "HEAD")
    restore_stash()
    paths = implementation_paths(status_paths())
    print_path_list("implementation candidate paths after branch switch", paths)
    if not paths:
        return {"changed": "false", "branch": branch, "sha": ""}
    validate_intended_files(paths, intended_paths)

    configure_git(author_name, author_email)
    stage_implementation_changes(paths)
    staged = staged_paths()
    print_path_list("staged implementation paths", staged)
    if not staged:
        return {"changed": "false", "branch": branch, "sha": ""}
    validate_staged_paths(staged)
    token = workflow_update_token()
    workflow_staged = workflow_paths(staged)
    validate_workflow_push_permissions(staged, token)
    if workflow_staged and not repo:
        raise SystemExit("workflow context repository is required to push GitHub workflow file changes")

    run(["git", "commit", "-m", title])
    if workflow_staged:
        print_path_list("GitHub workflow paths require WORKFLOW_UPDATE_TOKEN", workflow_staged)
        configure_workflow_push_token(repo, token)
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
