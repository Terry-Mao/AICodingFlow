from __future__ import annotations

import unittest
from unittest import mock

from tests.script_imports import import_script


commit_impl = import_script(
    ".github/scripts/commit_implementation_branch.py",
    "commit_implementation_branch",
)


class CommitImplementationBranchTest(unittest.TestCase):
    def test_implementation_paths_excludes_workflow_temp_files(self) -> None:
        self.assertEqual(
            commit_impl.implementation_paths(
                [
                    "issue_context.json",
                    "implementation_summary.md",
                    "pr-metadata.json",
                    ".github/scripts/post_pr_review.py",
                    "tests/test_post_pr_review.py",
                ]
            ),
            [".github/scripts/post_pr_review.py", "tests/test_post_pr_review.py"],
        )

    def test_status_paths_parses_simple_and_rename_entries(self) -> None:
        output = " M file.py\0?? new.py\0R  renamed.py\0old.py\0"
        with mock.patch.object(commit_impl, "run", return_value=output):
            self.assertEqual(commit_impl.status_paths(), ["file.py", "new.py", "renamed.py"])

    def test_has_remote_branch_uses_ls_remote_exit_status(self) -> None:
        with mock.patch("subprocess.run", return_value=mock.Mock(returncode=0)):
            self.assertTrue(commit_impl.has_remote_branch("feature"))
        with mock.patch("subprocess.run", return_value=mock.Mock(returncode=2)):
            self.assertFalse(commit_impl.has_remote_branch("missing"))

    def test_switch_to_existing_branch_fetches_and_checks_out_remote(self) -> None:
        calls: list[list[str]] = []
        with (
            mock.patch.object(commit_impl, "has_remote_branch", return_value=True),
            mock.patch.object(commit_impl, "run", side_effect=lambda args, **_: calls.append(args) or ""),
        ):
            commit_impl.switch_to_branch("feature", "origin/main")

        self.assertEqual(
            calls,
            [
                ["git", "fetch", "origin", "+refs/heads/feature:refs/remotes/origin/feature"],
                ["git", "switch", "-C", "feature", "origin/feature"],
            ],
        )

    def test_switch_to_new_branch_uses_base_ref(self) -> None:
        calls: list[list[str]] = []
        with (
            mock.patch.object(commit_impl, "has_remote_branch", return_value=False),
            mock.patch.object(commit_impl, "run", side_effect=lambda args, **_: calls.append(args) or ""),
        ):
            commit_impl.switch_to_branch("feature", "origin/main")

        self.assertEqual(calls, [["git", "switch", "-C", "feature", "origin/main"]])

    def test_stash_worktree_saves_all_changes(self) -> None:
        calls: list[list[str]] = []
        with mock.patch.object(
            commit_impl,
            "run",
            side_effect=lambda args, **_: calls.append(args) or "Saved working directory",
        ):
            self.assertTrue(commit_impl.stash_worktree())

        self.assertEqual(
            calls,
            [
                [
                    "git",
                    "stash",
                    "push",
                    "--include-untracked",
                    "-m",
                    "implementation workflow handoff",
                ]
            ],
        )

    def test_stash_worktree_returns_false_when_git_has_nothing_to_save(self) -> None:
        with mock.patch.object(commit_impl, "run", return_value="No local changes to save"):
            self.assertFalse(commit_impl.stash_worktree())

    def test_commit_and_push_stashes_before_switching_branch(self) -> None:
        calls: list[list[str]] = []
        with (
            mock.patch.object(commit_impl, "load_json", side_effect=[
                {"default_branch": "main"},
                {"branch_name": "spec/implement-issue-18-workflow", "pr_title": "feat: add workflow"},
            ]),
            mock.patch.object(commit_impl, "status_paths", side_effect=[
                ["app.py", "pr-metadata.json"],
                ["app.py", "pr-metadata.json"],
            ]),
            mock.patch.object(commit_impl, "implementation_paths", wraps=commit_impl.implementation_paths),
            mock.patch.object(commit_impl, "has_remote_branch", return_value=False),
            mock.patch.object(
                commit_impl,
                "run",
                side_effect=lambda args, **kwargs: calls.append(args) or (
                    "app.py" if args == ["git", "diff", "--cached", "--name-only"] else
                    "abc123" if args == ["git", "rev-parse", "HEAD"] else
                    "Saved working directory" if args[:3] == ["git", "stash", "push"] else
                    ""
                ),
            ),
        ):
            result = commit_impl.commit_and_push(
                mock.Mock(),
                mock.Mock(),
                "github-actions[bot]",
                "41898282+github-actions[bot]@users.noreply.github.com",
            )

        self.assertEqual(result, {"changed": "true", "branch": "spec/implement-issue-18-workflow", "sha": "abc123"})
        self.assertLess(calls.index(["git", "stash", "push", "--include-untracked", "-m", "implementation workflow handoff"]), calls.index(["git", "switch", "-C", "spec/implement-issue-18-workflow", "HEAD"]))
        self.assertLess(calls.index(["git", "switch", "-C", "spec/implement-issue-18-workflow", "HEAD"]), calls.index(["git", "stash", "pop"]))

    def test_commit_and_push_recomputes_paths_after_restore(self) -> None:
        with (
            mock.patch.object(commit_impl, "load_json", side_effect=[
                {"default_branch": "main"},
                {"branch_name": "spec/implement-issue-18", "pr_title": "fix: update workflow"},
            ]),
            mock.patch.object(commit_impl, "status_paths", side_effect=[
                ["app.py"],
                ["issue_context.json", "pr-metadata.json"],
            ]),
            mock.patch.object(commit_impl, "stash_worktree", return_value=True),
            mock.patch.object(commit_impl, "switch_to_branch"),
            mock.patch.object(commit_impl, "restore_stash"),
            mock.patch.object(commit_impl, "run", return_value=""),
        ):
            result = commit_impl.commit_and_push(
                mock.Mock(),
                mock.Mock(),
                "github-actions[bot]",
                "41898282+github-actions[bot]@users.noreply.github.com",
            )

        self.assertEqual(result, {"changed": "false", "branch": "spec/implement-issue-18", "sha": ""})


if __name__ == "__main__":
    unittest.main()
