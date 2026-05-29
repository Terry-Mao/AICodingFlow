#!/usr/bin/env python3
"""Write the product wiki compile pull request body."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


WIKI_ROOT = "docs/product/wiki/"


def changed_wiki_files() -> list[str]:
    result = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all", "--", "docs/product/wiki"],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    paths: list[str] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if path.startswith(WIKI_ROOT):
            paths.append(path)
    return sorted(paths)


def format_paths(paths: list[str]) -> list[str]:
    if not paths:
        return ["- none"]
    return [f"- `{path}`" for path in paths]


def build_body(paths: list[str]) -> str:
    changed = set(paths)
    has_index = "docs/product/wiki/index.md" in changed
    has_agents = "docs/product/wiki/AGENTS.md" in changed
    has_log = "docs/product/wiki/log.md" in changed
    has_schema = any(path.startswith("docs/product/wiki/schema/") for path in paths)
    has_summaries = any(path.startswith("docs/product/wiki/summaries/") for path in paths)
    has_concepts = any(path.startswith("docs/product/wiki/concepts/") for path in paths)

    return "\n".join(
        [
            "编译 `docs/product/raw/` 为 LLM Wiki 知识层。",
            "",
            "## Summary",
            "",
            "- source root: `docs/product/raw/`",
            "- target root: `docs/product/wiki/`",
            "- trigger: scheduled or manual product wiki compile",
            "",
            "## Ingest",
            "",
            f"- index updated: `{'yes' if has_index else 'no'}`",
            f"- AGENTS guide updated: `{'yes' if has_agents else 'no'}`",
            f"- summaries updated: `{'yes' if has_summaries else 'no'}`",
            f"- concepts updated: `{'yes' if has_concepts else 'no'}`",
            f"- schema updated: `{'yes' if has_schema else 'no'}`",
            f"- compile log updated: `{'yes' if has_log else 'no'}`",
            "",
            "## Changed Files",
            "",
            *format_paths(paths),
            "",
            "## Review Notes",
            "",
            "- `docs/product/raw/` remains the authoritative source of truth.",
            "- Review that summaries and concepts are traceable to raw sources.",
            "- Review any `待确认` or `开放问题` entries before relying on them as product truth.",
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    Path(args.output).write_text(build_body(changed_wiki_files()), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
