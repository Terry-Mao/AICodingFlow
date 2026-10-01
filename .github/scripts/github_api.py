"""Small GitHub CLI helpers shared by workflow scripts."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from typing import Any

from context_snapshot import flatten_pages


def run_gh_json(args: list[str]) -> Any:
    result = subprocess.run(["gh", *args], check=True, stdout=subprocess.PIPE, text=True)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        # `gh api --paginate` emits one JSON value per line without --slurp.
        # Keep callers compatible with both that stream and the aggregated form.
        decoder = json.JSONDecoder()
        values: list[Any] = []
        offset = 0
        while offset < len(result.stdout):
            while offset < len(result.stdout) and result.stdout[offset].isspace():
                offset += 1
            if offset >= len(result.stdout):
                break
            value, end = decoder.raw_decode(result.stdout, offset)
            values.append(value)
            offset = end
        if not values:
            raise
        return values


def run_gh_text(args: list[str]) -> str:
    result = subprocess.run(["gh", *args], check=True, stdout=subprocess.PIPE, text=True)
    return result.stdout


def fetch_default_branch(repo: str, *, run_json: Callable[[list[str]], Any] | None = None) -> str:
    data = (run_json or run_gh_json)(["repo", "view", repo, "--json", "defaultBranchRef"])
    branch = (data.get("defaultBranchRef") or {}).get("name")
    if not branch:
        raise SystemExit("could not determine default branch")
    return branch


def flatten_gh_pages(value: Any) -> list[dict[str, Any]]:
    return flatten_pages(value)
