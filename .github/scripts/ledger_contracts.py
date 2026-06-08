"""Shared helpers for PR-keyed workflow ledgers."""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

from artifact_contracts import load_json, write_json


UTC = dt.timezone.utc


def now_iso() -> str:
    return dt.datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_ledger(path: Path, *, ledger_name: str) -> dict[str, Any]:
    if not path.exists():
        return {"version": 1, "entries": []}
    data = load_json(path)
    if not isinstance(data, dict):
        raise SystemExit(f"invalid {ledger_name} ledger: {path}")
    data.setdefault("version", 1)
    data.setdefault("entries", [])
    if not isinstance(data["entries"], list):
        raise SystemExit(f"invalid {ledger_name} ledger entries: {path}")
    return data


def entries_by_pr(ledger: dict[str, Any]) -> dict[int, dict[str, Any]]:
    entries: dict[int, dict[str, Any]] = {}
    for entry in ledger.get("entries") or []:
        try:
            entries[int(entry.get("pr"))] = entry
        except (TypeError, ValueError):
            continue
    return entries


def merge_commit_oid(pr: dict[str, Any]) -> str:
    merge_commit = pr.get("mergeCommit") or {}
    return merge_commit.get("oid") or ""


def sort_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(entries, key=lambda item: (item.get("merged_at") or "", int(item.get("pr") or 0)))


def set_sorted_entries(ledger: dict[str, Any], entries: list[dict[str, Any]]) -> dict[str, Any]:
    ledger["version"] = 1
    ledger["entries"] = sort_entries(entries)
    return ledger


def write_ledger(path: Path, ledger: dict[str, Any]) -> None:
    write_json(path, ledger)
