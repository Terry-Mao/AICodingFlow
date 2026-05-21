from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest import mock

from script_imports import ROOT, import_script


prepare_local = import_script(".github/scripts/prepare_local_review_inputs.py", "prepare_local_review_inputs")


CODE_DIFF = [
    "diff --git a/core/foo.py b/core/foo.py",
    "index 1111111..2222222 100644",
    "--- a/core/foo.py",
    "+++ b/core/foo.py",
    "@@ -1 +1 @@",
    "-old",
    "+new",
]

SPEC_DIFF = [
    "diff --git a/specs/issue-80/product.md b/specs/issue-80/product.md",
    "index 1111111..2222222 100644",
    "--- a/specs/issue-80/product.md",
    "+++ b/specs/issue-80/product.md",
    "@@ -1 +1 @@",
    "-old",
    "+new",
]


class PrepareLocalReviewInputsTest(unittest.TestCase):
    def run_in_tempdir(self, callback) -> None:
        old_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as directory:
            os.chdir(directory)
            try:
                callback(Path(directory))
            finally:
                os.chdir(old_cwd)

    def common_patches(self, diff_lines: list[str]):
        return (
            mock.patch.object(prepare_local, "default_repo", return_value="owner/repo"),
            mock.patch.object(prepare_local, "default_base", return_value="upstream/main"),
            mock.patch.object(prepare_local, "resolve_ref", side_effect=["head-sha", "base-sha"]),
            mock.patch.object(
                prepare_local,
                "local_pr_event",
                return_value={
                    "pull_request": {
                        "number": "",
                        "title": "feat: local review",
                        "body": "",
                        "html_url": "",
                        "user": {"login": "dev"},
                        "base": {"ref": "main", "sha": "base-sha", "repo": {"default_branch": "main"}},
                        "head": {"ref": "feat/local-review-skills-80", "sha": "head-sha"},
                    }
                },
            ),
            mock.patch.object(prepare_local, "github_pr_event_for_current_branch", return_value=None),
            mock.patch.object(prepare_local, "local_worktree_diff", return_value=diff_lines),
            mock.patch.object(prepare_local, "write_baseline_status", return_value=".local_review_baseline.status"),
        )

    def git(self, directory: Path, *args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=directory,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        )
        return result.stdout.strip()

    def init_repo(self, directory: Path) -> str:
        self.git(directory, "init", "-b", "main")
        self.git(directory, "config", "user.name", "Test User")
        self.git(directory, "config", "user.email", "test@example.com")
        (directory / "core").mkdir()
        (directory / "core/foo.py").write_text("old\n", encoding="utf-8")
        (directory / "core/deleted.py").write_text("delete me\n", encoding="utf-8")
        self.git(directory, "add", "core/foo.py", "core/deleted.py")
        self.git(directory, "commit", "-m", "base")
        return self.git(directory, "rev-parse", "HEAD")

    def test_prepares_code_review_inputs_and_removes_stale_files(self) -> None:
        def scenario(directory: Path) -> None:
            for name in ("pr_description.txt", "pr_diff.txt", "spec_context.md", "review.json"):
                Path(name).write_text("stale", encoding="utf-8")

            with ExitStack() as stack:
                for patcher in self.common_patches(CODE_DIFF):
                    stack.enter_context(patcher)
                resolve_spec_context = stack.enter_context(
                    mock.patch.object(
                        prepare_local.write_spec_context,
                        "resolve_spec_context",
                        return_value={"spec_context_source": "", "spec_entries": []},
                    )
                )
                stack.enter_context(mock.patch("sys.argv", ["prepare_local_review_inputs.py", "--github-output", ""]))
                self.assertEqual(prepare_local.main(), 0)

            self.assertIn("Title: feat: local review", Path("pr_description.txt").read_text(encoding="utf-8"))
            self.assertIn("FILE core/foo.py", Path("pr_diff.txt").read_text(encoding="utf-8"))
            self.assertFalse(Path("spec_context.md").exists())
            self.assertFalse(Path("review.json").exists())
            resolve_spec_context.assert_called_once()

        self.run_in_tempdir(scenario)

    def test_prepares_spec_review_inputs_without_spec_context(self) -> None:
        def scenario(directory: Path) -> None:
            Path("spec_context.md").write_text("stale", encoding="utf-8")

            with ExitStack() as stack:
                for patcher in self.common_patches(SPEC_DIFF):
                    stack.enter_context(patcher)
                resolve_spec_context = stack.enter_context(
                    mock.patch.object(prepare_local.write_spec_context, "resolve_spec_context")
                )
                stack.enter_context(
                    mock.patch(
                        "sys.argv",
                        [
                            "prepare_local_review_inputs.py",
                            "--github-output",
                            "",
                        ],
                    )
                )
                self.assertEqual(prepare_local.main(), 0)

            self.assertIn("FILE specs/issue-80/product.md", Path("pr_diff.txt").read_text(encoding="utf-8"))
            self.assertFalse(Path("spec_context.md").exists())
            resolve_spec_context.assert_not_called()

        self.run_in_tempdir(scenario)

    def test_prefers_github_pr_base_sha_for_diff_and_description(self) -> None:
        def scenario(directory: Path) -> None:
            github_event = {
                "pull_request": {
                    "number": 12,
                    "title": "fix: github pr",
                    "body": "remote body",
                    "html_url": "https://github.com/owner/repo/pull/12",
                    "user": {"login": "reviewer"},
                    "base": {"ref": "main", "sha": "github-base", "repo": {"default_branch": "main"}},
                    "head": {"ref": "fix/github-pr", "sha": "github-head"},
                }
            }

            with ExitStack() as stack:
                stack.enter_context(mock.patch.object(prepare_local, "default_repo", return_value="owner/repo"))
                default_base = stack.enter_context(mock.patch.object(prepare_local, "default_base", return_value="upstream/main"))
                resolve_ref = stack.enter_context(mock.patch.object(prepare_local, "resolve_ref", return_value="head-sha"))
                local_pr_event = stack.enter_context(mock.patch.object(prepare_local, "local_pr_event"))
                local_worktree_diff = stack.enter_context(mock.patch.object(prepare_local, "local_worktree_diff", return_value=CODE_DIFF))
                stack.enter_context(
                    mock.patch.object(
                        prepare_local,
                        "github_pr_event_for_current_branch",
                        return_value=github_event,
                    )
                )
                stack.enter_context(
                    mock.patch.object(
                        prepare_local.write_spec_context,
                        "resolve_spec_context",
                        return_value={"spec_context_source": "", "spec_entries": []},
                    )
                )
                stack.enter_context(
                    mock.patch.object(prepare_local, "write_baseline_status", return_value=".local_review_baseline.status")
                )
                stack.enter_context(mock.patch("sys.argv", ["prepare_local_review_inputs.py", "--github-output", ""]))
                self.assertEqual(prepare_local.main(), 0)

            description = Path("pr_description.txt").read_text(encoding="utf-8")
            self.assertIn("Title: fix: github pr", description)
            self.assertIn("Body:\nremote body", description)
            self.assertIn("Base: main @ github-base", description)
            self.assertIn("FILE core/foo.py", Path("pr_diff.txt").read_text(encoding="utf-8"))
            default_base.assert_not_called()
            resolve_ref.assert_called_once_with("HEAD")
            local_pr_event.assert_not_called()
            local_worktree_diff.assert_called_once_with("github-base", 3)

        self.run_in_tempdir(scenario)

    def test_explicit_base_overrides_github_pr_base_and_updates_description(self) -> None:
        def scenario(directory: Path) -> None:
            github_event = {
                "pull_request": {
                    "number": 12,
                    "title": "fix: github pr",
                    "body": "remote body",
                    "html_url": "https://github.com/owner/repo/pull/12",
                    "user": {"login": "reviewer"},
                    "base": {"ref": "main", "sha": "github-base", "repo": {"default_branch": "main"}},
                    "head": {"ref": "fix/github-pr", "sha": "github-head"},
                }
            }

            with ExitStack() as stack:
                stack.enter_context(mock.patch.object(prepare_local, "default_repo", return_value="owner/repo"))
                default_base = stack.enter_context(mock.patch.object(prepare_local, "default_base"))
                resolve_ref = stack.enter_context(mock.patch.object(prepare_local, "resolve_ref", side_effect=["head-sha", "explicit-base-sha"]))
                local_worktree_diff = stack.enter_context(mock.patch.object(prepare_local, "local_worktree_diff", return_value=CODE_DIFF))
                stack.enter_context(
                    mock.patch.object(
                        prepare_local,
                        "github_pr_event_for_current_branch",
                        return_value=github_event,
                    )
                )
                stack.enter_context(
                    mock.patch.object(
                        prepare_local.write_spec_context,
                        "resolve_spec_context",
                        return_value={"spec_context_source": "", "spec_entries": []},
                    )
                )
                stack.enter_context(
                    mock.patch.object(prepare_local, "write_baseline_status", return_value=".local_review_baseline.status")
                )
                stack.enter_context(
                    mock.patch(
                        "sys.argv",
                        ["prepare_local_review_inputs.py", "--github-output", "", "--base", "origin/main"],
                    )
                )
                self.assertEqual(prepare_local.main(), 0)

            description = Path("pr_description.txt").read_text(encoding="utf-8")
            self.assertIn("Title: fix: github pr", description)
            self.assertIn("Base: main @ explicit-base-sha", description)
            default_base.assert_not_called()
            self.assertEqual(resolve_ref.call_args_list, [mock.call("HEAD"), mock.call("origin/main")])
            local_worktree_diff.assert_called_once_with("explicit-base-sha", 3)

        self.run_in_tempdir(scenario)

    def test_github_pr_event_without_base_sha_uses_fallback_base(self) -> None:
        def scenario(directory: Path) -> None:
            github_event = {
                "pull_request": {
                    "number": 12,
                    "title": "fix: github pr",
                    "body": "remote body",
                    "html_url": "https://github.com/owner/repo/pull/12",
                    "user": {"login": "reviewer"},
                    "base": {"ref": "main", "sha": "", "repo": {"default_branch": "main"}},
                    "head": {"ref": "fix/github-pr", "sha": "github-head"},
                }
            }

            with ExitStack() as stack:
                stack.enter_context(mock.patch.object(prepare_local, "default_repo", return_value="owner/repo"))
                default_base = stack.enter_context(mock.patch.object(prepare_local, "default_base", return_value="origin/main"))
                resolve_ref = stack.enter_context(mock.patch.object(prepare_local, "resolve_ref", side_effect=["head-sha", "fallback-base-sha"]))
                local_worktree_diff = stack.enter_context(mock.patch.object(prepare_local, "local_worktree_diff", return_value=CODE_DIFF))
                stack.enter_context(
                    mock.patch.object(
                        prepare_local,
                        "github_pr_event_for_current_branch",
                        return_value=github_event,
                    )
                )
                stack.enter_context(
                    mock.patch.object(
                        prepare_local.write_spec_context,
                        "resolve_spec_context",
                        return_value={"spec_context_source": "", "spec_entries": []},
                    )
                )
                stack.enter_context(
                    mock.patch.object(prepare_local, "write_baseline_status", return_value=".local_review_baseline.status")
                )
                stack.enter_context(mock.patch("sys.argv", ["prepare_local_review_inputs.py", "--github-output", ""]))
                self.assertEqual(prepare_local.main(), 0)

            description = Path("pr_description.txt").read_text(encoding="utf-8")
            self.assertIn("Base: main @ fallback-base-sha", description)
            default_base.assert_called_once()
            self.assertEqual(resolve_ref.call_args_list, [mock.call("HEAD"), mock.call("origin/main")])
            local_worktree_diff.assert_called_once_with("fallback-base-sha", 3)

        self.run_in_tempdir(scenario)

    def test_default_base_prefers_origin_before_upstream(self) -> None:
        def exists(ref: str) -> bool:
            with mock.patch.object(
                prepare_local,
                "optional_git",
                side_effect=lambda args: "sha" if args[-1] == ref else "",
            ):
                return prepare_local.default_base() == ref

        with mock.patch.object(
            prepare_local,
            "optional_git",
            side_effect=lambda args: "sha" if args[-1] in {"origin/main", "upstream/main", "main"} else "",
        ):
            self.assertEqual(prepare_local.default_base(), "origin/main")

        self.assertTrue(exists("upstream/main"))
        self.assertTrue(exists("main"))

        with mock.patch.object(prepare_local, "optional_git", return_value=""):
            with self.assertRaisesRegex(SystemExit, "could not resolve default review base"):
                prepare_local.default_base()

    def test_github_pr_event_for_current_branch_fetches_description(self) -> None:
        def fake_run(args: list[str], env: dict[str, str] | None = None) -> str:
            if args[:5] == ["gh", "pr", "view", "fix/github-pr", "--repo"]:
                return """
                {
                  "number": 12,
                  "state": "OPEN",
                  "isDraft": false,
                  "title": "fix: github pr",
                  "body": "remote body",
                  "url": "https://github.com/owner/repo/pull/12",
                  "author": {"login": "reviewer"},
                  "baseRefName": "main",
                  "baseRefOid": "github-base",
                  "headRefName": "fix/github-pr",
                  "headRefOid": "github-head"
                }
                """
            raise AssertionError(args)

        with (
            mock.patch.object(prepare_local, "current_branch", return_value="fix/github-pr"),
            mock.patch.object(prepare_local, "run", side_effect=fake_run),
        ):
            event = prepare_local.github_pr_event_for_current_branch("owner/repo")

        self.assertIsNotNone(event)
        self.assertEqual(event["pull_request"]["title"], "fix: github pr")
        self.assertEqual(event["pull_request"]["body"], "remote body")

    def test_github_pr_event_for_current_branch_returns_none_when_fetch_fails(self) -> None:
        with (
            mock.patch.object(prepare_local, "current_branch", return_value="fix/github-pr"),
            mock.patch.object(prepare_local, "run", side_effect=subprocess.CalledProcessError(1, ["gh"])),
        ):
            self.assertIsNone(prepare_local.github_pr_event_for_current_branch("owner/repo"))

    def test_gitignore_excludes_root_review_snapshots(self) -> None:
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        for path in (
            "pr_description.txt",
            "pr_diff.txt",
            "spec_context.md",
            "review.json",
            ".local_review_baseline.status",
            "implementation_summary.md",
        ):
            self.assertIn(f"/{path}", gitignore)

    def test_remote_repo_from_url_accepts_ssh_https_and_dotted_names(self) -> None:
        self.assertEqual(
            prepare_local.remote_repo_from_url("git@github.com:owner/repo.name.git"),
            "owner/repo.name",
        )
        self.assertEqual(
            prepare_local.remote_repo_from_url("https://github.com/owner/repo.name.git"),
            "owner/repo.name",
        )

    def test_local_worktree_diff_includes_committed_unstaged_staged_deleted_and_untracked_files(self) -> None:
        def scenario(directory: Path) -> None:
            base_sha = self.init_repo(directory)
            (directory / "core/foo.py").write_text("committed\n", encoding="utf-8")
            self.git(directory, "add", "core/foo.py")
            self.git(directory, "commit", "-m", "change foo")

            (directory / "core/foo.py").write_text("unstaged\n", encoding="utf-8")
            (directory / "core/staged.py").write_text("staged\n", encoding="utf-8")
            self.git(directory, "add", "core/staged.py")
            (directory / "core/deleted.py").unlink()
            (directory / "core/untracked.py").write_text("untracked\n", encoding="utf-8")
            (directory / "pr_diff.txt").write_text("snapshot\n", encoding="utf-8")
            status_before = self.git(directory, "status", "--porcelain=v1", "-z", "--untracked-files=all")

            diff_text = prepare_local.build_pr_diff.convert(prepare_local.local_worktree_diff(base_sha, 3))
            status_after = self.git(directory, "status", "--porcelain=v1", "-z", "--untracked-files=all")

            self.assertEqual(status_after, status_before)
            self.assertIn("FILE core/foo.py", diff_text)
            self.assertIn("RIGHT    1 | unstaged", diff_text)
            self.assertIn("FILE core/staged.py", diff_text)
            self.assertIn("FILE core/deleted.py", diff_text)
            self.assertIn("FILE core/untracked.py", diff_text)
            self.assertNotIn("FILE pr_diff.txt", diff_text)

        self.run_in_tempdir(scenario)

    def test_local_worktree_diff_excludes_ignored_untracked_files(self) -> None:
        def scenario(directory: Path) -> None:
            base_sha = self.init_repo(directory)
            (directory / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
            self.git(directory, "add", ".gitignore")
            self.git(directory, "commit", "-m", "ignore file")
            (directory / "ignored.txt").write_text("ignored\n", encoding="utf-8")

            diff_text = prepare_local.build_pr_diff.convert(prepare_local.local_worktree_diff(base_sha, 3))

            self.assertIn("FILE .gitignore", diff_text)
            self.assertNotIn("FILE ignored.txt", diff_text)

        self.run_in_tempdir(scenario)

    def test_local_worktree_diff_removes_staged_rename_source_from_snapshot(self) -> None:
        def scenario(directory: Path) -> None:
            base_sha = self.init_repo(directory)
            self.git(directory, "mv", "core/deleted.py", "core/renamed.py")

            raw_diff = "\n".join(prepare_local.local_worktree_diff(base_sha, 3))
            diff_text = prepare_local.build_pr_diff.convert(raw_diff.splitlines())

            self.assertIn("rename from core/deleted.py", raw_diff)
            self.assertIn("rename to core/renamed.py", raw_diff)
            self.assertIn("FILE core/renamed.py", diff_text)

        self.run_in_tempdir(scenario)

    def test_write_local_diff_rejects_empty_diff(self) -> None:
        def scenario(directory: Path) -> None:
            base_sha = self.init_repo(directory)

            with self.assertRaisesRegex(SystemExit, "no local changes to review"):
                prepare_local.write_local_diff(base_sha, Path("pr_diff.txt"))

        self.run_in_tempdir(scenario)

    def test_write_baseline_status_uses_fixed_ignored_root_path(self) -> None:
        def scenario(directory: Path) -> None:
            self.init_repo(directory)
            (directory / "core/foo.py").write_text("dirty\n", encoding="utf-8")
            self.git(directory, "mv", "core/deleted.py", "core/renamed.py")

            path = prepare_local.write_baseline_status()

            self.assertEqual(path, ".local_review_baseline.status")
            self.assertTrue((directory / ".local_review_baseline.status").exists())
            baseline = (directory / ".local_review_baseline.status").read_bytes()
            self.assertIn(b" M core/foo.py\0", baseline)
            self.assertIn(b"R  core/renamed.py\0core/deleted.py\0", baseline)

        self.run_in_tempdir(scenario)


if __name__ == "__main__":
    unittest.main()
