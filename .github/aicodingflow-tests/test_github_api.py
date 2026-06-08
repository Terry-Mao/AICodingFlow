from __future__ import annotations

import json
import subprocess
import unittest
from unittest import mock

from script_imports import import_script


github_api = import_script(".github/scripts/github_api.py", "github_api")


class GithubApiTests(unittest.TestCase):
    def test_run_gh_json_invokes_gh_and_parses_stdout(self) -> None:
        completed = subprocess.CompletedProcess(args=[], returncode=0, stdout=json.dumps({"ok": True}))
        with mock.patch.object(github_api.subprocess, "run", return_value=completed) as run:
            self.assertEqual(github_api.run_gh_json(["repo", "view"]), {"ok": True})

        run.assert_called_once_with(["gh", "repo", "view"], check=True, stdout=subprocess.PIPE, text=True)

    def test_run_gh_text_returns_stdout(self) -> None:
        completed = subprocess.CompletedProcess(args=[], returncode=0, stdout="body\n")
        with mock.patch.object(github_api.subprocess, "run", return_value=completed):
            self.assertEqual(github_api.run_gh_text(["pr", "diff"]), "body\n")

    def test_fetch_default_branch_requires_branch_name(self) -> None:
        with mock.patch.object(github_api, "run_gh_json", return_value={"defaultBranchRef": {"name": "main"}}):
            self.assertEqual(github_api.fetch_default_branch("owner/repo"), "main")

        with mock.patch.object(github_api, "run_gh_json", return_value={"defaultBranchRef": {}}):
            with self.assertRaisesRegex(SystemExit, "could not determine default branch"):
                github_api.fetch_default_branch("owner/repo")

    def test_flatten_gh_pages_delegates_paginated_shape(self) -> None:
        self.assertEqual(github_api.flatten_gh_pages([[{"number": 1}], [{"number": 2}]]), [{"number": 1}, {"number": 2}])


if __name__ == "__main__":
    unittest.main()
