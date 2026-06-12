from __future__ import annotations

import unittest
from unittest import mock

from script_imports import import_script


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
                    "pr_comment_context.json",
                    "pr_event.json",
                    "pr_description.md",
                    "pr_description.txt",
                    "pr_diff.txt",
                    "review_discussion_context.json",
                    "review.json",
                    "review_comment_ids.json",
                    "resolved_review_comments.json",
                    ".local_review_baseline.status",
                    ".codex-runtime/skills/implement-specs/SKILL.md",
                    "implementation-output/.github/skills/update-dedupe/SKILL.md",
                    ".github/scripts/post_pr_review.py",
                    ".github/scripts/__pycache__/post_pr_review.cpython-312.pyc",
                    ".github/skills/review-pr-repo/SKILL.md",
                    "tests/test_post_pr_review.py",
                    "tests/__pycache__/test_post_pr_review.cpython-312.pyc",
                ]
            ),
            [
                ".github/scripts/post_pr_review.py",
                ".github/skills/review-pr-repo/SKILL.md",
                "tests/test_post_pr_review.py",
            ],
        )

    def test_status_paths_parses_simple_and_rename_entries(self) -> None:
        output = " M file.py\0?? new.py\0R  renamed.py\0old.py\0"
        with mock.patch.object(commit_impl, "run", return_value=output):
            self.assertEqual(commit_impl.status_paths(), ["file.py", "new.py", "renamed.py"])

    def test_run_preserves_porcelain_status_spacing(self) -> None:
        result = mock.Mock(stdout=" M .github/scripts/post_pr_review.py\0")
        with mock.patch("subprocess.run", return_value=result):
            self.assertEqual(
                commit_impl.run(["git", "status", "--porcelain=v1", "-z"], capture=True),
                " M .github/scripts/post_pr_review.py\0",
            )

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

    def test_stage_implementation_changes_stages_intended_paths_and_unstages_workflow_temp_files(self) -> None:
        calls: list[list[str]] = []
        with (
            mock.patch.object(commit_impl, "existing_temp_workflow_paths", return_value=["pr-metadata.json"]),
            mock.patch.object(commit_impl, "run", side_effect=lambda args, **_: calls.append(args) or ""),
        ):
            commit_impl.stage_implementation_changes([".github/skills/review-pr-repo/SKILL.md", "tests/test_file.py"])

        self.assertEqual(
            calls,
            [
                ["git", "add", "-A", "--", ".github/skills/review-pr-repo/SKILL.md", "tests/test_file.py"],
                ["git", "reset", "--", "pr-metadata.json"],
            ],
        )

    def test_stage_implementation_changes_skips_reset_when_no_temp_files_exist(self) -> None:
        calls: list[list[str]] = []
        with (
            mock.patch.object(commit_impl, "existing_temp_workflow_paths", return_value=[]),
            mock.patch.object(commit_impl, "run", side_effect=lambda args, **_: calls.append(args) or ""),
        ):
            commit_impl.stage_implementation_changes(["app.py"])

        self.assertEqual(calls, [["git", "add", "-A", "--", "app.py"]])

    def test_validate_staged_paths_rejects_generated_files(self) -> None:
        with self.assertRaisesRegex(SystemExit, "refusing to commit generated files"):
            commit_impl.validate_staged_paths(
                [
                    ".github/scripts/post_pr_review.py",
                    ".github/scripts/__pycache__/post_pr_review.cpython-312.pyc",
                ]
            )

    def test_validate_workflow_push_permissions_requires_token_for_workflow_files(self) -> None:
        with self.assertRaisesRegex(SystemExit, "WORKFLOW_UPDATE_TOKEN"):
            commit_impl.validate_workflow_push_permissions([".github/workflows/review-pr.yml"], "")
        commit_impl.validate_workflow_push_permissions([".github/workflows/review-pr.yml"], "token")

    def test_push_repo_prefers_agent_push_repo(self) -> None:
        self.assertEqual(
            commit_impl.push_repo(
                {
                    "repository": "owner/base",
                    "agent_push_repo_full_name": "owner/head",
                }
            ),
            "owner/head",
        )

    def test_validate_intended_files_rejects_missing_and_unexpected_files(self) -> None:
        commit_impl.validate_intended_files([".github/skills/review-pr-repo/SKILL.md", "app.py"], ["app.py", ".github/skills/review-pr-repo/SKILL.md"])
        with self.assertRaisesRegex(SystemExit, "without implementation changes"):
            commit_impl.validate_intended_files(["app.py"], ["app.py", ".github/skills/review-pr-repo/SKILL.md"])
        with self.assertRaisesRegex(SystemExit, "not listed in intended_files"):
            commit_impl.validate_intended_files(["app.py", "tests/test_app.py"], ["app.py"])

    def test_commit_and_push_stashes_before_switching_branch(self) -> None:
        calls: list[list[str]] = []
        with (
            mock.patch.dict("os.environ", {"GITHUB_TOKEN": "github-token"}, clear=False),
            mock.patch.object(commit_impl, "load_json", side_effect=[
                {"default_branch": "main", "agent_push_repo_full_name": "owner/repo"},
                {
                    "branch_name": "spec/implement-issue-18-workflow",
                    "pr_title": "feat: add workflow",
                    "intended_files": ["app.py"],
                },
            ]),
            mock.patch.object(commit_impl, "status_paths", side_effect=[
                ["app.py", "pr-metadata.json"],
                ["app.py", "pr-metadata.json"],
            ]),
            mock.patch.object(commit_impl, "implementation_paths", wraps=commit_impl.implementation_paths),
            mock.patch.object(commit_impl, "has_remote_branch", return_value=False),
            mock.patch.object(commit_impl, "staged_paths", return_value=["app.py"]),
            mock.patch.object(
                commit_impl,
                "run",
                side_effect=lambda args, **kwargs: calls.append(args) or (
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
        self.assertLess(
            calls.index(["git", "remote", "set-url", "origin", "https://x-access-token:github-token@github.com/owner/repo.git"]),
            calls.index(["git", "fetch", "origin", "main"]),
        )
        self.assertLess(
            calls.index(["git", "stash", "push", "--include-untracked", "-m", "implementation workflow handoff"]),
            calls.index(["git", "switch", "-C", "spec/implement-issue-18-workflow", "HEAD"]),
        )
        self.assertLess(
            calls.index(["git", "switch", "-C", "spec/implement-issue-18-workflow", "HEAD"]),
            calls.index(["git", "stash", "pop"]),
        )
        self.assertIn(["git", "add", "-A", "--", "app.py"], calls)

    def test_commit_and_push_recomputes_paths_after_restore(self) -> None:
        with (
            mock.patch.object(commit_impl, "load_json", side_effect=[
                {"default_branch": "main"},
                {
                    "branch_name": "spec/implement-issue-18",
                    "pr_title": "fix: update workflow",
                    "intended_files": ["app.py"],
                },
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

    def test_commit_and_push_uses_workflow_token_for_workflow_files(self) -> None:
        calls: list[list[str]] = []
        with (
            mock.patch.dict("os.environ", {"GITHUB_TOKEN": "github-token", "WORKFLOW_UPDATE_TOKEN": "workflow-token"}, clear=False),
            mock.patch.object(commit_impl, "load_json", side_effect=[
                {"default_branch": "main", "repository": "owner/repo"},
                {
                    "branch_name": "spec/implement-issue-51",
                    "pr_title": "fix: update workflow",
                    "intended_files": [".github/workflows/review-pr.yml"],
                },
            ]),
            mock.patch.object(commit_impl, "status_paths", side_effect=[
                [".github/workflows/review-pr.yml"],
                [".github/workflows/review-pr.yml"],
            ]),
            mock.patch.object(commit_impl, "has_remote_branch", return_value=False),
            mock.patch.object(commit_impl, "staged_paths", return_value=[".github/workflows/review-pr.yml"]),
            mock.patch.object(commit_impl, "existing_temp_workflow_paths", return_value=[]),
            mock.patch.object(
                commit_impl,
                "run",
                side_effect=lambda args, **kwargs: calls.append(args) or (
                    "abc123" if args == ["git", "rev-parse", "HEAD"] else
                    "includeif.gitdir:/home/runner/work/example/example/.git.path"
                    if args[:5] == ["git", "config", "--local", "--name-only", "--get-regexp"] else
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

        self.assertEqual(result, {"changed": "true", "branch": "spec/implement-issue-51", "sha": "abc123"})
        commit_index = calls.index(["git", "commit", "-m", "fix: update workflow"])
        workflow_remote_index = calls.index(["git", "remote", "set-url", "origin", "https://x-access-token:workflow-token@github.com/owner/repo.git"])
        self.assertLess(
            calls.index(["git", "remote", "set-url", "origin", "https://x-access-token:github-token@github.com/owner/repo.git"]),
            calls.index(["git", "fetch", "origin", "main"]),
        )
        self.assertLess(
            commit_index,
            workflow_remote_index,
        )
        self.assertLess(
            max(
                index
                for index, call in enumerate(calls)
                if call == ["git", "config", "--local", "--unset-all", "http.https://github.com/.extraheader"]
                and index > commit_index
            ),
            workflow_remote_index,
        )
        self.assertLess(
            max(
                index
                for index, call in enumerate(calls)
                if call == ["git", "config", "--local", "--name-only", "--get-regexp", r"^includeIf\..*\.path$"]
                and index > commit_index
            ),
            workflow_remote_index,
        )
        self.assertLess(
            calls.index(["git", "config", "--local", "--unset-all", "includeif.gitdir:/home/runner/work/example/example/.git.path"]),
            workflow_remote_index,
        )
        self.assertLess(
            workflow_remote_index,
            calls.index(["git", "push", "-u", "origin", "spec/implement-issue-51"]),
        )

    def test_commit_and_push_fails_before_commit_when_workflow_token_is_missing(self) -> None:
        calls: list[list[str]] = []
        with (
            mock.patch.dict("os.environ", {}, clear=True),
            mock.patch.object(commit_impl, "load_json", side_effect=[
                {"default_branch": "main", "repository": "owner/repo"},
                {
                    "branch_name": "spec/implement-issue-51",
                    "pr_title": "fix: update workflow",
                    "intended_files": [".github/workflows/review-pr.yml"],
                },
            ]),
            mock.patch.object(commit_impl, "status_paths", side_effect=[
                [".github/workflows/review-pr.yml"],
                [".github/workflows/review-pr.yml"],
            ]),
            mock.patch.object(commit_impl, "has_remote_branch", return_value=False),
            mock.patch.object(commit_impl, "staged_paths", return_value=[".github/workflows/review-pr.yml"]),
            mock.patch.object(commit_impl, "existing_temp_workflow_paths", return_value=[]),
            mock.patch.object(
                commit_impl,
                "run",
                side_effect=lambda args, **kwargs: calls.append(args) or (
                    "Saved working directory" if args[:3] == ["git", "stash", "push"] else ""
                ),
            ),
        ):
            with self.assertRaisesRegex(SystemExit, "WORKFLOW_UPDATE_TOKEN"):
                commit_impl.commit_and_push(
                    mock.Mock(),
                    mock.Mock(),
                    "github-actions[bot]",
                    "41898282+github-actions[bot]@users.noreply.github.com",
                )

        self.assertNotIn(["git", "commit", "-m", "fix: update workflow"], calls)


if __name__ == "__main__":
    unittest.main()
