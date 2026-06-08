#!/usr/bin/env python3
"""Update the product change report ledger after report generation."""

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


def load_ledger(path: Path) -> dict[str, Any]:
    return load_pr_ledger(path, ledger_name="product change report")


def build_entry(pr: dict[str, Any], context: dict[str, Any], recorded_at: str, status: str) -> dict[str, Any]:
    return {
        "pr": int(pr["number"]),
        "url": pr.get("url") or "",
        "title": pr.get("title") or "",
        "merged_at": pr.get("mergedAt") or "",
        "merge_commit": merge_commit_oid(pr),
        "status": status,
        "report_date": context["report_date"],
        "report_path": context["report_path"],
        "recorded_at": recorded_at,
    }


def update_ledger(ledger: dict[str, Any], context: dict[str, Any], recorded_at: str, status: str = "reported") -> dict[str, Any]:
    by_pr = entries_by_pr(ledger)

    for pr in context.get("reportable_prs") or []:
        pr_number = int(pr["number"])
        existing = by_pr.get(pr_number) or {}
        entry_recorded_at = recorded_at
        if existing.get("report_path") == context["report_path"] and existing.get("recorded_at"):
            entry_recorded_at = str(existing["recorded_at"])
        by_pr[pr_number] = build_entry(pr, context, entry_recorded_at, status)

    return set_sorted_entries(ledger, list(by_pr.values()))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--context", default="product-change-report-context.json")
    parser.add_argument("--ledger", default="")
    parser.add_argument("--status", choices=["reported", "scanned_no_update"], default="reported")
    args = parser.parse_args()

    context = load_json(Path(args.context))
    report_path = Path(context["report_path"])
    if args.status == "reported" and not report_path.exists():
        raise SystemExit(f"report file does not exist; refusing to update ledger: {report_path}")

    ledger_path = Path(args.ledger or context.get("ledger_path") or "docs/updates/.product-change-report-ledger.json")
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger = update_ledger(load_ledger(ledger_path), context, now_iso(), args.status)
    write_ledger(ledger_path, ledger)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
