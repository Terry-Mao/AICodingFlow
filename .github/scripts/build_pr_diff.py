#!/usr/bin/env python3
"""Convert git diff output into PR_DIFF_V1 line annotations."""

from __future__ import annotations

import argparse
import re
import subprocess
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
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--output", default="pr_diff.txt")
    parser.add_argument("--context", type=int, default=3)
    args = parser.parse_args()

    diff_lines = run_git_diff(args.base, args.head, args.context)
    Path(args.output).write_text(convert(diff_lines), encoding="utf-8")


if __name__ == "__main__":
    main()
