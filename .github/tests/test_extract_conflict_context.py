#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

from script_imports import import_script


extract_conflict_context = import_script(
    ".agents/skills/resolve-merge-conflicts/scripts/extract_conflict_context.py",
    "extract_conflict_context",
)


class ExtractConflictContextTest(unittest.TestCase):
    def run_git(self, repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            check=False,
        )
        if check and result.returncode != 0:
            self.fail(f"git {' '.join(args)} failed: {result.stderr or result.stdout}")
        return result

    def init_repo(self, repo: Path) -> None:
        self.run_git(repo, "init", "-b", "main")
        self.run_git(repo, "config", "user.email", "test@example.com")
        self.run_git(repo, "config", "user.name", "Test User")

    def run_script(self, repo: Path, *args: str) -> tuple[int | None, str, str]:
        stdout = StringIO()
        stderr = StringIO()
        argv = ["extract_conflict_context.py", "--repo", str(repo), *args]
        with mock.patch("sys.argv", argv), redirect_stdout(stdout), redirect_stderr(stderr):
            result = extract_conflict_context.main()
        return result, stdout.getvalue(), stderr.getvalue()

    def create_text_conflict(self, repo: Path) -> None:
        self.init_repo(repo)
        note_path = repo / "notes.txt"
        note_path.write_text("intro\nbase line\noutro\n", encoding="utf-8")
        self.run_git(repo, "add", "notes.txt")
        self.run_git(repo, "commit", "-m", "base")
        self.run_git(repo, "checkout", "-b", "theirs")
        note_path.write_text("intro\ntheirs line\noutro\n", encoding="utf-8")
        self.run_git(repo, "commit", "-am", "theirs")
        self.run_git(repo, "checkout", "main")
        note_path.write_text("intro\nours line\noutro\n", encoding="utf-8")
        self.run_git(repo, "commit", "-am", "ours")
        merge = self.run_git(repo, "merge", "theirs", check=False)
        self.assertNotEqual(merge.returncode, 0)

    def create_add_add_conflict(self, repo: Path) -> None:
        self.init_repo(repo)
        (repo / "README.md").write_text("base\n", encoding="utf-8")
        self.run_git(repo, "add", "README.md")
        self.run_git(repo, "commit", "-m", "base")
        self.run_git(repo, "checkout", "-b", "theirs")
        (repo / "settings.ini").write_text("mode=theirs\n", encoding="utf-8")
        self.run_git(repo, "add", "settings.ini")
        self.run_git(repo, "commit", "-m", "theirs settings")
        self.run_git(repo, "checkout", "main")
        (repo / "settings.ini").write_text("mode=ours\n", encoding="utf-8")
        self.run_git(repo, "add", "settings.ini")
        self.run_git(repo, "commit", "-m", "ours settings")
        merge = self.run_git(repo, "merge", "theirs", check=False)
        self.assertNotEqual(merge.returncode, 0)

    def test_summary_reports_conflicted_file_type_stages_and_hunk_count(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            self.create_text_conflict(repo)

            result, stdout, stderr = self.run_script(repo)

        self.assertEqual(result, 0)
        self.assertEqual(stderr, "")
        self.assertIn("conflicted files: 1", stdout)
        self.assertIn("- notes.txt | type=text | stages=1,2,3 | hunks=1", stdout)
        self.assertIn("use --file <path> for compact hunk details", stdout)

    def test_file_detail_prints_only_conflict_context_and_compact_diff(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            self.create_text_conflict(repo)

            result, stdout, stderr = self.run_script(repo, "--file", "notes.txt", "--context", "1")

        self.assertEqual(result, 0)
        self.assertEqual(stderr, "")
        self.assertIn("== notes.txt ==", stdout)
        self.assertIn("type: text", stdout)
        self.assertIn("before:\n  intro", stdout)
        self.assertIn("ours (HEAD):\n  ours line", stdout)
        self.assertIn("theirs (theirs):\n  theirs line", stdout)
        self.assertIn("ours vs theirs diff:", stdout)
        self.assertIn("-ours line", stdout)
        self.assertIn("+theirs line", stdout)
        self.assertIn("after:\n  outro", stdout)

    def test_json_detail_includes_hunks_and_diff_for_requested_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            self.create_text_conflict(repo)

            result, stdout, stderr = self.run_script(repo, "--file", "notes.txt", "--json")

        self.assertEqual(result, 0)
        self.assertEqual(stderr, "")
        payload = json.loads(stdout)
        self.assertEqual(len(payload["conflicted_files"]), 1)
        file_entry = payload["conflicted_files"][0]
        self.assertEqual(file_entry["path"], "notes.txt")
        self.assertEqual(file_entry["conflict_type"], "text")
        self.assertEqual(file_entry["marker_hunks"], 1)
        self.assertEqual(file_entry["hunks"][0]["ours"], ["ours line"])
        self.assertEqual(file_entry["hunks"][0]["theirs"], ["theirs line"])
        self.assertIn("-ours line", file_entry["hunks"][0]["ours_vs_theirs_diff"])
        self.assertIn("+theirs line", file_entry["hunks"][0]["ours_vs_theirs_diff"])

    def test_add_add_conflict_uses_index_preview_when_markers_are_absent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            self.create_add_add_conflict(repo)
            (repo / "settings.ini").write_text("", encoding="utf-8")

            result, stdout, stderr = self.run_script(repo, "--file", "settings.ini")

        self.assertEqual(result, 0)
        self.assertEqual(stderr, "")
        self.assertIn("type: add/add", stdout)
        self.assertIn("hunks: 0", stdout)
        self.assertIn("index preview:", stdout)
        self.assertIn("ours:\n  mode=ours", stdout)
        self.assertIn("theirs:\n  mode=theirs", stdout)
        self.assertIn("-mode=ours", stdout)
        self.assertIn("+mode=theirs", stdout)

    def test_empty_stage_renders_as_empty_and_still_has_diff(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            self.init_repo(repo)
            (repo / "empty.txt").write_text("base line\n", encoding="utf-8")
            self.run_git(repo, "add", "empty.txt")
            self.run_git(repo, "commit", "-m", "base")
            self.run_git(repo, "checkout", "-b", "theirs")
            (repo / "empty.txt").write_text("theirs line\n", encoding="utf-8")
            self.run_git(repo, "commit", "-am", "theirs nonempty")
            self.run_git(repo, "checkout", "main")
            (repo / "empty.txt").write_text("", encoding="utf-8")
            self.run_git(repo, "commit", "-am", "ours empty")
            merge = self.run_git(repo, "merge", "theirs", check=False)
            self.assertNotEqual(merge.returncode, 0)
            (repo / "empty.txt").write_text("", encoding="utf-8")

            result, stdout, stderr = self.run_script(repo, "--file", "empty.txt")

        self.assertEqual(result, 0)
        self.assertEqual(stderr, "")
        self.assertIn("ours:\n  (empty)", stdout)
        self.assertIn("theirs:\n  theirs line", stdout)
        self.assertIn("ours vs theirs diff:", stdout)
        self.assertIn("+theirs line", stdout)

    def test_binary_index_preview_does_not_crash_on_invalid_utf8(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            self.init_repo(repo)
            (repo / "README.md").write_text("base\n", encoding="utf-8")
            self.run_git(repo, "add", "README.md")
            self.run_git(repo, "commit", "-m", "base")
            self.run_git(repo, "checkout", "-b", "theirs")
            (repo / "asset.bin").write_bytes(b"\xff\xfe\xfdtheirs")
            self.run_git(repo, "add", "asset.bin")
            self.run_git(repo, "commit", "-m", "theirs binary")
            self.run_git(repo, "checkout", "main")
            (repo / "asset.bin").write_bytes(b"\xff\xfe\xfdours")
            self.run_git(repo, "add", "asset.bin")
            self.run_git(repo, "commit", "-m", "ours binary")
            merge = self.run_git(repo, "merge", "theirs", check=False)
            self.assertNotEqual(merge.returncode, 0)
            (repo / "asset.bin").write_bytes(b"")

            result, stdout, stderr = self.run_script(repo, "--file", "asset.bin")

        self.assertEqual(result, 0)
        self.assertEqual(stderr, "")
        self.assertIn("type: add/add", stdout)
        self.assertIn("ours:\n  (not present)", stdout)
        self.assertIn("theirs:\n  (not present)", stdout)

    def test_missing_requested_file_exits_with_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            self.create_text_conflict(repo)

            result, stdout, stderr = self.run_script(repo, "--file", "missing.txt")

        self.assertEqual(result, 2)
        self.assertEqual(stdout, "")
        self.assertIn("error: conflicted file not found: missing.txt", stderr)


if __name__ == "__main__":
    unittest.main()
