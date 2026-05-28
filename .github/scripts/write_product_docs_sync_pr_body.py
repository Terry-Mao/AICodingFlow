#!/usr/bin/env python3
"""Write the product docs sync pull request body."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


def build_body(pr_number: str, pr_url: str, result: dict[str, Any]) -> str:
    affected_docs = result.get("affected_docs") or []
    source_context = result.get("source_context") or []
    return "\n".join(
        [
            f"Synchronizes long-term product docs after implementation PR #{pr_number}.",
            "",
            "Decision:",
            f"- docs update: `{result.get('docs_update')}`",
            f"- reason: {result.get('reason')}",
            f"- source PR: {pr_url}",
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
            "Long-term product docs are authoritative only after this PR is reviewed and merged.",
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", default="product-docs-sync-result.json")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    result = json.loads(Path(args.result).read_text(encoding="utf-8"))
    body = build_body(
        pr_number=os.environ["SOURCE_PR_NUMBER"],
        pr_url=os.environ.get("SOURCE_PR_URL", ""),
        result=result,
    )
    Path(args.output).write_text(body, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
