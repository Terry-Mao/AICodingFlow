"""Validate the selected workflow model provider before invoking an agent."""

from __future__ import annotations

import os
import re
import sys


MODEL_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]*\Z")


def validate(provider: str, codex_key: str, claude_key: str, claude_model: str) -> str:
    selected = provider or "codex"
    if selected == "codex":
        if not codex_key:
            raise ValueError("CODEX_API_KEY is not set")
    elif selected == "claude":
        if not claude_key:
            raise ValueError("ANTHROPIC_API_KEY is not set")
        if not MODEL_RE.fullmatch(claude_model):
            raise ValueError("CLAUDE_MODEL must be a nonempty model identifier")
    else:
        raise ValueError("AI_PROVIDER must be codex or claude")
    return selected


def main() -> int:
    try:
        selected = validate(
            os.environ.get("AI_PROVIDER", ""),
            os.environ.get("CODEX_API_KEY", ""),
            os.environ.get("ANTHROPIC_API_KEY", ""),
            os.environ.get("CLAUDE_MODEL", ""),
        )
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    print(f"Selected AI provider: {selected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
