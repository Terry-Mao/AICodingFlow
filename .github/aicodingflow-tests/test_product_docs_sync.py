from __future__ import annotations

import json
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


def workflow() -> dict:
    return yaml.safe_load((ROOT / ".github/workflows/product-docs-sync.yml").read_text(encoding="utf-8"))


class ProductDocsSyncScriptTest(unittest.TestCase):
    def test_issue_numbers_are_deduplicated_from_closing_references(self) -> None:
        pr = {
            "closingIssuesReferences": [
                {"number": 87},
                {"number": "87"},
                {"number": 88},
                {"number": None},
            ]
        }

        self.assertEqual(prepare.issue_numbers(pr), [87, 88])

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

    def test_write_surface_allows_not_needed_without_docs_change(self) -> None:
        docs = validator.validate_write_surface(
            "not-needed",
            ["product-docs-sync-result.json", "product-docs-sync-context.md"],
        )

        self.assertEqual(docs, [])

    def test_write_surface_rejects_non_docs_product_paths(self) -> None:
        with self.assertRaises(SystemExit):
            validator.validate_write_surface(
                "required",
                ["docs/product/raw/flow.md", ".github/workflows/product-docs-sync.yml"],
            )

    def test_pr_body_includes_decision_and_source_pr(self) -> None:
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
        )

        self.assertIn("docs update: `uncertain`", body)
        self.assertIn("source PR: https://example.test/pull/87", body)
        self.assertIn("docs/product/raw/flow.md", body)

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
    def test_workflow_runs_on_merged_prs_and_manual_dispatch(self) -> None:
        data = workflow()
        triggers = data[True]

        self.assertIn("workflow_dispatch", triggers)
        self.assertEqual(triggers["pull_request"]["types"], ["closed"])
        self.assertIn("github.event.pull_request.merged == true", data["jobs"]["sync"]["if"])
        self.assertEqual(data["permissions"]["contents"], "write")
        self.assertEqual(data["permissions"]["pull-requests"], "write")

    def test_workflow_prompt_restricts_write_surface(self) -> None:
        data = workflow()
        steps = data["jobs"]["sync"]["steps"]
        codex_step = next(step for step in steps if step.get("name") == "Run product docs sync")
        prompt = codex_step["with"]["prompt"]

        self.assertIn(".agents/skills/product-docs-sync/SKILL.md", prompt)
        self.assertIn("product-docs-sync-result.json", prompt)
        self.assertIn("modify only files under docs/product/", prompt)
        self.assertIn("If docs_update is not-needed, do not modify docs/product/.", prompt)

    def test_workflow_validates_decision_before_creating_pr(self) -> None:
        data = workflow()
        steps = data["jobs"]["sync"]["steps"]
        names = [step.get("name") or step.get("uses") for step in steps]

        self.assertLess(names.index("Validate product docs sync context integrity"), names.index("Validate product docs sync result"))
        self.assertLess(names.index("Validate product docs sync result"), names.index("Create or update product docs sync pull request"))

        validate_step = next(step for step in steps if step.get("name") == "Validate product docs sync result")
        create_step = next(step for step in steps if step.get("name") == "Create or update product docs sync pull request")
        self.assertIn("validate_product_docs_sync_result.py", validate_step["run"])
        self.assertIn("steps.decision.outputs.should_create_pr == 'true'", create_step["if"])
        self.assertIn('branch="docs/product-docs-sync-pr-${SOURCE_PR_NUMBER}"', create_step["run"])
        self.assertIn("--draft", create_step["run"])


if __name__ == "__main__":
    unittest.main()
