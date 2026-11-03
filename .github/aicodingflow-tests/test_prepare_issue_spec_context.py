#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import tempfile
import unittest
from pathlib import Path

from script_imports import import_script


prepare_issue_spec_context = import_script(
    ".github/scripts/prepare_issue_spec_context.py",
    "prepare_issue_spec_context",
)


class PrepareIssueSpecContextTest(unittest.TestCase):
    def test_spec_paths_use_issue_directory_and_spec_branch(self) -> None:
        self.assertEqual(
            prepare_issue_spec_context.spec_paths(32),
            {
                "spec_dir": "specs/issue-32",
                "product_spec": "specs/issue-32/product.md",
                "tech_spec": "specs/issue-32/tech.md",
                "branch_name": "spec/issue-32",
                "target_branch": "spec/issue-32",
            },
        )

    def test_triggering_comment_extracts_stable_fields(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            event_path = Path(directory) / "event.json"
            event_path.write_text(
                json.dumps(
                    {
                        "comment": {
                            "body": "@codex please spec this",
                            "created_at": "2026-05-13T00:00:00Z",
                            "html_url": "https://github.test/comment",
                            "user": {"login": "maintainer"},
                        }
                    }
                ),
                encoding="utf-8",
            )

            self.assertEqual(
                prepare_issue_spec_context.triggering_comment(str(event_path)),
                {
                    "id": None,
                    "author": "maintainer",
                    "body": "@codex please spec this",
                    "created_at": "2026-05-13T00:00:00Z",
                    "url": "https://github.test/comment",
                },
            )

    def test_remove_triggering_comment_filters_by_id_or_url(self) -> None:
        comments = [
            {"id": 1, "html_url": "https://github.test/one", "body": "old"},
            {"id": 2, "html_url": "https://github.test/two", "body": "trigger"},
            {"id": 3, "html_url": "https://github.test/three", "body": "later"},
        ]

        self.assertEqual(
            prepare_issue_spec_context.remove_triggering_comment(
                comments,
                {"id": 2, "url": "https://github.test/two"},
            ),
            [
                {"id": 1, "html_url": "https://github.test/one", "body": "old"},
                {"id": 3, "html_url": "https://github.test/three", "body": "later"},
            ],
        )

    def test_collect_coauthor_directives_deduplicates_valid_lines(self) -> None:
        self.assertEqual(
            prepare_issue_spec_context.collect_coauthor_directives(
                "Co-authored-by: Ada Lovelace <ada@example.com>",
                "text\nco-authored-by: Ada Lovelace <ada@example.com>\nCo-authored-by: Grace <grace@example.com>",
            ),
            [
                "Co-authored-by: Ada Lovelace <ada@example.com>",
                "Co-authored-by: Grace <grace@example.com>",
            ],
        )

    def test_should_run_when_ready_to_spec_label_is_added_to_assigned_issue(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            event_path = Path(directory) / "event.json"
            event_path.write_text(
                json.dumps({"action": "labeled", "label": {"name": "ready-to-spec"}}),
                encoding="utf-8",
            )
            args = argparse.Namespace(
                force=False,
                event_name="issues",
                event_path=str(event_path),
                agent_login="codex[bot]",
            )
            issue = {
                "labels": [{"name": "ready-to-spec"}],
                "assignees": [{"login": "codex[bot]"}],
            }

            self.assertEqual(
                prepare_issue_spec_context.should_run(args, issue),
                (True, "ready-to-spec label added to issue assigned to codex[bot]"),
            )

    def test_should_not_run_for_unrelated_issue_label_event(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            event_path = Path(directory) / "event.json"
            event_path.write_text(json.dumps({"action": "labeled", "label": {"name": "bug"}}), encoding="utf-8")
            args = argparse.Namespace(
                force=False,
                event_name="issues",
                event_path=str(event_path),
                agent_login="codex",
            )
            issue = {"labels": [{"name": "ready-to-spec"}], "assignees": [{"login": "codex"}]}

            self.assertEqual(
                prepare_issue_spec_context.should_run(args, issue),
                (False, "issue label event is not ready-to-spec"),
            )

    def test_should_run_when_agent_is_assigned_to_ready_to_spec_issue(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            event_path = Path(directory) / "event.json"
            event_path.write_text(json.dumps({"action": "assigned", "assignee": {"login": "codex"}}), encoding="utf-8")
            args = argparse.Namespace(
                force=False,
                event_name="issues",
                event_path=str(event_path),
                agent_login="codex",
            )
            issue = {"labels": [{"name": "ready-to-spec"}], "assignees": [{"login": "codex"}]}

            self.assertEqual(
                prepare_issue_spec_context.should_run(args, issue),
                (True, "ready-to-spec issue assigned to codex"),
            )

    def test_should_not_run_when_issue_assignment_is_for_someone_else(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            event_path = Path(directory) / "event.json"
            event_path.write_text(json.dumps({"action": "assigned", "assignee": {"login": "alice"}}), encoding="utf-8")
            args = argparse.Namespace(
                force=False,
                event_name="issues",
                event_path=str(event_path),
                agent_login="codex",
            )
            issue = {
                "labels": [{"name": "ready-to-spec"}],
                "assignees": [{"login": "codex"}, {"login": "alice"}],
            }

            self.assertEqual(
                prepare_issue_spec_context.should_run(args, issue),
                (False, "issue assignment event is not for codex"),
            )

    def test_should_not_run_for_reopened_ready_to_spec_assigned_issue(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            event_path = Path(directory) / "event.json"
            event_path.write_text(json.dumps({"action": "reopened"}), encoding="utf-8")
            args = argparse.Namespace(
                force=False,
                event_name="issues",
                event_path=str(event_path),
                agent_login="codex",
            )
            issue = {"labels": [{"name": "ready-to-spec"}], "assignees": [{"login": "codex"}]}

            self.assertEqual(
                prepare_issue_spec_context.should_run(args, issue),
                (False, "issue event action is not a spec trigger: reopened"),
            )

    def test_workflow_dispatch_still_requires_ready_label_and_assignment(self) -> None:
        args = argparse.Namespace(
            force=False,
            event_name="workflow_dispatch",
            event_path="",
            agent_login="codex",
        )

        self.assertEqual(
            prepare_issue_spec_context.should_run(args, {"labels": [], "assignees": [{"login": "codex"}]}),
            (False, "issue is missing ready-to-spec"),
        )
        self.assertEqual(
            prepare_issue_spec_context.should_run(
                args,
                {"labels": [{"name": "ready-to-spec"}], "assignees": []},
            ),
            (False, "ready-to-spec issue is not assigned to or mentioning the configured agent"),
        )
        self.assertEqual(
            prepare_issue_spec_context.should_run(
                args,
                {"labels": [{"name": "ready-to-spec"}], "assignees": [{"login": "codex"}]},
            ),
            (True, "ready-to-spec assigned to codex"),
        )

    def test_should_not_run_when_issue_is_already_ready_to_implement(self) -> None:
        args = argparse.Namespace(
            force=False,
            event_name="issues",
            event_path="",
            agent_login="codex",
        )
        issue = {
            "labels": [{"name": "ready-to-spec"}, {"name": "ready-to-implement"}],
            "assignees": [{"login": "codex"}],
        }

        self.assertEqual(
            prepare_issue_spec_context.should_run(args, issue),
            (False, "issue is already ready-to-implement"),
        )

    def test_should_run_for_ready_to_spec_comment_mention(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            event_path = Path(directory) / "event.json"
            event_path.write_text(json.dumps({"comment": {"body": "@codex please spec this"}}), encoding="utf-8")
            args = argparse.Namespace(
                force=False,
                event_name="issue_comment",
                event_path=str(event_path),
                agent_login="codex",
            )
            issue = {"labels": [{"name": "ready-to-spec"}], "assignees": []}

            self.assertEqual(
                prepare_issue_spec_context.should_run(args, issue),
                (True, "ready-to-spec comment mentioned @codex"),
            )

    def test_should_run_for_visible_html_block_mention(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            event_path = Path(directory) / "event.json"
            event_path.write_text(
                json.dumps({"comment": {"body": "<div>\n@codex please spec\n</div>"}}),
                encoding="utf-8",
            )
            args = argparse.Namespace(
                force=False,
                event_name="issue_comment",
                event_path=str(event_path),
                agent_login="codex",
            )
            issue = {"labels": [{"name": "ready-to-spec"}], "assignees": []}
            self.assertEqual(
                prepare_issue_spec_context.should_run(args, issue),
                (True, "ready-to-spec comment mentioned @codex"),
            )

    def test_should_run_distinguishes_escaped_and_real_mentions_in_one_paragraph(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            event_path = Path(directory) / "event.json"
            args = argparse.Namespace(
                force=False,
                event_name="issue_comment",
                event_path=str(event_path),
                agent_login="codex",
            )
            issue = {"labels": [{"name": "ready-to-spec"}], "assignees": []}
            cases = (
                ("please \\@codex /spec", False),
                ("\\@codex is literal, @codex /spec", True),
            )
            for comment, should_trigger in cases:
                with self.subTest(comment=comment):
                    event_path.write_text(json.dumps({"comment": {"body": comment}}), encoding="utf-8")
                    result, _ = prepare_issue_spec_context.should_run(args, issue)
                    self.assertEqual(result, should_trigger)

    def test_should_not_run_for_pull_request_comment_mention(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            event_path = Path(directory) / "event.json"
            event_path.write_text(
                json.dumps(
                    {
                        "issue": {"pull_request": {"url": "https://api.github.test/repos/owner/repo/pulls/61"}},
                        "comment": {"body": "@codex please spec this"},
                    }
                ),
                encoding="utf-8",
            )
            args = argparse.Namespace(
                force=False,
                event_name="issue_comment",
                event_path=str(event_path),
                agent_login="codex",
            )
            issue = {"labels": [{"name": "ready-to-spec"}], "assignees": []}

            self.assertEqual(
                prepare_issue_spec_context.should_run(args, issue),
                (False, "PR comments are handled by review-pr workflow"),
            )

    def test_should_not_run_for_partial_or_quoted_agent_mention(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            event_path = Path(directory) / "event.json"
            event_path.write_text(
                json.dumps({"comment": {"body": "@codex-action should handle this\n> @codex old text"}}),
                encoding="utf-8",
            )
            args = argparse.Namespace(
                force=False,
                event_name="issue_comment",
                event_path=str(event_path),
                agent_login="codex",
            )
            issue = {"labels": [{"name": "ready-to-spec"}], "assignees": []}

            self.assertEqual(
                prepare_issue_spec_context.should_run(args, issue),
                (False, "ready-to-spec issue is not assigned to or mentioning the configured agent"),
            )

    def test_comment_mentions_login_uses_login_boundaries(self) -> None:
        self.assertTrue(prepare_issue_spec_context.comment_mentions_login("please @codex.", "codex"))
        self.assertTrue(prepare_issue_spec_context.comment_mentions_login("please @codex[bot]", "codex[bot]"))
        self.assertFalse(prepare_issue_spec_context.comment_mentions_login("please @codex-action", "codex"))
        self.assertFalse(prepare_issue_spec_context.comment_mentions_login("> @codex quoted", "codex"))

    def test_escaped_at_sign_only_masks_its_own_mention(self) -> None:
        self.assertFalse(prepare_issue_spec_context.comment_mentions_login("please \\@codex /spec", "codex"))
        self.assertTrue(prepare_issue_spec_context.comment_mentions_login("\\@codex is literal, @codex /spec", "codex"))
        self.assertTrue(prepare_issue_spec_context.comment_mentions_login("please \\@codex, then @codex /spec", "codex"))
        self.assertTrue(prepare_issue_spec_context.comment_mentions_login("\\\\@codex /spec", "codex"))

    def test_comment_mentions_login_uses_markdown_block_boundaries(self) -> None:
        code_only = (
            "- item\n\n---\n    @codex /spec",
            "- item\n\n# Heading\n    @codex /spec",
            "- item\n\n> quoted\n\n    @codex /spec",
            "<code>@codex /spec</code>",
            "<code data-note='>'>@codex /spec</code>",
            "<div><pre>@codex /spec</pre></div>",
            "<!-- @codex /spec -->",
            "<script>@codex /spec</script>",
            "\\@codex /spec",
        )
        for comment in code_only:
            with self.subTest(comment=comment):
                self.assertFalse(prepare_issue_spec_context.comment_mentions_login(comment, "codex"))

        visible_after_block = (
            "- item\n\n---\n@codex please spec",
            "- item\n\n# Heading\n@codex please spec",
            "<code>sample</code> @codex please spec",
            "<code/> @codex please spec",
            "<div>@codex please spec</div>",
            "<div>\n@codex please spec\n</div>",
        )
        for comment in visible_after_block:
            with self.subTest(comment=comment):
                self.assertTrue(prepare_issue_spec_context.comment_mentions_login(comment, "codex"))

    def test_comment_mentions_login_ignores_code(self) -> None:
        code_only = (
            "```text\n@codex /spec\n```",
            "~~~~log\n@codex /spec\n~~~~",
            "````\n@codex\n```\n@codex\n````",
            "Here is `@codex` in a sample.",
            "Here is ``@codex`` in a sample.",
            "Here is `a multiline\n@codex` sample.",
            "@co`sample`dex is not a mention",
            "    @codex in indented code",
            "\t@codex in indented code",
            "Intro\n\n    @codex in indented code",
            "# Heading\n    @codex in indented code",
            "- item\n\n        @codex in list code",
            "- item\n\n    ~~~text\n    @codex /spec\n    ~~~",
            "- item\n    ```text\n    @codex /spec\n    ```",
            "Title\n===\n    @codex /spec",
            "Title\n---\n    @codex /spec",
            "---\n    @codex /spec",
            "* * *\n    @codex /spec",
        )
        for comment in code_only:
            with self.subTest(comment=comment):
                self.assertFalse(prepare_issue_spec_context.comment_mentions_login(comment, "codex"))

        self.assertTrue(prepare_issue_spec_context.comment_mentions_login("`@codex`\n@codex please spec", "codex"))
        self.assertTrue(prepare_issue_spec_context.comment_mentions_login("```\n@codex\n```\n@codex please spec", "codex"))
        self.assertTrue(prepare_issue_spec_context.comment_mentions_login("- item\n\n    ~~~\n    @codex\n    ~~~\n    @codex please spec", "codex"))

    def test_comment_mentions_login_keeps_indented_paragraph_and_list_text(self) -> None:
        visible_comments = (
            "Please\n    @codex please spec",
            "- item @codex please spec",
            "- item\n    @codex please spec",
            "- item\n\n    @codex please spec",
        )
        for comment in visible_comments:
            with self.subTest(comment=comment):
                self.assertTrue(prepare_issue_spec_context.comment_mentions_login(comment, "codex"))

    def test_list_item_marker_can_open_fenced_code(self) -> None:
        code_only = (
            "- ```text\n  @codex /spec\n  ```",
            "1. ~~~text\n   @codex /spec\n   ~~~",
            "- parent\n  - ```text\n    @codex /spec\n    ```",
        )
        for comment in code_only:
            with self.subTest(comment=comment):
                self.assertFalse(prepare_issue_spec_context.comment_mentions_login(comment, "codex"))

        visible_after_fence = (
            "- ```text\n  sample\n  ```\n  @codex please spec",
            "- parent\n  - ~~~text\n    sample\n    ~~~\n    @codex please spec",
        )
        for comment in visible_after_fence:
            with self.subTest(comment=comment):
                self.assertTrue(prepare_issue_spec_context.comment_mentions_login(comment, "codex"))

    def test_list_item_padding_of_five_spaces_starts_code(self) -> None:
        code_only = (
            "-     @codex /spec",
            "1.     @codex /spec",
            "- parent\n  -     @codex /spec",
        )
        for comment in code_only:
            with self.subTest(comment=comment):
                self.assertFalse(prepare_issue_spec_context.comment_mentions_login(comment, "codex"))

        visible_comments = (
            "-    @codex please spec",
            "1.    @codex please spec",
            "-     sample\n\n  @codex please spec",
            "1.     sample\n\n@codex please spec",
        )
        for comment in visible_comments:
            with self.subTest(comment=comment):
                self.assertTrue(prepare_issue_spec_context.comment_mentions_login(comment, "codex"))

    def test_non_one_ordered_marker_does_not_interrupt_paragraph(self) -> None:
        visible_comments = (
            "paragraph\n2.     @codex /spec",
            "paragraph\n10.     @codex /spec",
            "- item\n  paragraph\n  2.     @codex /spec",
            "- outer\nparagraph\n  2.     @codex /spec",
        )
        for comment in visible_comments:
            with self.subTest(comment=comment):
                self.assertTrue(prepare_issue_spec_context.comment_mentions_login(comment, "codex"))

        code_only = (
            "2.     @codex /spec",
            "- outer\n2.     @codex /spec",
            "- outer\n10.     @codex /spec",
            "- outer\nparagraph\n2.     @codex /spec",
            "- outer\n  - inner\nparagraph\n2.     @codex /spec",
            "paragraph\n\n2.     @codex /spec",
            "paragraph\n1.     @codex /spec",
            "paragraph\n-     @codex /spec",
        )
        for comment in code_only:
            with self.subTest(comment=comment):
                self.assertFalse(prepare_issue_spec_context.comment_mentions_login(comment, "codex"))

        with tempfile.TemporaryDirectory() as directory:
            event_path = Path(directory) / "event.json"
            event_path.write_text(
                json.dumps({"comment": {"body": "paragraph\n2.     @codex /spec"}}),
                encoding="utf-8",
            )
            args = argparse.Namespace(
                force=False,
                event_name="issue_comment",
                event_path=str(event_path),
                agent_login="codex",
            )
            issue = {"labels": [{"name": "ready-to-spec"}], "assignees": []}
            self.assertEqual(
                prepare_issue_spec_context.should_run(args, issue),
                (True, "ready-to-spec comment mentioned @codex"),
            )

    def test_should_not_run_for_mention_only_in_code(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            event_path = Path(directory) / "event.json"
            args = argparse.Namespace(
                force=False,
                event_name="issue_comment",
                event_path=str(event_path),
                agent_login="codex",
            )
            issue = {"labels": [{"name": "ready-to-spec"}], "assignees": []}
            comments = (
                "Example:\n```yaml\nagent: @codex\n```\nUse `@codex` here.",
                "- item\n\n    ~~~text\n    @codex /spec\n    ~~~",
                "- ```text\n  @codex /spec\n  ```",
                "-     @codex /spec",
                "1.     @codex /spec",
                "- outer\n2.     @codex /spec",
                "- outer\nparagraph\n2.     @codex /spec",
                "Title\n===\n    @codex /spec",
                "---\n    @codex /spec",
            )
            for comment in comments:
                with self.subTest(comment=comment):
                    event_path.write_text(json.dumps({"comment": {"body": comment}}), encoding="utf-8")
                    self.assertEqual(
                        prepare_issue_spec_context.should_run(args, issue),
                        (False, "ready-to-spec issue is not assigned to or mentioning the configured agent"),
                    )

    def test_should_not_run_without_ready_to_spec(self) -> None:
        args = argparse.Namespace(
            force=False,
            event_name="issues",
            event_path="",
            agent_login="codex[bot]",
        )
        issue = {"labels": [{"name": "enhancement"}], "assignees": [{"login": "codex[bot]"}]}

        self.assertEqual(
            prepare_issue_spec_context.should_run(args, issue),
            (False, "issue is missing ready-to-spec"),
        )

    def test_should_not_run_without_configured_agent_login(self) -> None:
        args = argparse.Namespace(
            force=False,
            event_name="issues",
            event_path="",
            agent_login="",
        )
        issue = {"labels": [{"name": "ready-to-spec"}], "assignees": []}

        self.assertEqual(
            prepare_issue_spec_context.should_run(args, issue),
            (False, "agent login is not configured"),
        )


if __name__ == "__main__":
    unittest.main()
