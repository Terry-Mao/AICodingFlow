#!/usr/bin/env python3
"""Write the product docs sync pull request body."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


DEFAULT_LEDGER_PATH = "docs/product/.product-docs-sync-ledger.json"
MAX_GITHUB_MARKDOWN_CHARS = 60_000
MAX_FIELD_CHARS = 4_000
MAX_LEDGER_FIELD_CHARS = 800
MAX_LEDGER_ENTRIES_IN_BODY = 20


def truncate_text(value: Any, max_chars: int, *, label: str = "content") -> str:
    text = str(value or "").strip()
    if len(text) <= max_chars:
        return text
    suffix = f"\n\n[Truncated {label}; full content is available in workflow artifacts.]"
    return text[: max(0, max_chars - len(suffix))].rstrip() + suffix


def enforce_markdown_limit(markdown: str, max_chars: int = MAX_GITHUB_MARKDOWN_CHARS) -> str:
    if len(markdown) <= max_chars:
        return markdown
    suffix = "\n\n[Truncated to stay within GitHub body length limits. See workflow artifacts for full details.]\n"
    return markdown[: max(0, max_chars - len(suffix))].rstrip() + suffix


def load_ledger(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": 1, "entries": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"invalid product docs sync ledger: {path}")
    entries = data.get("entries")
    if not isinstance(entries, list):
        raise SystemExit(f"invalid product docs sync ledger entries: {path}")
    return data


def format_list(values: list[Any]) -> list[str]:
    items = [str(value) for value in values if str(value)]
    if not items:
        return ["  - none"]
    return [f"  - `{item}`" for item in items]


def format_decision(entry: dict[str, Any]) -> list[str]:
    pr_number = entry.get("pr")
    title = str(entry.get("title") or "").strip()
    heading = f"- PR #{pr_number}"
    if title:
        heading += f": {title}"
    lines = [
        heading,
        f"  - docs update: `{entry.get('docs_update')}`",
        f"  - reason: {truncate_text(entry.get('reason') or '', MAX_LEDGER_FIELD_CHARS, label='reason')}",
        f"  - url: {entry.get('url') or ''}",
        "  - affected docs:",
        *format_list(entry.get("affected_docs") or []),
    ]
    proposed_patch = truncate_text(
        entry.get("proposed_patch") or "",
        MAX_LEDGER_FIELD_CHARS,
        label="change summary",
    )
    if proposed_patch:
        lines.extend(["  - change summary:", *[f"    {line}" for line in proposed_patch.splitlines()]])
    return lines


def ledger_entries(ledger: dict[str, Any]) -> list[dict[str, Any]]:
    entries = [entry for entry in ledger.get("entries") or [] if isinstance(entry, dict)]
    return sorted(entries, key=lambda item: (item.get("merged_at") or "", int(item.get("pr") or 0)))


def build_body(pr_number: str, pr_url: str, result: dict[str, Any], ledger: dict[str, Any] | None = None) -> str:
    affected_docs = result.get("affected_docs") or []
    source_context = result.get("source_context") or []
    processed_entries = ledger_entries(ledger or {})
    shown_entries = processed_entries[-MAX_LEDGER_ENTRIES_IN_BODY:]
    omitted_count = max(0, len(processed_entries) - len(shown_entries))
    omitted_lines = (
        [f"- Omitted {omitted_count} older processed decisions to keep the PR body within GitHub limits.", ""]
        if omitted_count
        else []
    )
    body = "\n".join(
        [
            "Synchronizes long-term product docs from merged implementation pull requests.",
            "",
            "Latest decision:",
            f"- source PR: #{pr_number}",
            f"- docs update: `{result.get('docs_update')}`",
            f"- reason: {truncate_text(result.get('reason'), MAX_FIELD_CHARS, label='reason')}",
            f"- source URL: {pr_url}",
            "",
            "Affected docs:",
            *(f"- `{path}`" for path in affected_docs),
            "",
            "Source context:",
            *(f"- {item}" for item in source_context),
            "",
            "Patch summary:",
            truncate_text(result.get("proposed_patch"), MAX_FIELD_CHARS, label="patch summary"),
            "",
            "Processed decisions in this PR:",
            *omitted_lines,
            *(
                line
                for entry in shown_entries
                for line in [*format_decision(entry), ""]
            ),
            "This PR may accumulate multiple product docs sync decisions until it is reviewed and merged.",
            "",
        ]
    )
    return enforce_markdown_limit(body)


def build_comment(pr_number: str, pr_url: str, result: dict[str, Any]) -> str:
    affected_docs = result.get("affected_docs") or []
    lines = [
        "Product Docs Sync processed a source PR.",
        "",
        f"- source PR: #{pr_number}",
        f"- docs update: `{result.get('docs_update')}`",
        f"- reason: {truncate_text(result.get('reason'), MAX_FIELD_CHARS, label='reason')}",
        f"- source URL: {pr_url}",
        "",
        "Affected docs:",
        *(f"- `{path}`" for path in affected_docs),
    ]
    if not affected_docs:
        lines.append("- none")

    proposed_patch = truncate_text(result.get("proposed_patch") or "", MAX_FIELD_CHARS, label="patch summary")
    lines.extend(["", "Patch summary:", proposed_patch or "None."])
    if result.get("docs_update") == "uncertain":
        lines.extend(["", "This docs update is uncertain and needs maintainer confirmation."])
    lines.append("")
    return enforce_markdown_limit("\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", default="product-docs-sync-result.json")
    parser.add_argument("--ledger", default="")
    parser.add_argument("--output", required=True)
    parser.add_argument("--comment-output", default="")
    args = parser.parse_args()

    result = json.loads(Path(args.result).read_text(encoding="utf-8"))
    pr_number = os.environ["SOURCE_PR_NUMBER"]
    pr_url = os.environ.get("SOURCE_PR_URL", "")
    ledger_path = Path(args.ledger or os.environ.get("LEDGER_PATH") or DEFAULT_LEDGER_PATH)
    body = build_body(
        pr_number=pr_number,
        pr_url=pr_url,
        result=result,
        ledger=load_ledger(ledger_path),
    )
    Path(args.output).write_text(body, encoding="utf-8")
    if args.comment_output:
        Path(args.comment_output).write_text(build_comment(pr_number, pr_url, result), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
