#!/usr/bin/env python3
"""Update the product docs sync ledger after a sync decision."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any


UTC = dt.timezone.utc
DEFAULT_LEDGER_PATH = "docs/product/.product-docs-sync-ledger.json"


def now_iso() -> str:
    return dt.datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_ledger(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": 1, "entries": []}
    data = load_json(path)
    if not isinstance(data, dict):
        raise SystemExit(f"invalid product docs sync ledger: {path}")
    data.setdefault("version", 1)
    data.setdefault("entries", [])
    if not isinstance(data["entries"], list):
        raise SystemExit(f"invalid product docs sync ledger entries: {path}")
    return data


def merge_commit_oid(pr: dict[str, Any]) -> str:
    merge_commit = pr.get("mergeCommit") or {}
    return merge_commit.get("oid") or ""


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
    by_pr: dict[int, dict[str, Any]] = {}
    for entry in ledger.get("entries") or []:
        try:
            by_pr[int(entry.get("pr"))] = entry
        except (TypeError, ValueError):
            continue

    pr = context.get("pr") or {}
    pr_number = int(pr["number"])
    existing = by_pr.get(pr_number) or {}
    entry_recorded_at = str(existing.get("recorded_at") or recorded_at)
    by_pr[pr_number] = build_entry(context, result, entry_recorded_at)

    ledger["version"] = 1
    ledger["entries"] = sorted(by_pr.values(), key=lambda item: (item.get("merged_at") or "", int(item.get("pr") or 0)))
    return ledger


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
    ledger_path.write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
