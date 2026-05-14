from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.script_imports import import_script


read_branch_sha = import_script(".github/scripts/read_branch_sha.py", "read_branch_sha")


class ReadBranchShaTest(unittest.TestCase):
    def test_read_branch_sha_returns_empty_for_missing_branch(self) -> None:
        with mock.patch.object(read_branch_sha, "run_gh_json", return_value=None):
            self.assertEqual(read_branch_sha.read_branch_sha("owner/repo", "missing"), "")

    def test_read_branch_sha_returns_object_sha(self) -> None:
        with mock.patch.object(read_branch_sha, "run_gh_json", return_value={"object": {"sha": "abc123"}}):
            self.assertEqual(read_branch_sha.read_branch_sha("owner/repo", "main"), "abc123")

    def test_metadata_branch_ignores_missing_or_invalid_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing.json"
            invalid = Path(directory) / "invalid.json"
            invalid.write_text("{", encoding="utf-8")

            self.assertEqual(read_branch_sha.metadata_branch(missing), "")
            self.assertEqual(read_branch_sha.metadata_branch(invalid), "")

    def test_metadata_branch_reads_branch_name(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            metadata = Path(directory) / "pr-metadata.json"
            metadata.write_text(json.dumps({"branch_name": "spec/implement-issue-18"}), encoding="utf-8")

            self.assertEqual(read_branch_sha.metadata_branch(metadata), "spec/implement-issue-18")


if __name__ == "__main__":
    unittest.main()
