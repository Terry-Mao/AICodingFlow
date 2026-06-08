#!/usr/bin/env python3
"""Update the product docs sync ledger after a sync decision."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from artifact_contracts import load_json
from ledger_contracts import (
    entries_by_pr,
    load_ledger as load_pr_ledger,
    merge_commit_oid,
    now_iso,
    set_sorted_entries,
    write_ledger,
)

DEFAULT_LEDGER_PATH = "docs/product/.product-docs-sync-ledger.json"


def load_ledger(path: Path) -> dict[str, Any]:
    return load_pr_ledger(path, ledger_name="product docs sync")


def build_entry(context: dict[str, Any], result: dict[str, Any], recorded_at: str) -> dict[str, Any]:
    pr = context.get("pr") or {}
    return {
        "pr": int(pr["number"]),
        "url": pr.get("url") or "",
        "title": pr.get("title") or "",
        "merged_at": pr.get("mergedAt") or "",
        "merge_commit": merge_commit_oid(pr),
        "docs_update": result["docs_update"],
        "affected_docs": result.get("affected_docs") or [],
        "source_context": result.get("source_context") or [],
        "proposed_patch": result.get("proposed_patch") or "",
        "reason": result.get("reason") or "",
        "recorded_at": recorded_at,
    }


def update_ledger(
    ledger: dict[str, Any],
    context: dict[str, Any],
    result: dict[str, Any],
    recorded_at: str,
) -> dict[str, Any]:
    by_pr = entries_by_pr(ledger)

    pr = context.get("pr") or {}
    pr_number = int(pr["number"])
    existing = by_pr.get(pr_number) or {}
    entry_recorded_at = str(existing.get("recorded_at") or recorded_at)
    by_pr[pr_number] = build_entry(context, result, entry_recorded_at)

    return set_sorted_entries(ledger, list(by_pr.values()))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", default="product-docs-sync-context.json")
    parser.add_argument("--result", default="product-docs-sync-result.json")
    parser.add_argument("--ledger", default="")
    args = parser.parse_args()

    context = load_json(Path(args.context))
    result = load_json(Path(args.result))
    ledger_path = Path(args.ledger or context.get("ledger_path") or DEFAULT_LEDGER_PATH)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger = update_ledger(load_ledger(ledger_path), context, result, now_iso())
    write_ledger(ledger_path, ledger)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
