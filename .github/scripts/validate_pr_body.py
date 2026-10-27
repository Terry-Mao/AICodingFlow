#!/usr/bin/env python3
"""Check that a PR body explains testing, risk, and rollback."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


REQUIRED_SECTIONS = ("Summary", "Testing", "Risk", "How to revert")
HEADING = re.compile(r"^##[ \t]+(.+?)[ \t]*$", re.MULTILINE)
FENCE_OPEN = re.compile(r"^ {0,3}(`{3,}|~{3,})([^\r\n]*)$")


def strip_html_comments(line: str, in_comment: bool) -> tuple[str, bool]:
    visible = []
    offset = 0
    while offset < len(line):
        if in_comment:
            end = line.find("-->", offset)
            if end < 0:
                break
            offset = end + 3
            in_comment = False
        else:
            start = line.find("<!--", offset)
            if start < 0:
                visible.append(line[offset:])
                break
            visible.append(line[offset:start])
            offset = start + 4
            in_comment = True
    return "".join(visible), in_comment


def section_contents(body: str) -> dict[str, str]:
    """Read headings outside fences while retaining fenced section content."""
    sections: dict[str, list[str]] = {}
    current_section: str | None = None
    fence_char = ""
    fence_length = 0
    in_comment = False
    for line in body.splitlines():
        if fence_char:
            if re.fullmatch(r" {0,3}" + re.escape(fence_char) + "{" + str(fence_length) + r",}[ \t]*", line):
                fence_char = ""
            elif current_section is not None:
                sections[current_section].append(line)
            continue
        line, in_comment = strip_html_comments(line, in_comment)
        opening = FENCE_OPEN.fullmatch(line)
        if opening and (opening.group(1)[0] == "~" or "`" not in opening.group(2)):
            fence_char = opening.group(1)[0]
            fence_length = len(opening.group(1))
            continue
        heading = HEADING.fullmatch(line)
        if heading:
            current_section = heading.group(1).strip().lower()
            sections[current_section] = []
        elif current_section is not None:
            sections[current_section].append(line)
    return {name: "\n".join(lines).strip() for name, lines in sections.items()}


def validate_body(body: str) -> None:
    sections = section_contents(body)
    missing = [name for name in REQUIRED_SECTIONS if not sections.get(name.lower())]
    if missing:
        raise SystemExit("PR body needs non-empty sections: " + ", ".join(missing))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("body_file", type=Path)
    args = parser.parse_args()
    validate_body(args.body_file.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
