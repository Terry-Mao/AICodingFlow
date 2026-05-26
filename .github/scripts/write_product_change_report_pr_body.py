#!/usr/bin/env python3
"""Write the product change report pull request body."""

from __future__ import annotations

import argparse
import os
from pathlib import Path


def build_body(report_date: str, report_path: str, scanned_pr_count: str, reportable_pr_count: str, ledger_path: str) -> str:
    return "\n".join(
        [
            f"Generates the product change report for `{report_date}`.",
            "",
            "Source scan:",
            f"- scanned merged PRs: {scanned_pr_count}",
            f"- reportable merged PRs: {reportable_pr_count}",
            "- scan window: the report date in UTC, start inclusive and next day exclusive",
            "- processing order: `mergedAt` ascending, then PR number ascending",
            f"- ledger: `{ledger_path}`",
            "",
            "Output:",
            f"- `{report_path}`",
            "",
            "This report is a time-series update artifact. It does not modify authoritative product docs or compiled wiki pages.",
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    body = build_body(
        report_date=os.environ["REPORT_DATE"],
        report_path=os.environ["REPORT_PATH"],
        scanned_pr_count=os.environ["SCANNED_PR_COUNT"],
        reportable_pr_count=os.environ["REPORTABLE_PR_COUNT"],
        ledger_path=os.environ["LEDGER_PATH"],
    )
    Path(args.output).write_text(body, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
