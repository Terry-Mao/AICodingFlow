from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from script_imports import import_script


read_branch_sha = import_script(".github/scripts/read_branch_sha.py", "read_branch_sha")


class ReadBranchShaTest(unittest.TestCase):
    def test_read_branch_sha_returns_empty_for_missing_branch(self) -> None:
        with mock.patch.object(read_branch_sha, "run_gh_json", return_value=None):
            self.assertEqual(read_branch_sha.read_branch_sha("owner/repo", "missing"), "")

    def test_read_branch_sha_returns_object_sha(self) -> None:
        with mock.patch.object(read_branch_sha, "run_gh_json", return_value={"object": {"sha": "abc123"}}):
            self.assertEqual(read_branch_sha.read_branch_sha("owner/repo", "main"), "abc123")

    def test_matching_branch_shas_filters_target_and_slugged_branches(self) -> None:
        with mock.patch.object(
            read_branch_sha,
            "run_gh_json",
            return_value=[
                {"ref": "refs/heads/spec/implement-issue-18", "object": {"sha": "base"}},
                {"ref": "refs/heads/spec/implement-issue-18-workflow", "object": {"sha": "slug"}},
                {"ref": "refs/heads/spec/implement-issue-180", "object": {"sha": "other"}},
            ],
        ):
            self.assertEqual(
                read_branch_sha.matching_branch_shas("owner/repo", "spec/implement-issue-18"),
                {
                    "spec/implement-issue-18": "base",
                    "spec/implement-issue-18-workflow": "slug",
                },
            )

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

    def test_snapshot_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            snapshot = Path(directory) / "branch-start-shas.json"
            read_branch_sha.write_snapshot(snapshot, {"spec/implement-issue-18-workflow": "old"})

            self.assertEqual(
                read_branch_sha.read_snapshot(snapshot),
                {"spec/implement-issue-18-workflow": "old"},
            )

    def test_end_state_detects_changed_slug_branch_without_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            snapshot = Path(directory) / "branch-start-shas.json"
            read_branch_sha.write_snapshot(
                snapshot,
                {
                    "spec/implement-issue-18": "base",
                    "spec/implement-issue-18-workflow": "old",
                },
            )
            with mock.patch.object(
                read_branch_sha,
                "matching_branch_shas",
                return_value={
                    "spec/implement-issue-18": "base",
                    "spec/implement-issue-18-workflow": "new",
                },
            ):
                state = read_branch_sha.end_state(
                    "owner/repo",
                    "spec/implement-issue-18",
                    None,
                    snapshot,
                )

        self.assertEqual(state["branch"], "spec/implement-issue-18")
        self.assertEqual(state["sha"], "base")
        self.assertEqual(state["changed"], "true")
        self.assertEqual(state["changed_branches"], "spec/implement-issue-18-workflow")

    def test_end_state_uses_metadata_branch_when_present(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            snapshot = Path(directory) / "branch-start-shas.json"
            metadata = Path(directory) / "pr-metadata.json"
            read_branch_sha.write_snapshot(snapshot, {"spec/implement-issue-18-workflow": "old"})
            metadata.write_text(json.dumps({"branch_name": "spec/implement-issue-18-workflow"}), encoding="utf-8")
            with mock.patch.object(
                read_branch_sha,
                "matching_branch_shas",
                return_value={"spec/implement-issue-18-workflow": "new"},
            ):
                state = read_branch_sha.end_state(
                    "owner/repo",
                    "spec/implement-issue-18",
                    metadata,
                    snapshot,
                )

        self.assertEqual(state["branch"], "spec/implement-issue-18-workflow")
        self.assertEqual(state["sha"], "new")
        self.assertEqual(state["start_sha"], "old")
        self.assertEqual(state["changed"], "true")


if __name__ == "__main__":
    unittest.main()
