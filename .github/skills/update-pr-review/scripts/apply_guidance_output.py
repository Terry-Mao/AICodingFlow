#!/usr/bin/env python3
"""Apply update-pr-review output files produced outside .agents."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ALLOWED_FILES = {
    ".github/skills/review-pr-repo/SKILL.md": "review-pr-repo/SKILL.md",
    ".github/skills/review-spec-repo/SKILL.md": "review-spec-repo/SKILL.md",
}
VALID_STATUSES = {"changed", "no_change", "error"}


def load_status(output_dir: Path) -> dict[str, Any]:
    status_path = output_dir / "status.json"
    if not status_path.is_file():
        raise SystemExit(f"missing update-pr-review status file: {status_path}")
    try:
        data = json.loads(status_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid update-pr-review status JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit("update-pr-review status must be a JSON object")
    return data


def validate_updated_files(updated_files: Any) -> list[str]:
    if not isinstance(updated_files, list):
        raise SystemExit("status.updated_files must be a list")
    if not updated_files:
        raise SystemExit("status.updated_files must not be empty when status is changed")
    for path in updated_files:
        if path not in ALLOWED_FILES:
            raise SystemExit(f"update-pr-review output path is not allowed: {path}")
    return sorted(set(updated_files))


def apply_output(output_dir: Path, repo_root: Path) -> str:
    status_data = load_status(output_dir)
    status = status_data.get("status")
    reason = status_data.get("reason", "")

    if status not in VALID_STATUSES:
        raise SystemExit(f"invalid update-pr-review status: {status!r}")
    if not isinstance(reason, str):
        raise SystemExit("status.reason must be a string")

    if status == "error":
        raise SystemExit(f"update-pr-review reported error: {reason}")
    if status == "no_change":
        print(f"update-pr-review reported no change: {reason}")
        return status

    updated_files = validate_updated_files(status_data.get("updated_files"))
    for destination in updated_files:
        source = output_dir / ALLOWED_FILES[destination]
        if not source.is_file():
            raise SystemExit(f"missing proposed guidance file: {source}")
        target = repo_root / destination
        target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        print(f"applied {destination}")

    return status


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="update-pr-review-output")
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args()

    apply_output(Path(args.output_dir), Path(args.repo_root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
