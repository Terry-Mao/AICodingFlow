#!/usr/bin/env python3
"""Read GitHub branch head SHAs and expose them as workflow outputs."""

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


def matching_branch_shas(repo: str, branch_prefix: str) -> dict[str, str]:
    refs = run_gh_json(["api", f"repos/{repo}/git/matching-refs/heads/{branch_prefix}"])
    if not isinstance(refs, list):
        return {}
    shas: dict[str, str] = {}
    for ref in refs:
        if not isinstance(ref, dict):
            continue
        name = str(ref.get("ref") or "").removeprefix("refs/heads/")
        if name != branch_prefix and not name.startswith(f"{branch_prefix}-"):
            continue
        obj = ref.get("object") or {}
        sha = obj.get("sha")
        if isinstance(sha, str) and sha:
            shas[name] = sha
    return shas


def write_snapshot(path: Path, shas: dict[str, str]) -> None:
    path.write_text(json.dumps(shas, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_snapshot(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(value, dict):
        return {}
    return {str(key): value for key, value in value.items() if isinstance(value, str)}


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


def changed_branches(start_shas: dict[str, str], end_shas: dict[str, str]) -> list[str]:
    return sorted(
        branch
        for branch, sha in end_shas.items()
        if sha and sha != start_shas.get(branch, "")
    )


def end_state(repo: str, branch_prefix: str, metadata_path: Path | None, snapshot_path: Path | None) -> dict[str, str]:
    start_shas = read_snapshot(snapshot_path) if snapshot_path else {}
    end_shas = matching_branch_shas(repo, branch_prefix)

    metadata_ref = metadata_branch(metadata_path) if metadata_path else ""
    changed = changed_branches(start_shas, end_shas)
    branch = metadata_ref or branch_prefix
    sha = end_shas.get(branch, "")
    if metadata_ref and not sha:
        sha = read_branch_sha(repo, metadata_ref)
    start_sha = start_shas.get(branch, "")

    return {
        "branch": branch,
        "sha": sha,
        "start_sha": start_sha,
        "changed": "true" if (sha and sha != start_sha) or (not metadata_ref and changed) else "false",
        "changed_branches": ",".join(changed),
    }


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
    parser.add_argument("--snapshot", default="")
    parser.add_argument("--snapshot-output", default="")
    parser.add_argument("--github-output", default="")
    args = parser.parse_args()

    if args.snapshot_output:
        shas = matching_branch_shas(args.repo, args.branch)
        if args.branch not in shas:
            sha = read_branch_sha(args.repo, args.branch)
            if sha:
                shas[args.branch] = sha
        write_snapshot(Path(args.snapshot_output), shas)
        write_github_output(args.github_output, {"branch": args.branch, "sha": shas.get(args.branch, "")})
        print(shas.get(args.branch, ""))
        return

    state = end_state(
        args.repo,
        args.branch,
        Path(args.metadata) if args.metadata else None,
        Path(args.snapshot) if args.snapshot else None,
    )
    print(state["sha"])
    write_github_output(args.github_output, state)


if __name__ == "__main__":
    main()
