#!/usr/bin/env python3
"""Validate product wiki compile output."""

from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
from pathlib import Path

from artifact_contracts import write_github_output


WIKI_ROOT = "docs/product/wiki/"
REQUIRED_FILES = {
    "docs/product/wiki/AGENTS.md",
    "docs/product/wiki/index.md",
    "docs/product/wiki/log.md",
    "docs/product/wiki/schema/README.md",
    "docs/product/wiki/schema/page-types.md",
    "docs/product/wiki/schema/linking.md",
    "docs/product/wiki/schema/query.md",
    "docs/product/wiki/schema/staging.md",
}
HANDOFF_FILES = {
    "product-wiki-raw.sha256",
}
FRONTMATTER_REQUIRED_TYPES = {"summary", "concept"}
FRONTMATTER_REQUIRED_STATUS = {"current", "proposed", "needs-review", "deprecated"}
FRONTMATTER_REQUIRED_CONFIDENCE = {"high", "medium", "low"}
FRONTMATTER_REQUIRED_SOURCE_STATUS = {"verified", "partial", "conflict"}
MAX_WIKI_PAGE_LINES = 400
MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def changed_paths() -> list[str]:
    result = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
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
        paths.append(path)
    return paths


def validate_write_surface(paths: list[str]) -> list[str]:
    invalid_paths = [
        path
        for path in paths
        if path not in HANDOFF_FILES
        and (not path.startswith(WIKI_ROOT) or not path.endswith(".md"))
    ]
    if invalid_paths:
        raise SystemExit("product wiki compile modified files outside docs/product/wiki Markdown: " + ", ".join(invalid_paths))

    wiki_paths = [path for path in paths if path.startswith(WIKI_ROOT)]
    non_markdown_wiki_paths = [path for path in wiki_paths if not path.endswith(".md")]
    if non_markdown_wiki_paths:
        raise SystemExit("product wiki compile wrote non-Markdown wiki files: " + ", ".join(non_markdown_wiki_paths))
    return wiki_paths


def existing_wiki_markdown(root: Path) -> list[Path]:
    wiki_root = root / WIKI_ROOT
    if not wiki_root.exists():
        return []
    return sorted(path for path in wiki_root.rglob("*.md") if path.is_file())


def has_raw_sources(root: Path) -> bool:
    raw_root = root / "docs/product/raw"
    return raw_root.exists() and any(path.is_file() for path in raw_root.rglob("*.md"))


def validate_required_files(root: Path, wiki_paths: list[str]) -> None:
    if not wiki_paths and not has_raw_sources(root):
        return
    missing = [path for path in sorted(REQUIRED_FILES) if not (root / path).is_file()]
    if missing:
        raise SystemExit("product wiki compile is missing required files: " + ", ".join(missing))


def parse_frontmatter(text: str, path: Path) -> dict[str, object] | None:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    data: dict[str, object] = {}
    index = 1
    while index < len(lines):
        line = lines[index]
        if line.strip() == "---":
            return data
        if ":" in line and not line.startswith((" ", "-")):
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            if value:
                data[key] = value.strip('"\'')
            else:
                items: list[str] = []
                index += 1
                while index < len(lines):
                    item_line = lines[index]
                    if item_line.strip() == "---":
                        index -= 1
                        break
                    if item_line.startswith("  - "):
                        items.append(item_line[4:].strip().strip('"\''))
                        index += 1
                        continue
                    index -= 1
                    break
                data[key] = items
        index += 1
    raise SystemExit(f"unterminated frontmatter: {path}")


def parse_frontmatter_date(value: object, field: str, relative: str) -> dt.date:
    if not isinstance(value, str) or not DATE_RE.match(value):
        raise SystemExit(f"{relative} frontmatter {field} must use YYYY-MM-DD")
    try:
        return dt.date.fromisoformat(value)
    except ValueError:
        raise SystemExit(f"{relative} frontmatter {field} must be a valid date")


def validate_frontmatter(root: Path) -> None:
    for path in existing_wiki_markdown(root):
        relative = path.relative_to(root).as_posix()
        if not (relative.startswith("docs/product/wiki/summaries/") or relative.startswith("docs/product/wiki/concepts/")):
            continue
        data = parse_frontmatter(path.read_text(encoding="utf-8"), path)
        if data is None:
            raise SystemExit(f"missing frontmatter: {relative}")
        page_type = data.get("type")
        if page_type not in FRONTMATTER_REQUIRED_TYPES:
            raise SystemExit(f"{relative} frontmatter type must be summary or concept")
        title = data.get("title")
        if not isinstance(title, str) or not title.strip():
            raise SystemExit(f"{relative} frontmatter title must be non-empty")
        sources = data.get("sources")
        if not isinstance(sources, list) or not sources or any(not isinstance(item, str) or not item.strip() for item in sources):
            raise SystemExit(f"{relative} frontmatter sources must be a non-empty list")
        status = data.get("status")
        if status not in FRONTMATTER_REQUIRED_STATUS:
            raise SystemExit(f"{relative} frontmatter status must be one of: {', '.join(sorted(FRONTMATTER_REQUIRED_STATUS))}")
        confidence = data.get("confidence")
        if confidence not in FRONTMATTER_REQUIRED_CONFIDENCE:
            raise SystemExit(f"{relative} frontmatter confidence must be one of: {', '.join(sorted(FRONTMATTER_REQUIRED_CONFIDENCE))}")
        source_status = data.get("source_status")
        if source_status not in FRONTMATTER_REQUIRED_SOURCE_STATUS:
            raise SystemExit(f"{relative} frontmatter source_status must be one of: {', '.join(sorted(FRONTMATTER_REQUIRED_SOURCE_STATUS))}")
        owner = data.get("owner")
        if not isinstance(owner, str) or not owner.strip():
            raise SystemExit(f"{relative} frontmatter owner must be non-empty")
        last_reviewed = parse_frontmatter_date(data.get("last_reviewed"), "last_reviewed", relative)
        review_due = parse_frontmatter_date(data.get("review_due"), "review_due", relative)
        if review_due < last_reviewed:
            raise SystemExit(f"{relative} frontmatter review_due must not be before last_reviewed")
        if relative.startswith("docs/product/wiki/summaries/") and page_type != "summary":
            raise SystemExit(f"{relative} must use type: summary")
        if relative.startswith("docs/product/wiki/concepts/") and page_type != "concept":
            raise SystemExit(f"{relative} must use type: concept")


def wiki_relative_path(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def wiki_links(root: Path, path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    links: set[str] = set()
    for match in MARKDOWN_LINK_RE.finditer(text):
        target = match.group(1).strip()
        if not target or "://" in target or target.startswith("#") or target.startswith("mailto:"):
            continue
        target = target.split("#", 1)[0].split("?", 1)[0]
        if not target.endswith(".md"):
            continue
        resolved = (path.parent / target).resolve()
        try:
            relative = resolved.relative_to(root.resolve()).as_posix()
        except ValueError:
            continue
        if relative.startswith(WIKI_ROOT):
            links.add(relative)
    return links


def validate_link_contract(root: Path) -> None:
    wiki_files = [wiki_relative_path(root, path) for path in existing_wiki_markdown(root)]
    if not wiki_files:
        return

    summaries = sorted(path for path in wiki_files if path.startswith("docs/product/wiki/summaries/"))
    concepts = sorted(path for path in wiki_files if path.startswith("docs/product/wiki/concepts/"))
    if has_raw_sources(root) and not summaries:
        raise SystemExit("product wiki compile requires at least one summary page when raw sources exist")
    if has_raw_sources(root) and not concepts:
        raise SystemExit("product wiki compile requires at least one concept page when raw sources exist")
    required_index_targets = sorted(REQUIRED_FILES | set(summaries) | set(concepts))
    index_path = root / "docs/product/wiki/index.md"
    index_links = wiki_links(root, index_path)
    missing_index_links = [path for path in required_index_targets if path != "docs/product/wiki/index.md" and path not in index_links]
    if missing_index_links:
        raise SystemExit("product wiki index is missing links: " + ", ".join(missing_index_links))

    concept_set = set(concepts)
    summary_set = set(summaries)
    if concept_set:
        for summary in summaries:
            links = wiki_links(root, root / summary)
            if not links.intersection(concept_set):
                raise SystemExit(f"{summary} must link to at least one concept page")
    if summary_set:
        for concept in concepts:
            links = wiki_links(root, root / concept)
            if not links.intersection(summary_set):
                raise SystemExit(f"{concept} must link to at least one summary page")


def validate_health_contract(root: Path) -> None:
    titles: dict[str, str] = {}
    for path in existing_wiki_markdown(root):
        relative = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        if len(lines) > MAX_WIKI_PAGE_LINES:
            raise SystemExit(f"{relative} exceeds {MAX_WIKI_PAGE_LINES} lines")
        if relative.startswith(("docs/product/wiki/summaries/", "docs/product/wiki/concepts/")):
            data = parse_frontmatter(text, path) or {}
            title = str(data.get("title", "")).strip()
            if title in titles:
                raise SystemExit(f"duplicate wiki title: {title} in {titles[title]} and {relative}")
            titles[title] = relative
            has_review_marker = "待确认" in text or "开放问题" in text
            has_review_section = "\n## 待确认" in text or "\n## 开放问题" in text
            if has_review_marker and not has_review_section:
                raise SystemExit(f"{relative} uses 待确认 or 开放问题 without a dedicated review section")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--github-output", default="")
    args = parser.parse_args()

    root = Path(args.root)
    wiki_paths = validate_write_surface(changed_paths())
    validate_required_files(root, wiki_paths)
    validate_frontmatter(root)
    validate_link_contract(root)
    validate_health_contract(root)
    write_github_output(
        args.github_output,
        {
            "changed": "true" if wiki_paths else "false",
            "changed_files": ",".join(sorted(wiki_paths)),
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
