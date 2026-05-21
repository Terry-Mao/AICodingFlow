#!/usr/bin/env python3
"""Select the review skill path for a PR_DIFF_V1 snapshot."""

from __future__ import annotations

import argparse
import os
from pathlib import Path


CODE_REVIEW_SKILL = ".agents/skills/review-pr/SKILL.md"
SPEC_REVIEW_SKILL = ".agents/skills/review-spec/SKILL.md"
CODE_REVIEW_COMPANION_SKILL = ".agents/skills/review-pr-repo/SKILL.md"
SPEC_REVIEW_COMPANION_SKILL = ".agents/skills/review-spec-repo/SKILL.md"


def changed_files(pr_diff_text: str) -> list[str]:
    files: list[str] = []
    for line in pr_diff_text.splitlines():
        if line.startswith("FILE "):
            path = line[5:].strip()
            if path:
                files.append(path)
    return files


def is_spec_only(files: list[str]) -> bool:
    return bool(files) and all(path.startswith("specs/") for path in files)


def select_skill(pr_diff_text: str) -> str:
    files = changed_files(pr_diff_text)
    if is_spec_only(files):
        return skill_path(SPEC_REVIEW_COMPANION_SKILL, SPEC_REVIEW_SKILL)
    return skill_path(CODE_REVIEW_COMPANION_SKILL, CODE_REVIEW_SKILL)


def needs_spec_context(skill: str) -> bool:
    return skill in {CODE_REVIEW_SKILL, CODE_REVIEW_COMPANION_SKILL}


def skill_path(companion: str, core: str) -> str:
    return companion if Path(companion).is_file() else core


def write_github_output(name: str, value: str) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    with Path(output_path).open("a", encoding="utf-8") as output:
        output.write(f"{name}={value}\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--diff", default="pr_diff.txt")
    args = parser.parse_args()

    skill = select_skill(Path(args.diff).read_text(encoding="utf-8"))
    write_github_output("path", skill)
    write_github_output("needs_spec_context", "true" if needs_spec_context(skill) else "false")
    print(skill)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
