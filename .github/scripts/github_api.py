"""Small GitHub CLI helpers shared by workflow scripts."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable
from typing import Any

from context_snapshot import flatten_pages


def run_gh_json(args: list[str]) -> Any:
    result = subprocess.run(["gh", *args], check=True, stdout=subprocess.PIPE, text=True)
    return json.loads(result.stdout)


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
