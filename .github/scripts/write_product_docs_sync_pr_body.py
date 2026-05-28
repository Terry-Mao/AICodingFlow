#!/usr/bin/env python3
"""Write the product docs sync pull request body."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


DEFAULT_LEDGER_PATH = "docs/product/.product-docs-sync-ledger.json"


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
        f"  - reason: {entry.get('reason') or ''}",
        f"  - url: {entry.get('url') or ''}",
        "  - affected docs:",
        *format_list(entry.get("affected_docs") or []),
    ]
    proposed_patch = str(entry.get("proposed_patch") or "").strip()
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
    return "\n".join(
        [
            "Synchronizes long-term product docs from merged implementation pull requests.",
            "",
            "Latest decision:",
            f"- source PR: #{pr_number}",
            f"- docs update: `{result.get('docs_update')}`",
            f"- reason: {result.get('reason')}",
            f"- source URL: {pr_url}",
            "",
            "Affected docs:",
            *(f"- `{path}`" for path in affected_docs),
            "",
            "Source context:",
            *(f"- {item}" for item in source_context),
            "",
            "Patch summary:",
            str(result.get("proposed_patch") or ""),
            "",
            "Processed decisions in this PR:",
            *(
                line
                for entry in processed_entries
                for line in [*format_decision(entry), ""]
            ),
            "This PR may accumulate multiple product docs sync decisions until it is reviewed and merged.",
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", default="product-docs-sync-result.json")
    parser.add_argument("--ledger", default="")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = json.loads(Path(args.result).read_text(encoding="utf-8"))
    ledger_path = Path(args.ledger or os.environ.get("LEDGER_PATH") or DEFAULT_LEDGER_PATH)
    body = build_body(
        pr_number=os.environ["SOURCE_PR_NUMBER"],
        pr_url=os.environ.get("SOURCE_PR_URL", ""),
        result=result,
        ledger=load_ledger(ledger_path),
    )
    Path(args.output).write_text(body, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
