#!/usr/bin/env python3
"""Prepare root-level review snapshots for local PR review skills."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
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
    Path(".local_review_baseline.status"),
)
TEMP_REVIEW_PATH_NAMES = {path.as_posix() for path in TEMP_REVIEW_PATHS}
StatusRecord = tuple[str, str, str, str]


def run(args: list[str], env: dict[str, str] | None = None) -> str:
    result = subprocess.run(args, check=True, stdout=subprocess.PIPE, text=True, env=env)
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


def parse_status_records(raw: bytes) -> list[StatusRecord]:
    parts = raw.decode("utf-8", errors="replace").split("\0")
    records: list[StatusRecord] = []
    index = 0
    while index < len(parts):
        entry = parts[index]
        index += 1
        if not entry:
            continue
        status = entry[:2]
        path = entry[3:]
        source = ""
        if ("R" in status or "C" in status) and index < len(parts):
            source = parts[index]
            index += 1
        records.append((status[0], status[1], path, source))
    return records


def serialize_status_records(records: list[StatusRecord]) -> bytes:
    output = bytearray()
    for index_status, worktree_status, path, source in records:
        output.extend(f"{index_status}{worktree_status} {path}\0".encode("utf-8"))
        if source:
            output.extend(f"{source}\0".encode("utf-8"))
    return bytes(output)


def git_status_raw() -> bytes:
    return subprocess.run(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        check=True,
        stdout=subprocess.PIPE,
    ).stdout


def is_temp_review_path(path: str) -> bool:
    return Path(path).as_posix() in TEMP_REVIEW_PATH_NAMES


def filtered_status_records() -> list[StatusRecord]:
    return [record for record in parse_status_records(git_status_raw()) if not is_temp_review_path(record[2])]


def resolve_ref(ref: str) -> str:
    return run(["git", "rev-parse", ref])


def default_base() -> str:
    for ref in ("origin/main", "upstream/main", "main"):
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


def github_pr_event(repo: str, branch: str) -> dict[str, Any]:
    fields = ",".join(
        [
            "number",
            "state",
            "isDraft",
            "title",
            "body",
            "url",
            "author",
            "baseRefName",
            "baseRefOid",
            "headRefName",
            "headRefOid",
        ]
    )
    data = json.loads(run(["gh", "pr", "view", branch, "--repo", repo, "--json", fields]))
    return {
        "pull_request": {
            "number": data.get("number") or "",
            "state": data.get("state") or "",
            "draft": bool(data.get("isDraft")),
            "title": data.get("title") or "",
            "body": data.get("body") or "",
            "html_url": data.get("url") or "",
            "user": {"login": (data.get("author") or {}).get("login") or ""},
            "base": {
                "ref": data.get("baseRefName") or "",
                "sha": data.get("baseRefOid") or "",
                "repo": {"full_name": repo, "default_branch": data.get("baseRefName") or ""},
            },
            "head": {
                "ref": data.get("headRefName") or "",
                "sha": data.get("headRefOid") or "",
                "repo": {"full_name": repo},
            },
        }
    }


def github_pr_event_for_current_branch(repo: str) -> dict[str, Any] | None:
    branch = current_branch()
    try:
        return github_pr_event(repo, branch)
    except (OSError, json.JSONDecodeError, subprocess.CalledProcessError):
        return None


def pr_base_sha(event: dict[str, Any] | None) -> str:
    if not event:
        return ""
    return str(((event.get("pull_request") or {}).get("base") or {}).get("sha") or "")


def pr_base_ref(event: dict[str, Any] | None) -> str:
    if not event:
        return ""
    return str(((event.get("pull_request") or {}).get("base") or {}).get("ref") or "")


def sync_event_base(event: dict[str, Any], base: str, base_sha: str) -> None:
    pull_request = event.setdefault("pull_request", {})
    base_record = pull_request.setdefault("base", {})
    base_ref = display_base_ref(base)
    base_record["ref"] = base_ref
    base_record["sha"] = base_sha
    repo = base_record.setdefault("repo", {})
    repo["default_branch"] = base_ref


def run_git_with_index(args: list[str], index_path: str) -> str:
    env = os.environ.copy()
    env["GIT_INDEX_FILE"] = index_path
    return run(["git", *args], env=env)


def local_worktree_diff(base_sha: str, context_lines: int) -> list[str]:
    with tempfile.NamedTemporaryFile(prefix="local-review-index-", delete=False) as handle:
        index_path = handle.name
    Path(index_path).unlink(missing_ok=True)

    try:
        run_git_with_index(["read-tree", "HEAD"], index_path)
        for index_status, worktree_status, path, source in filtered_status_records():
            if source:
                run_git_with_index(["rm", "--cached", "-q", "--ignore-unmatch", "--", source], index_path)
            if not Path(path).exists() and (index_status == "D" or worktree_status == "D"):
                run_git_with_index(["rm", "--cached", "-q", "--ignore-unmatch", "--", path], index_path)
            elif Path(path).exists():
                run_git_with_index(["add", "--", path], index_path)

        diff = run_git_with_index(
            [
                "diff",
                "--cached",
                "--no-color",
                "--no-ext-diff",
                f"--unified={context_lines}",
                "--find-renames",
                base_sha,
            ],
            index_path,
        )
        return diff.splitlines()
    finally:
        Path(index_path).unlink(missing_ok=True)


def write_local_diff(base_sha: str, output: Path) -> str:
    raw_diff = local_worktree_diff(base_sha, 3)
    if not raw_diff:
        raise SystemExit(f"no local changes to review against {base_sha}")
    diff_text = build_pr_diff.convert(raw_diff)
    output.write_text(diff_text, encoding="utf-8")
    return diff_text


def write_baseline_status() -> str:
    records = filtered_status_records()
    path = Path(".local_review_baseline.status")
    path.write_bytes(serialize_status_records(records))
    return path.as_posix()


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
    parser.add_argument("--github-output", default=os.environ.get("GITHUB_OUTPUT", ""))
    args = parser.parse_args()

    remove_stale_review_files()

    repo = args.repo or default_repo()
    head_sha = resolve_ref(args.head)
    event = github_pr_event_for_current_branch(repo)

    if args.base:
        base = args.base
        base_sha = resolve_ref(base)
        if event:
            sync_event_base(event, base, base_sha)
    elif pr_base_sha(event):
        base_sha = pr_base_sha(event)
        base = pr_base_ref(event) or base_sha
    else:
        base = default_base()
        base_sha = resolve_ref(base)
        if event:
            sync_event_base(event, base, base_sha)

    if not event:
        event = local_pr_event(repo, base, base_sha, head_sha)

    Path("pr_description.txt").write_text(write_pr_description.format_pr_description(event), encoding="utf-8")
    pr_diff_text = write_local_diff(base_sha, Path("pr_diff.txt"))
    skill = select_review_skill.select_skill(pr_diff_text)

    needs_spec_context = select_review_skill.needs_spec_context(skill)
    write_spec_context_if_needed(repo, event, pr_diff_text, needs_spec_context)
    baseline_status_path = write_baseline_status()

    values = {
        "skill": skill,
        "needs_spec_context": "true" if needs_spec_context else "false",
        "base": base,
        "base_sha": base_sha,
        "head_sha": head_sha,
        "baseline_status_path": baseline_status_path,
    }
    write_github_output(args.github_output, values)
    for key, value in values.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
