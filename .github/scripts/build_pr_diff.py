#!/usr/bin/env python3
"""Convert git diff output into PR_DIFF_V1 line annotations."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import urllib.error
import urllib.request
from pathlib import Path


HUNK_RE = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@(.*)$")


def run_git_diff(base: str, head: str, context: int) -> list[str]:
    result = subprocess.run(
        [
            "git",
            "diff",
            "--no-color",
            "--no-ext-diff",
            f"--unified={context}",
            "--find-renames",
            base,
            head,
        ],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    return result.stdout.splitlines()


def github_request(repo: str, pr_number: str, token: str, accept: str) -> bytes:
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/pulls/{pr_number}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": accept,
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(request) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(detail)
            message = payload.get("message")
            if isinstance(message, str) and message:
                detail = message
        except json.JSONDecodeError:
            pass
        raise SystemExit(f"GitHub PR diff request failed: {exc.code} {detail}") from exc


def fetch_github_pr_metadata(repo: str, pr_number: str, token: str) -> dict[str, object]:
    raw = github_request(repo, pr_number, token, "application/vnd.github+json")
    metadata = json.loads(raw.decode("utf-8"))
    if not isinstance(metadata, dict):
        raise SystemExit("GitHub PR metadata response was not an object")
    return metadata


def nested_sha(metadata: dict[str, object], key: str) -> str:
    value = metadata.get(key)
    if not isinstance(value, dict):
        return ""
    sha = value.get("sha")
    return sha if isinstance(sha, str) else ""


def validate_github_pr_snapshot(
    metadata: dict[str, object],
    expected_head_sha: str,
    expected_base_sha: str,
) -> None:
    current_head_sha = nested_sha(metadata, "head")
    current_base_sha = nested_sha(metadata, "base")
    if current_head_sha != expected_head_sha:
        raise SystemExit(
            "GitHub PR head changed while preparing review diff: "
            f"expected {expected_head_sha}, got {current_head_sha or '<missing>'}"
        )
    if current_base_sha != expected_base_sha:
        raise SystemExit(
            "GitHub PR base changed while preparing review diff: "
            f"expected {expected_base_sha}, got {current_base_sha or '<missing>'}"
        )


def fetch_github_pr_diff(
    repo: str,
    pr_number: str,
    token: str,
    expected_head_sha: str,
    expected_base_sha: str,
) -> list[str]:
    metadata = fetch_github_pr_metadata(repo, pr_number, token)
    validate_github_pr_snapshot(metadata, expected_head_sha, expected_base_sha)
    diff_lines = github_request(repo, pr_number, token, "application/vnd.github.diff").decode("utf-8").splitlines()
    metadata = fetch_github_pr_metadata(repo, pr_number, token)
    validate_github_pr_snapshot(metadata, expected_head_sha, expected_base_sha)
    return diff_lines


def clean_path(path: str) -> str:
    if path == "/dev/null":
        return path
    if path.startswith("a/") or path.startswith("b/"):
        return path[2:]
    return path


def emit_file(output: list[str], current_file: str | None, next_file: str) -> str:
    if current_file is not None:
        output.append("END_FILE")
        output.append("")
    output.append(f"FILE {next_file}")
    return next_file


def diff_git_new_path(line: str) -> str:
    parts = line.split(" ", 3)
    if len(parts) < 4:
        return ""
    return clean_path(parts[3])


def emit_metadata_only_file(output: list[str], path: str) -> None:
    if path and path != "/dev/null":
        output.append(f"FILE {path}")
        output.append("END_FILE")


def convert(lines: list[str]) -> str:
    output = ["# PR_DIFF_V1"]
    current_file: str | None = None
    metadata_only_path: str | None = None
    pending_old: str | None = None
    pending_new: str | None = None
    old_line: int | None = None
    new_line: int | None = None
    in_hunk = False

    for line in lines:
        if line.startswith("diff --git "):
            if current_file is not None:
                output.append("END_FILE")
                output.append("")
                current_file = None
            elif metadata_only_path is not None:
                emit_metadata_only_file(output, metadata_only_path)
                output.append("")
            in_hunk = False
            metadata_only_path = diff_git_new_path(line)
            pending_old = None
            pending_new = None
            continue

        if not in_hunk and line.startswith("--- "):
            pending_old = clean_path(line[4:].split("\t", 1)[0])
            continue

        if not in_hunk and line.startswith("+++ "):
            pending_new = clean_path(line[4:].split("\t", 1)[0])
            path = pending_new if pending_new != "/dev/null" else pending_old
            if path and path != "/dev/null":
                current_file = emit_file(output, current_file, path)
                metadata_only_path = None
            continue

        hunk = HUNK_RE.match(line)
        if hunk and current_file:
            old_line = int(hunk.group(1))
            new_line = int(hunk.group(2))
            output.append(f"HUNK {line}")
            in_hunk = True
            continue

        if not in_hunk or current_file is None:
            continue
        if line.startswith("\\ No newline at end of file"):
            continue
        if old_line is None or new_line is None:
            continue

        marker = line[:1]
        content = line[1:]
        if marker == " ":
            output.append(f"BOTH  {new_line:>4} | {content}")
            old_line += 1
            new_line += 1
        elif marker == "-":
            output.append(f"LEFT  {old_line:>4} | {content}")
            old_line += 1
        elif marker == "+":
            output.append(f"RIGHT {new_line:>4} | {content}")
            new_line += 1

    if current_file is not None:
        output.append("END_FILE")
    elif metadata_only_path is not None:
        emit_metadata_only_file(output, metadata_only_path)

    return "\n".join(output) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--base")
    source.add_argument("--repo")
    parser.add_argument("--head")
    parser.add_argument("--head-sha")
    parser.add_argument("--base-sha")
    parser.add_argument("--pr-number")
    parser.add_argument("--output", default="pr_diff.txt")
    parser.add_argument("--context", type=int, default=3)
    parser.add_argument("--token-env", default="GITHUB_TOKEN")
    args = parser.parse_args()

    if args.repo:
        if not args.pr_number:
            raise SystemExit("--pr-number is required with --repo")
        if not args.head_sha:
            raise SystemExit("--head-sha is required with --repo")
        if not args.base_sha:
            raise SystemExit("--base-sha is required with --repo")
        token = os.environ.get(args.token_env)
        if not token:
            raise SystemExit(f"{args.token_env} is not set")
        diff_lines = fetch_github_pr_diff(args.repo, args.pr_number, token, args.head_sha, args.base_sha)
    else:
        if not args.head:
            raise SystemExit("--head is required with --base")
        diff_lines = run_git_diff(args.base, args.head, args.context)
    Path(args.output).write_text(convert(diff_lines), encoding="utf-8")


if __name__ == "__main__":
    main()
