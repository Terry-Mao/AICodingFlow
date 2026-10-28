#!/usr/bin/env python3
"""Prepare a pinned repository review cycle and issue snapshot."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
from pathlib import Path
from zoneinfo import ZoneInfo

from github_api import flatten_gh_pages, run_gh_json

DEFAULT_CYCLE_DAYS = 7
MAX_CYCLE_DAYS = 90
SOURCE_SUFFIXES = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".java",
    ".kt", ".c", ".h", ".cc", ".cpp", ".cs", ".rb", ".php",
    ".sh", ".bash", ".zsh", ".yml", ".yaml", ".toml", ".json",
    ".pyi", ".swift", ".scala", ".sql", ".vue", ".svelte", ".dart",
    ".lua", ".ex", ".exs", ".hs", ".fs", ".fsx", ".tf", ".hcl",
    ".proto", ".graphql", ".astro",
}
SPECIAL_NAMES = {"Dockerfile", "Makefile", "Justfile"}
EXCLUDED_PARTS = {
    "docs", "specs", "tests", "test", "fixtures", "vendor", "node_modules",
    "dist", "build", "generated", "__pycache__", ".worktrees", "aicodingflow-tests",
}
EXCLUDED_NAMES = {"package-lock.json", "pnpm-lock.yaml", "yarn.lock", "Cargo.lock"}


def parse_cycle_days(value: str) -> int:
    try:
        days = int(value)
    except ValueError as exc:
        raise SystemExit("--cycle-days must be an integer") from exc
    if not 1 <= days <= MAX_CYCLE_DAYS:
        raise SystemExit(f"--cycle-days must be between 1 and {MAX_CYCLE_DAYS}")
    return days


def shard_for_path(path: str, cycle_days: int) -> int:
    return int.from_bytes(hashlib.sha256(path.encode("utf-8")).digest()[:8], "big") % cycle_days


def selected_shard(value: str, scan_date: dt.date, cycle_days: int) -> int:
    if not value:
        return scan_date.toordinal() % cycle_days
    if value not in {str(number) for number in range(cycle_days)}:
        raise SystemExit(f"--shard must be an integer from 0 through {cycle_days - 1}")
    return int(value)


def is_reviewable_path(path: str) -> bool:
    item = Path(path)
    if any(part in EXCLUDED_PARTS for part in item.parts) or item.name in EXCLUDED_NAMES:
        return False
    if item.name.endswith((".min.js", ".min.css")):
        return False
    if item.suffix == ".md":
        return path.startswith((".agents/skills/", ".github/skills/")) and item.name == "SKILL.md"
    return item.suffix in SOURCE_SUFFIXES or item.name in SPECIAL_NAMES


def tracked_paths() -> list[str]:
    result = subprocess.run(["git", "ls-files", "-z"], check=True, stdout=subprocess.PIPE)
    return [item.decode("utf-8") for item in result.stdout.split(b"\0") if item]


def snapshot_files(root: Path, paths: list[str]) -> list[dict[str, object]]:
    files = []
    for path in sorted(paths):
        if not is_reviewable_path(path):
            continue
        full_path = root / path
        if full_path.is_symlink() or not full_path.is_file():
            continue
        data = full_path.read_bytes()
        if b"\0" in data:
            continue
        try:
            source = data.decode("utf-8")
        except UnicodeDecodeError:
            continue
        files.append({
            "path": path,
            "sha256": hashlib.sha256(data).hexdigest(),
            "line_count": len(source.splitlines()),
        })
    return files


def focus_files(project_files: list[dict[str, object]], shard: int, cycle_days: int) -> list[dict[str, object]]:
    focused = [item for item in project_files if shard_for_path(str(item["path"]), cycle_days) == shard]
    if focused or not project_files:
        return focused
    # Sparse projects still get a project-level review on every scheduled day.
    return [project_files[shard % len(project_files)]]


def issue_snapshot(repo: str) -> list[dict[str, object]]:
    pages = run_gh_json(["api", f"repos/{repo}/issues?state=all&per_page=100", "--paginate", "--slurp"])
    issues = []
    for item in flatten_gh_pages(pages):
        if item.get("pull_request") or not isinstance(item.get("number"), int):
            continue
        issues.append({
            "number": item["number"],
            "title": str(item.get("title") or ""),
            "body": str(item.get("body") or "")[:4000],
            "state": str(item.get("state") or ""),
            "url": str(item.get("html_url") or ""),
        })
    return issues


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--shard", default="")
    parser.add_argument("--cycle-days", default=str(DEFAULT_CYCLE_DAYS))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()

    root = Path.cwd()
    scan_date = dt.datetime.now(ZoneInfo("Asia/Shanghai")).date()
    cycle_days = parse_cycle_days(args.cycle_days)
    shard = selected_shard(args.shard, scan_date, cycle_days)
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True
    ).stdout.strip()
    project_files = snapshot_files(root, tracked_paths())
    files = focus_files(project_files, shard, cycle_days)
    context = {
        "commit": commit,
        "scan_date": scan_date.isoformat(),
        "shard": shard,
        "cycle_days": cycle_days,
        "project_files": project_files,
        "files": files,
    }
    write_json(args.output_dir / "context.json", context)
    write_json(args.output_dir / "issues.json", issue_snapshot(args.repo) if files else [])
    if args.github_output:
        with args.github_output.open("a", encoding="utf-8") as output:
            output.write(f"file_count={len(files)}\nshard={shard}\ncycle_days={cycle_days}\n")
    print(f"Nightly review: shard {shard}/{cycle_days}, {len(files)} focus files of {len(project_files)}, commit {commit}")


if __name__ == "__main__":
    main()
