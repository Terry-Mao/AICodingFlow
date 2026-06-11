#!/usr/bin/env python3
"""Apply update-triage output files produced outside .agents/.github."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ALLOWED_FILES = {
    ".github/skills/triage-issue-repo/SKILL.md": "triage-issue-repo/SKILL.md",
    ".github/issue-triage/config.json": "issue-triage/config.json",
}
VALID_STATUSES = {"changed", "no_change", "error"}


def load_status(output_dir: Path) -> dict[str, Any]:
    status_path = output_dir / "status.json"
    if not status_path.is_file():
        raise SystemExit(f"missing update-triage status file: {status_path}")
    try:
        data = json.loads(status_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid update-triage status JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit("update-triage status must be a JSON object")
    return data


def validate_updated_files(updated_files: Any) -> list[str]:
    if not isinstance(updated_files, list):
        raise SystemExit("status.updated_files must be a list")
    if not updated_files:
        raise SystemExit("status.updated_files must not be empty when status is changed")
    for path in updated_files:
        if path not in ALLOWED_FILES:
            raise SystemExit(f"update-triage output path is not allowed: {path}")
    return sorted(set(updated_files))


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def read_proposed_file(source: Path, output_dir: Path) -> str:
    output_root = output_dir.resolve()
    try:
        resolved_source = source.resolve(strict=True)
    except FileNotFoundError:
        raise SystemExit(f"missing proposed update-triage file: {source}") from None
    if source.is_symlink():
        raise SystemExit(f"refusing to apply symlink output: {source}")
    if not is_relative_to(resolved_source, output_root):
        raise SystemExit(f"refusing to apply output outside output dir: {source}")
    if not source.is_file():
        raise SystemExit(f"missing proposed update-triage file: {source}")
    return source.read_text(encoding="utf-8")


def normalize_config_json(content: str, source: Path) -> str:
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid proposed label config JSON: {source}: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit("proposed label config must be a JSON object")
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def apply_output(output_dir: Path, repo_root: Path) -> str:
    status_data = load_status(output_dir)
    status = status_data.get("status")
    reason = status_data.get("reason", "")

    if status not in VALID_STATUSES:
        raise SystemExit(f"invalid update-triage status: {status!r}")
    if not isinstance(reason, str):
        raise SystemExit("status.reason must be a string")

    if status == "error":
        raise SystemExit(f"update-triage reported error: {reason}")
    if status == "no_change":
        print(f"update-triage reported no change: {reason}")
        return status

    updated_files = validate_updated_files(status_data.get("updated_files"))
    for destination in updated_files:
        source = output_dir / ALLOWED_FILES[destination]
        content = read_proposed_file(source, output_dir)
        if destination == ".github/issue-triage/config.json":
            content = normalize_config_json(content, source)
        target = repo_root / destination
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        print(f"applied {destination}")

    return status


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="update-triage-output")
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args()

    apply_output(Path(args.output_dir), Path(args.repo_root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
