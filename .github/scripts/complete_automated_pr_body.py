#!/usr/bin/env python3
"""Add concrete review sections to workflow-generated PR bodies."""

from __future__ import annotations

import argparse
from pathlib import Path

from validate_pr_body import parse_sections, validate_body


HEADINGS = ("Summary", "Testing", "Risk", "How to revert")


def complete_body(body: str, workflow_name: str, risk: str) -> str:
    result = body.strip()
    if "summary" not in parse_sections(result)[1]:
        result = f"## Summary\n\n{result}"
    defaults = {
        "Summary": f"由 {workflow_name} 生成；具体变更见本 PR 的文件改动。",
        "Testing": f"由 {workflow_name} 生成；校验结果见对应的 GitHub Actions run。",
        "Risk": f"{risk}：自动生成内容可能不准确，需要在 PR 中核对。",
        "How to revert": "回滚此 PR 的合并提交。",
    }
    for name in HEADINGS:
        contents, heading_lines = parse_sections(result)
        key = name.lower()
        if key not in heading_lines:
            result += f"\n\n## {name}\n\n{defaults[name]}"
        elif not contents[key]:
            lines = result.splitlines(keepends=True)
            line_number = heading_lines[key]
            if not lines[line_number].endswith(("\r", "\n")):
                lines[line_number] += "\n"
            lines[line_number] += f"\n{defaults[name]}\n"
            result = "".join(lines)
    result += "\n"
    validate_body(result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--body-file", type=Path, required=True)
    parser.add_argument("--workflow-name", required=True)
    parser.add_argument("--risk", choices=("低", "中", "高"), required=True)
    args = parser.parse_args()
    body = args.body_file.read_text(encoding="utf-8")
    args.body_file.write_text(complete_body(body, args.workflow_name, args.risk), encoding="utf-8")


if __name__ == "__main__":
    main()
