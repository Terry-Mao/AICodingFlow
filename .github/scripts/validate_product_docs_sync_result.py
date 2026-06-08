#!/usr/bin/env python3
"""Validate product docs sync output and write workflow decision outputs."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from artifact_contracts import write_github_output


VALID_DECISIONS = {"required", "uncertain", "not-needed"}
LEDGER_FILE = "docs/product/.product-docs-sync-ledger.json"
HANDOFF_FILES = {
    "product-docs-sync-context.json",
    "product-docs-sync-context.md",
    "product-docs-sync-diff.md",
    "product-docs-existing.md",
    "product-docs-sync-result.json",
    "product-docs-sync-context.sha256",
}


def load_result(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"missing product docs sync result: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("product docs sync result must be a JSON object")
    return data


def validate_schema(data: dict[str, Any]) -> str:
    decision = data.get("docs_update")
    if decision not in VALID_DECISIONS:
        raise SystemExit("docs_update must be one of: required, uncertain, not-needed")
    for key in ("reason", "proposed_patch"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise SystemExit(f"{key} must be a non-empty string")
    for key in ("affected_docs", "source_context"):
        value = data.get(key)
        if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
            raise SystemExit(f"{key} must be a list of non-empty strings")
    return str(decision)


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


def validate_write_surface(decision: str, paths: list[str]) -> list[str]:
    product_doc_paths = [
        path
        for path in paths
        if path.startswith("docs/product/")
        and path != LEDGER_FILE
        and path.endswith(".md")
    ]
    invalid_paths = [
        path
        for path in paths
        if path not in HANDOFF_FILES
        and path != LEDGER_FILE
        and (not path.startswith("docs/product/") or not path.endswith(".md"))
    ]
    if invalid_paths:
        raise SystemExit("product docs sync modified files outside docs/product: " + ", ".join(invalid_paths))
    if decision in {"required", "uncertain"} and not product_doc_paths:
        raise SystemExit(f"docs_update={decision} requires at least one docs/product change")
    if decision == "not-needed" and product_doc_paths:
        raise SystemExit("docs_update=not-needed must not modify docs/product")
    return product_doc_paths


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", default="product-docs-sync-result.json")
    parser.add_argument("--github-output", default="")
    args = parser.parse_args()

    result = load_result(Path(args.result))
    decision = validate_schema(result)
    docs_paths = validate_write_surface(decision, changed_paths())
    write_github_output(
        args.github_output,
        {
            "docs_update": decision,
            "should_create_pr": "true" if decision in {"required", "uncertain"} else "false",
            "draft": "true" if decision == "uncertain" else "false",
            "changed_docs": ",".join(docs_paths),
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
