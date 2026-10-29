#!/usr/bin/env python3

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from script_imports import import_script


build_pr_diff = import_script(".github/scripts/build_pr_diff.py", "build_pr_diff")


class BuildPrDiffTest(unittest.TestCase):
    def test_local_diff_keeps_files_beyond_github_diff_limit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(["git", "init", "-q", str(root)], check=True)
            commit = ["git", "-C", str(root), "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit"]
            subprocess.run([*commit, "--allow-empty", "-qm", "base"], check=True)
            base = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
            for number in range(301):
                (root / f"file-{number:03d}.py").write_text("value = 1\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "."], check=True)
            subprocess.run([*commit, "-qm", "head"], check=True)
            head = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
            old = Path.cwd()
            try:
                os.chdir(root)
                snapshot = build_pr_diff.convert(build_pr_diff.run_git_diff(base, head, 3))
            finally:
                os.chdir(old)
            self.assertEqual(snapshot.count("\nFILE "), 301)
            self.assertIn("FILE file-300.py\n", snapshot)

    def test_fetch_github_pr_diff_uses_complete_local_merge_base_diff(self) -> None:
        captured = []

        class Response:
            def __init__(self, body: bytes) -> None:
                self.body = body

            def __enter__(self) -> "Response":
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def read(self) -> bytes:
                return self.body

        def fake_urlopen(request: object) -> Response:
            captured.append(
                {
                    "full_url": request.full_url,
                    "authorization": request.get_header("Authorization"),
                    "accept": request.get_header("Accept"),
                    "api_version": request.get_header("X-github-api-version"),
                }
            )
            return Response(b'{"head":{"sha":"head-sha"},"base":{"sha":"base-sha","ref":"main"}}')

        commands = []

        def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            commands.append(command)
            output = "base-sha\n" if command[1] == "rev-parse" else "merge-base-sha\n"
            return subprocess.CompletedProcess(command, 0, output)

        with (
            patch.object(build_pr_diff.urllib.request, "urlopen", fake_urlopen),
            patch.object(build_pr_diff.subprocess, "run", fake_run),
            patch.object(
                build_pr_diff, "run_git_diff",
                return_value=[f"diff --git a/{n}.py b/{n}.py" for n in range(301)],
            ) as local_diff,
        ):
            self.assertEqual(
                len(build_pr_diff.fetch_github_pr_diff("owner/repo", "42", "token", "head-sha", "base-sha")),
                301,
            )

        self.assertEqual(
            [call["full_url"] for call in captured],
            ["https://api.github.com/repos/owner/repo/pulls/42"] * 2,
        )
        self.assertEqual([call["authorization"] for call in captured], ["Bearer token"] * 2)
        self.assertEqual([call["accept"] for call in captured], ["application/vnd.github+json"] * 2)
        self.assertEqual([call["api_version"] for call in captured], ["2022-11-28"] * 2)
        self.assertEqual(commands, [
            ["git", "fetch", "--no-tags", "https://github.com/owner/repo.git", "refs/heads/main"],
            ["git", "rev-parse", "FETCH_HEAD"],
            ["git", "merge-base", "base-sha", "head-sha"],
        ])
        local_diff.assert_called_once_with("merge-base-sha", "head-sha", 3)

    def test_fetch_github_pr_diff_fails_when_head_changes_after_diff_fetch(self) -> None:
        metadata = [
            {"head": {"sha": "head-sha"}, "base": {"sha": "base-sha", "ref": "main"}},
            {"head": {"sha": "new-head"}, "base": {"sha": "base-sha", "ref": "main"}},
        ]

        def fake_metadata(repo: str, pr_number: str, token: str) -> dict[str, object]:
            self.assertEqual((repo, pr_number, token), ("owner/repo", "42", "token"))
            return metadata.pop(0)

        with (
            patch.object(build_pr_diff, "fetch_github_pr_metadata", fake_metadata),
            patch.object(build_pr_diff.subprocess, "run", side_effect=[
                subprocess.CompletedProcess([], 0),
                subprocess.CompletedProcess([], 0, "base-sha\n"),
                subprocess.CompletedProcess([], 0, "merge-base-sha\n"),
            ]),
            patch.object(build_pr_diff, "run_git_diff", return_value=[]),
        ):
            with self.assertRaisesRegex(SystemExit, "head changed"):
                build_pr_diff.fetch_github_pr_diff("owner/repo", "42", "token", "head-sha", "base-sha")

    def test_fetch_github_pr_diff_rejects_changed_fetched_base(self) -> None:
        metadata = {"head": {"sha": "head-sha"}, "base": {"sha": "base-sha", "ref": "main"}}
        with (
            patch.object(build_pr_diff, "fetch_github_pr_metadata", return_value=metadata),
            patch.object(build_pr_diff.subprocess, "run", side_effect=[
                subprocess.CompletedProcess([], 0),
                subprocess.CompletedProcess([], 0, "new-base-sha\n"),
            ]),
        ):
            with self.assertRaisesRegex(SystemExit, "base changed while fetching"):
                build_pr_diff.fetch_github_pr_diff("owner/repo", "42", "token", "head-sha", "base-sha")

    def test_fetch_github_pr_diff_fails_when_head_changed(self) -> None:
        def fake_metadata(repo: str, pr_number: str, token: str) -> dict[str, object]:
            self.assertEqual((repo, pr_number, token), ("owner/repo", "42", "token"))
            return {"head": {"sha": "new-head"}, "base": {"sha": "base-sha"}}

        with patch.object(build_pr_diff, "fetch_github_pr_metadata", fake_metadata):
            with self.assertRaisesRegex(SystemExit, "head changed"):
                build_pr_diff.fetch_github_pr_diff("owner/repo", "42", "token", "old-head", "base-sha")

    def test_fetch_github_pr_diff_fails_when_base_changed(self) -> None:
        def fake_metadata(repo: str, pr_number: str, token: str) -> dict[str, object]:
            self.assertEqual((repo, pr_number, token), ("owner/repo", "42", "token"))
            return {"head": {"sha": "head-sha"}, "base": {"sha": "new-base"}}

        with patch.object(build_pr_diff, "fetch_github_pr_metadata", fake_metadata):
            with self.assertRaisesRegex(SystemExit, "base changed"):
                build_pr_diff.fetch_github_pr_diff("owner/repo", "42", "token", "head-sha", "old-base")

    def test_metadata_only_rename_still_emits_file_section(self) -> None:
        diff = [
            "diff --git a/core/deleted.py b/core/renamed.py",
            "similarity index 100%",
            "rename from core/deleted.py",
            "rename to core/renamed.py",
        ]

        self.assertEqual(
            build_pr_diff.convert(diff),
            "\n".join(
                [
                    "# PR_DIFF_V1",
                    "FILE core/renamed.py",
                    "END_FILE",
                    "",
                ]
            ),
        )

    def test_hunk_lines_that_look_like_file_headers_are_not_file_headers(self) -> None:
        diff = [
            "diff --git a/docs/example.txt b/docs/example.txt",
            "index 1111111..2222222 100644",
            "--- a/docs/example.txt",
            "+++ b/docs/example.txt",
            "@@ -1,2 +1,3 @@",
            " unchanged",
            "--- old literal",
            "+++ literal content",
            "+next line",
        ]

        self.assertEqual(
            build_pr_diff.convert(diff),
            "\n".join(
                [
                    "# PR_DIFF_V1",
                    "FILE docs/example.txt",
                    "HUNK @@ -1,2 +1,3 @@",
                    "BOTH     1 | unchanged",
                    "LEFT     2 | -- old literal",
                    "RIGHT    2 | ++ literal content",
                    "RIGHT    3 | next line",
                    "END_FILE",
                    "",
                ]
            ),
        )


if __name__ == "__main__":
    unittest.main()
