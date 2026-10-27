#!/usr/bin/env python3
"""Check that a PR body explains testing, risk, and rollback."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


REQUIRED_SECTIONS = ("Summary", "Testing", "Risk", "How to revert")
HEADING = re.compile(r"^##[ \t]+(.+?)[ \t]*$", re.MULTILINE)
COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
FENCE_OPEN = re.compile(r"^ {0,3}(`{3,}|~{3,})([^\r\n]*)$")


def visible_markdown(body: str) -> str:
    """Remove comments and fenced examples before looking for PR sections."""
    lines = []
    fence_char = ""
    fence_length = 0
    for line in COMMENT.sub("", body).splitlines():
        if fence_char:
            if re.fullmatch(r" {0,3}" + re.escape(fence_char) + "{" + str(fence_length) + r",}[ \t]*", line):
                fence_char = ""
            lines.append("")
            continue
        opening = FENCE_OPEN.fullmatch(line)
        if opening and (opening.group(1)[0] == "~" or "`" not in opening.group(2)):
            fence_char = opening.group(1)[0]
            fence_length = len(opening.group(1))
            lines.append("")
            continue
        lines.append(line)
    return "\n".join(lines)


def section_contents(body: str) -> dict[str, str]:
    clean = visible_markdown(body)
    matches = list(HEADING.finditer(clean))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(clean)
        sections[match.group(1).strip().lower()] = clean[match.end():end].strip()
    return sections


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
