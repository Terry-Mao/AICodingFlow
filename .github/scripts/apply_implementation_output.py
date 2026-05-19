#!/usr/bin/env python3
"""Apply implementation files emitted outside the Codex sandbox write surface."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any


OUTPUT_DIR = "implementation-output"
ALLOWED_PREFIX = ".agents/"


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path} is invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    return value


def safe_relative_path(path: Path) -> str:
    if path.is_absolute() or ".." in path.parts:
        raise SystemExit(f"unsafe output path: {path}")
    return path.as_posix()


def output_files(output_dir: Path) -> list[Path]:
    if not output_dir.exists():
        return []
    if not output_dir.is_dir():
        raise SystemExit(f"{output_dir} must be a directory")
    files: list[Path] = []
    for path in output_dir.rglob("*"):
        if path.is_dir():
            continue
        if path.is_symlink():
            raise SystemExit(f"refusing to apply symlink output: {path}")
        files.append(path)
    return sorted(files)


def validate_target(rel_path: str, intended: set[str]) -> None:
    if not rel_path.startswith(ALLOWED_PREFIX):
        raise SystemExit(f"implementation-output may only contain {ALLOWED_PREFIX} files: {rel_path}")
    if rel_path not in intended:
        raise SystemExit(f"implementation-output file is not listed in pr-metadata.json intended_files: {rel_path}")


def apply_output(output_dir: Path, repo_root: Path, metadata_path: Path) -> list[str]:
    files = output_files(output_dir)
    if not files:
        return []

    metadata = load_json(metadata_path)
    raw_intended = metadata.get("intended_files")
    if not isinstance(raw_intended, list):
        raise SystemExit("pr-metadata.json field intended_files must be a list when implementation-output is used")
    intended = {path for path in raw_intended if isinstance(path, str)}

    applied: list[str] = []
    for source in files:
        rel_path = safe_relative_path(source.relative_to(output_dir))
        validate_target(rel_path, intended)
        target = repo_root / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        applied.append(rel_path)
        print(f"applied {rel_path}", flush=True)
    return applied


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=OUTPUT_DIR)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--metadata", default="pr-metadata.json")
    args = parser.parse_args()

    apply_output(Path(args.output_dir), Path(args.repo_root), Path(args.metadata))


if __name__ == "__main__":
    main()
