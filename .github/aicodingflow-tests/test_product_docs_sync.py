from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from script_imports import ROOT, import_script


prepare = import_script(
    ".github/scripts/prepare_product_docs_sync_context.py",
    "prepare_product_docs_sync_context",
)
validator = import_script(
    ".github/scripts/validate_product_docs_sync_result.py",
    "validate_product_docs_sync_result",
)
body_writer = import_script(
    ".github/scripts/write_product_docs_sync_pr_body.py",
    "write_product_docs_sync_pr_body",
)
ledger_writer = import_script(
    ".github/scripts/update_product_docs_sync_ledger.py",
    "update_product_docs_sync_ledger",
)


def workflow() -> dict:
    return yaml.safe_load((ROOT / ".github/workflows/product-docs-sync.yml").read_text(encoding="utf-8"))


class ProductDocsSyncScriptTest(unittest.TestCase):
    def test_issue_numbers_are_deduplicated_from_closing_and_refs_references(self) -> None:
        pr = {
            "title": "Implement product flow refs #90",
            "body": "Refs #88, #89 and PR #123\n\nReferenced pull request #124 should not count.\nFixes #91",
            "closingIssuesReferences": [
                {"number": 87},
                {"number": "87"},
                {"number": 88},
                {"number": None},
            ]
        }

        self.assertEqual(prepare.issue_numbers(pr), [87, 88, 90, 89, 91])

    def test_prepare_reads_linked_specs_and_product_docs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "specs/issue-87").mkdir(parents=True)
            (root / "specs/issue-87/product.md").write_text("# Product\n", encoding="utf-8")
            (root / "docs/product/raw").mkdir(parents=True)
            (root / "docs/product/raw/overview.md").write_text("# Overview\n", encoding="utf-8")

            specs = prepare.read_specs(root, [87])
            docs = prepare.read_existing_product_docs(root)

        self.assertEqual(specs[0]["path"], "specs/issue-87/product.md")
        self.assertEqual(docs[0]["path"], "docs/product/raw/overview.md")

    def test_fetch_existing_issues_skips_issue_view_failures(self) -> None:
        def fetch_issue(_repo: str, number: int) -> dict:
            if number == 999999:
                raise subprocess.CalledProcessError(1, ["gh", "issue", "view", str(number)])
            return {"number": number, "title": f"Issue {number}"}

        with patch.object(prepare, "fetch_issue", side_effect=fetch_issue):
            issues, skipped = prepare.fetch_existing_issues("owner/repo", [87, 999999, 88])

        self.assertEqual([issue["number"] for issue in issues], [87, 88])
        self.assertEqual(skipped, [999999])

    def test_main_skips_missing_linked_issue_and_reads_specs_for_existing_issues(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            context_output = root / "context.json"
            markdown_output = root / "context.md"
            diff_output = root / "diff.md"
            existing_docs_output = root / "existing.md"
            github_output = root / "github-output.txt"
            (root / "specs/issue-87").mkdir(parents=True)
            (root / "specs/issue-87/product.md").write_text("# Existing issue spec\n", encoding="utf-8")
            (root / "specs/issue-999999").mkdir(parents=True)
            (root / "specs/issue-999999/product.md").write_text("# Missing issue spec\n", encoding="utf-8")
            pr = {
                "number": 123,
                "title": "Implement workflow",
                "body": "Refs #87 and #999999",
                "url": "https://example.test/pull/123",
                "state": "MERGED",
                "mergedAt": "2026-05-25T02:00:00Z",
                "author": {"login": "maintainer"},
                "headRefName": "feature/docs",
                "baseRefName": "main",
                "mergeCommit": {"oid": "abc123"},
                "files": [],
                "closingIssuesReferences": [],
                "labels": [],
            }

            def fetch_issue(_repo: str, number: int) -> dict:
                if number == 999999:
                    raise subprocess.CalledProcessError(1, ["gh", "issue", "view", str(number)])
                return {
                    "number": number,
                    "title": "Existing issue",
                    "body": "Readable issue.",
                    "url": "https://example.test/issues/87",
                    "state": "OPEN",
                    "labels": [],
                    "comments": [],
                }

            with patch.object(prepare.Path, "cwd", return_value=root):
                with patch.object(prepare, "fetch_default_branch", return_value="main"):
                    with patch.object(prepare, "fetch_pr", return_value=pr):
                        with patch.object(prepare, "fetch_issue", side_effect=fetch_issue):
                            with patch.object(prepare, "fetch_pr_diff", return_value="diff"):
                                with patch(
                                    "sys.argv",
                                    [
                                        "prepare_product_docs_sync_context.py",
                                        "--repo",
                                        "owner/repo",
                                        "--pr-number",
                                        "123",
                                        "--context-output",
                                        str(context_output),
                                        "--markdown-output",
                                        str(markdown_output),
                                        "--diff-output",
                                        str(diff_output),
                                        "--existing-docs-output",
                                        str(existing_docs_output),
                                        "--github-output",
                                        str(github_output),
                                    ],
                                ):
                                    self.assertEqual(prepare.main(), 0)

            payload = json.loads(context_output.read_text(encoding="utf-8"))
            markdown = markdown_output.read_text(encoding="utf-8")
            self.assertEqual([issue["number"] for issue in payload["linked_issues"]], [87])
            self.assertEqual([spec["path"] for spec in payload["specs"]], ["specs/issue-87/product.md"])
            self.assertNotIn("## Issue #999999", markdown)
            self.assertNotIn("specs/issue-999999/product.md", markdown)
            self.assertIn("should_run=true", github_output.read_text(encoding="utf-8"))

    def test_ledger_selects_first_unprocessed_pr(self) -> None:
        prs = [
            {"number": 87, "title": "done", "url": "https://example.test/87", "mergedAt": "2026-05-25T01:00:00Z"},
            {"number": 88, "title": "next", "url": "https://example.test/88", "mergedAt": "2026-05-25T02:00:00Z"},
        ]
        ledger = {"version": 1, "entries": [{"pr": 87, "docs_update": "not-needed", "recorded_at": "2026-05-25T03:00:00Z"}]}

        selected, skipped = prepare.select_unprocessed_pr(prs, ledger)

        self.assertEqual(selected["number"], 88)
        self.assertEqual(skipped[0]["number"], 87)
        self.assertEqual(skipped[0]["docs_update"], "not-needed")

    def test_product_docs_sync_prs_are_detected(self) -> None:
        generated_prs = [
            {"headRefName": "docs/product-docs-sync", "title": "Anything"},
            {"headRefName": "docs/product-docs-sync-pr-87", "title": "Anything"},
            {"headRefName": "docs/manual-docs", "title": "Update product docs"},
            {"headRefName": "docs/manual-docs", "title": "Update product docs for PR #87"},
            {"headRefName": "docs/manual-docs", "title": "Draft: Product docs sync for PR #87 needs confirmation"},
            {"headRefName": "docs/manual-docs", "title": "Record product docs sync decision for PR #87"},
        ]

        for pr in generated_prs:
            self.assertTrue(prepare.is_product_docs_sync_pr(pr))

        self.assertFalse(
            prepare.is_product_docs_sync_pr(
                {"headRefName": "docs/product-docs-manual", "title": "Update product documentation"}
            )
        )

    def test_fetch_merged_prs_skips_product_docs_sync_prs(self) -> None:
        start = prepare.parse_github_datetime("2026-05-25T00:00:00Z")
        end = prepare.parse_github_datetime("2026-05-26T00:00:00Z")
        pr_by_number = {
            87: {
                "number": 87,
                "title": "Update product docs for PR #86",
                "headRefName": "docs/product-docs-sync-pr-86",
                "mergedAt": "2026-05-25T01:00:00Z",
            },
            88: {
                "number": 88,
                "title": "Implement workflow",
                "headRefName": "feat/workflow",
                "mergedAt": "2026-05-25T02:00:00Z",
            },
        }

        with patch.object(prepare, "search_merged_pr_numbers", return_value=[87, 88]):
            with patch.object(prepare, "fetch_pr", side_effect=lambda _repo, number: pr_by_number[int(number)]):
                prs = prepare.fetch_merged_prs("owner/repo", start, end, "main")

        self.assertEqual([pr["number"] for pr in prs], [88])

    def test_update_ledger_records_docs_sync_decision(self) -> None:
        context = {
            "pr": {
                "number": 87,
                "title": "Implement flow",
                "url": "https://example.test/pull/87",
                "mergedAt": "2026-05-25T02:00:00Z",
                "mergeCommit": {"oid": "abc123"},
            }
        }
        result = {
            "docs_update": "required",
            "reason": "Product flow changed.",
            "affected_docs": ["docs/product/raw/flow.md"],
        }

        ledger = ledger_writer.update_ledger({"version": 1, "entries": []}, context, result, "2026-05-25T03:00:00Z")

        self.assertEqual(ledger["entries"][0]["pr"], 87)
        self.assertEqual(ledger["entries"][0]["docs_update"], "required")
        self.assertEqual(ledger["entries"][0]["merge_commit"], "abc123")
        self.assertEqual(ledger["entries"][0]["proposed_patch"], "")

    def test_validate_schema_accepts_required_contract(self) -> None:
        decision = validator.validate_schema(
            {
                "docs_update": "required",
                "reason": "Product flow changed.",
                "affected_docs": ["docs/product/raw/flow.md"],
                "source_context": ["PR #1"],
                "proposed_patch": "Document the new flow.",
            }
        )

        self.assertEqual(decision, "required")

    def test_validate_schema_rejects_unknown_decision(self) -> None:
        with self.assertRaises(SystemExit):
            validator.validate_schema(
                {
                    "docs_update": "maybe",
                    "reason": "x",
                    "affected_docs": [],
                    "source_context": [],
                    "proposed_patch": "x",
                }
            )

    def test_write_surface_requires_docs_change_for_uncertain(self) -> None:
        with self.assertRaises(SystemExit):
            validator.validate_write_surface("uncertain", ["product-docs-sync-result.json"])

    def test_write_surface_does_not_count_ledger_as_product_docs(self) -> None:
        with self.assertRaises(SystemExit):
            validator.validate_write_surface(
                "required",
                ["product-docs-sync-result.json", "docs/product/.product-docs-sync-ledger.json"],
            )

    def test_write_surface_allows_not_needed_ledger_update(self) -> None:
        docs = validator.validate_write_surface(
            "not-needed",
            ["product-docs-sync-result.json", "docs/product/.product-docs-sync-ledger.json"],
        )

        self.assertEqual(docs, [])

    def test_write_surface_allows_not_needed_without_docs_change(self) -> None:
        docs = validator.validate_write_surface(
            "not-needed",
            ["product-docs-sync-result.json", "product-docs-sync-context.md"],
        )

        self.assertEqual(docs, [])

    def test_write_surface_rejects_non_markdown_product_paths(self) -> None:
        with self.assertRaises(SystemExit):
            validator.validate_write_surface(
                "not-needed",
                ["product-docs-sync-result.json", "docs/product/raw/flow.json"],
            )

    def test_write_surface_rejects_non_docs_product_paths(self) -> None:
        with self.assertRaises(SystemExit):
            validator.validate_write_surface(
                "required",
                ["docs/product/raw/flow.md", ".github/workflows/product-docs-sync.yml"],
            )

    def test_pr_body_includes_decision_source_pr_and_processed_entries(self) -> None:
        body = body_writer.build_body(
            pr_number="87",
            pr_url="https://example.test/pull/87",
            result={
                "docs_update": "uncertain",
                "reason": "Needs product confirmation.",
                "affected_docs": ["docs/product/raw/flow.md"],
                "source_context": ["Issue #87", "PR #87"],
                "proposed_patch": "Draft docs for review.",
            },
            ledger={
                "version": 1,
                "entries": [
                    {
                        "pr": 86,
                        "title": "Add first flow",
                        "url": "https://example.test/pull/86",
                        "merged_at": "2026-05-25T01:00:00Z",
                        "docs_update": "required",
                        "reason": "First flow changed.",
                        "affected_docs": ["docs/product/raw/first.md"],
                        "proposed_patch": "Document first flow.",
                    },
                    {
                        "pr": 87,
                        "title": "Add second flow",
                        "url": "https://example.test/pull/87",
                        "merged_at": "2026-05-25T02:00:00Z",
                        "docs_update": "uncertain",
                        "reason": "Needs product confirmation.",
                        "affected_docs": ["docs/product/raw/flow.md"],
                        "proposed_patch": "Draft docs for review.",
                    },
                ],
            },
        )

        self.assertIn("docs update: `uncertain`", body)
        self.assertIn("source PR: #87", body)
        self.assertIn("source URL: https://example.test/pull/87", body)
        self.assertIn("docs/product/raw/flow.md", body)
        self.assertIn("Processed decisions in this PR:", body)
        self.assertIn("PR #86: Add first flow", body)
        self.assertIn("Document first flow.", body)

    def test_pr_body_truncates_large_processed_decision_history(self) -> None:
        entries = []
        for number in range(1, 35):
            entries.append(
                {
                    "pr": number,
                    "title": f"PR {number}",
                    "url": f"https://example.test/pull/{number}",
                    "merged_at": f"2026-05-25T01:{number:02d}:00Z",
                    "docs_update": "required",
                    "reason": "Changed product behavior. " * 400,
                    "affected_docs": [f"docs/product/raw/{number}.md"],
                    "proposed_patch": "Document the product behavior in detail. " * 400,
                }
            )

        body = body_writer.build_body(
            pr_number="99",
            pr_url="https://example.test/pull/99",
            result={
                "docs_update": "required",
                "reason": "Product behavior changed.",
                "affected_docs": ["docs/product/raw/flow.md"],
                "source_context": ["PR #99"],
                "proposed_patch": "Document the flow.",
            },
            ledger={"version": 1, "entries": entries},
        )

        self.assertLessEqual(len(body), body_writer.MAX_GITHUB_MARKDOWN_CHARS)
        self.assertIn("Omitted 14 older processed decisions", body)
        self.assertNotIn("PR #1: PR 1", body)
        self.assertIn("PR #34: PR 34", body)
        self.assertIn("Truncated change summary", body)

    def test_pr_comment_truncates_large_patch_summary(self) -> None:
        comment = body_writer.build_comment(
            pr_number="87",
            pr_url="https://example.test/pull/87",
            result={
                "docs_update": "required",
                "reason": "Docs changed.",
                "affected_docs": ["docs/product/raw/flow.md"],
                "source_context": ["PR #87"],
                "proposed_patch": "Long patch summary. " * 1000,
            },
        )

        self.assertLessEqual(len(comment), body_writer.MAX_GITHUB_MARKDOWN_CHARS)
        self.assertIn("Truncated patch summary", comment)

    def test_pr_comment_includes_current_run_decision(self) -> None:
        comment = body_writer.build_comment(
            pr_number="87",
            pr_url="https://example.test/pull/87",
            result={
                "docs_update": "uncertain",
                "reason": "Needs product confirmation.",
                "affected_docs": ["docs/product/raw/flow.md"],
                "source_context": ["Issue #87", "PR #87"],
                "proposed_patch": "Draft docs for review.",
            },
        )

        self.assertIn("Product Docs Sync processed a source PR.", comment)
        self.assertIn("source PR: #87", comment)
        self.assertIn("docs update: `uncertain`", comment)
        self.assertIn("reason: Needs product confirmation.", comment)
        self.assertIn("source URL: https://example.test/pull/87", comment)
        self.assertIn("`docs/product/raw/flow.md`", comment)
        self.assertIn("Draft docs for review.", comment)
        self.assertIn("needs maintainer confirmation", comment)
        self.assertNotIn("Processed decisions in this PR:", comment)

    def test_pr_comment_uses_empty_states_for_missing_docs_and_patch(self) -> None:
        comment = body_writer.build_comment(
            pr_number="88",
            pr_url="https://example.test/pull/88",
            result={
                "docs_update": "required",
                "reason": "Docs changed.",
                "affected_docs": [],
                "source_context": [],
                "proposed_patch": "",
            },
        )

        self.assertIn("Affected docs:\n- none", comment)
        self.assertIn("Patch summary:\nNone.", comment)

    def test_pr_body_writer_cli_can_write_comment_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            result_path = root / "result.json"
            ledger_path = root / "ledger.json"
            body_path = root / "body.md"
            comment_path = root / "comment.md"
            result_path.write_text(
                json.dumps(
                    {
                        "docs_update": "required",
                        "reason": "Product flow changed.",
                        "affected_docs": ["docs/product/raw/flow.md"],
                        "source_context": ["PR #87"],
                        "proposed_patch": "Document the flow.",
                    }
                ),
                encoding="utf-8",
            )
            ledger_path.write_text(json.dumps({"version": 1, "entries": []}), encoding="utf-8")

            with patch.dict(
                body_writer.os.environ,
                {
                    "SOURCE_PR_NUMBER": "87",
                    "SOURCE_PR_URL": "https://example.test/pull/87",
                },
                clear=False,
            ):
                with patch(
                    "sys.argv",
                    [
                        "write_product_docs_sync_pr_body.py",
                        "--result",
                        str(result_path),
                        "--ledger",
                        str(ledger_path),
                        "--output",
                        str(body_path),
                        "--comment-output",
                        str(comment_path),
                    ],
                ):
                    self.assertEqual(body_writer.main(), 0)

            self.assertIn("Processed decisions in this PR:", body_path.read_text(encoding="utf-8"))
            self.assertIn("Product Docs Sync processed a source PR.", comment_path.read_text(encoding="utf-8"))

    def test_main_writes_decision_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result_path = Path(temp_dir) / "result.json"
            github_output = Path(temp_dir) / "github-output.txt"
            result_path.write_text(
                json.dumps(
                    {
                        "docs_update": "not-needed",
                        "reason": "No product behavior changed.",
                        "affected_docs": [],
                        "source_context": ["PR #1"],
                        "proposed_patch": "No patch.",
                    }
                ),
                encoding="utf-8",
            )

            with patch.object(validator, "changed_paths", return_value=["product-docs-sync-result.json"]):
                with patch(
                    "sys.argv",
                    [
                        "validate_product_docs_sync_result.py",
                        "--result",
                        str(result_path),
                        "--github-output",
                        str(github_output),
                    ],
                ):
                    self.assertEqual(validator.main(), 0)

            output = github_output.read_text(encoding="utf-8")
            self.assertIn("docs_update=not-needed", output)
            self.assertIn("should_create_pr=false", output)


class ProductDocsSyncWorkflowTest(unittest.TestCase):
    def test_workflow_runs_on_schedule_and_manual_dispatch(self) -> None:
        data = workflow()
        triggers = data[True]

        self.assertIn("workflow_dispatch", triggers)
        self.assertIn("schedule", triggers)
        self.assertIn({"cron": "45 * * * *"}, triggers["schedule"])
        self.assertNotIn("pull_request", triggers)
        self.assertEqual(triggers["workflow_dispatch"]["inputs"]["pr_number"]["required"], False)
        self.assertEqual(data["permissions"]["contents"], "write")
        self.assertEqual(data["permissions"]["pull-requests"], "write")

    def test_workflow_prompt_restricts_write_surface(self) -> None:
        data = workflow()
        steps = data["jobs"]["sync"]["steps"]
        codex_step = next(step for step in steps if step.get("name") == "Run product docs sync")
        prompt = codex_step["with"]["prompt"]

        self.assertIn(".github/skills/product-docs-sync/SKILL.md", prompt)
        self.assertIn("product-docs-sync-result.json", prompt)
        self.assertIn("modify only files under docs/product/", prompt)
        self.assertIn("If docs_update is not-needed, do not modify docs/product/.", prompt)

    def test_workflow_validates_decision_before_creating_pr(self) -> None:
        data = workflow()
        steps = data["jobs"]["sync"]["steps"]
        names = [step.get("name") or step.get("uses") for step in steps]

        self.assertLess(names.index("Initialize product docs sync branch"), names.index("Prepare product docs sync context"))
        self.assertLess(names.index("Validate product docs sync context integrity"), names.index("Validate product docs sync result"))
        self.assertLess(names.index("Validate product docs sync result"), names.index("Update product docs sync ledger"))
        self.assertLess(names.index("Update product docs sync ledger"), names.index("Create or update product docs sync pull request"))

        init_step = next(step for step in steps if step.get("name") == "Initialize product docs sync branch")
        validate_step = next(step for step in steps if step.get("name") == "Validate product docs sync result")
        ledger_step = next(step for step in steps if step.get("name") == "Update product docs sync ledger")
        create_step = next(step for step in steps if step.get("name") == "Create or update product docs sync pull request")
        self.assertIn('branch="docs/product-docs-sync"', init_step["run"])
        self.assertIn('git rebase "$base"', init_step["run"])
        self.assertIn("validate_product_docs_sync_result.py", validate_step["run"])
        self.assertIn("update_product_docs_sync_ledger.py", ledger_step["run"])
        self.assertIn("steps.changes.outputs.changed == 'true'", create_step["if"])
        self.assertIn('branch="$SYNC_BRANCH"', create_step["run"])
        self.assertIn('title="Update product docs"', create_step["run"])
        self.assertIn("--state open", create_step["run"])
        self.assertIn('if [ -n "$existing_pr" ]; then', create_step["run"])
        self.assertIn("--draft", create_step["run"])
        self.assertIn('comment_file="$(mktemp)"', create_step["run"])
        self.assertIn('--comment-output "$comment_file"', create_step["run"])
        self.assertIn('target_pr="$existing_pr"', create_step["run"])
        self.assertIn('gh pr view "$branch"', create_step["run"])
        self.assertIn('gh pr comment "$target_pr"', create_step["run"])


if __name__ == "__main__":
    unittest.main()
