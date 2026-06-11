from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from script_imports import ROOT, import_script


validator = import_script(
    ".github/scripts/validate_product_wiki_compile.py",
    "validate_product_wiki_compile",
)
body_writer = import_script(
    ".github/scripts/write_product_wiki_compile_pr_body.py",
    "write_product_wiki_compile_pr_body",
)


def workflow() -> dict:
    return yaml.safe_load((ROOT / ".github/workflows/product-wiki-compile.yml").read_text(encoding="utf-8"))


class ProductWikiCompileScriptTest(unittest.TestCase):
    def test_write_surface_allows_wiki_markdown_and_handoff_file(self) -> None:
        paths = validator.validate_write_surface(
            [
                "product-wiki-raw.sha256",
                "docs/product/wiki/AGENTS.md",
                "docs/product/wiki/index.md",
                "docs/product/wiki/summaries/spec-workflow.md",
                "docs/product/wiki/concepts/automated-spec-workflow.md",
                "docs/product/wiki/schema/README.md",
                "docs/product/wiki/log.md",
            ]
        )

        self.assertIn("docs/product/wiki/index.md", paths)
        self.assertNotIn("product-wiki-raw.sha256", paths)

    def test_write_surface_rejects_raw_docs_changes(self) -> None:
        with self.assertRaises(SystemExit):
            validator.validate_write_surface(["docs/product/raw/spec-workflow.md"])

    def test_write_surface_rejects_workflow_skill_specs_and_code_changes(self) -> None:
        invalid_paths = [
            ".github/workflows/product-wiki-compile.yml",
            ".github/skills/product-wiki/SKILL.md",
            "specs/issue-1/product.md",
            "src/app.py",
        ]

        for path in invalid_paths:
            with self.subTest(path=path):
                with self.assertRaises(SystemExit):
                    validator.validate_write_surface([path])

    def test_write_surface_rejects_non_markdown_wiki_files(self) -> None:
        with self.assertRaises(SystemExit):
            validator.validate_write_surface(["docs/product/wiki/index.json"])

    def test_required_files_are_enforced_when_wiki_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "docs/product/wiki").mkdir(parents=True)
            (root / "docs/product/wiki/index.md").write_text("# Index\n", encoding="utf-8")

            with self.assertRaises(SystemExit):
                validator.validate_required_files(root, ["docs/product/wiki/index.md"])

    def test_required_files_are_skipped_without_wiki_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            validator.validate_required_files(Path(temp_dir), [])

    def test_required_files_are_enforced_when_raw_sources_exist(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            raw = root / "docs/product/raw/spec-workflow.md"
            raw.parent.mkdir(parents=True)
            raw.write_text("# Spec workflow\n", encoding="utf-8")

            with self.assertRaises(SystemExit):
                validator.validate_required_files(root, [])

    def test_frontmatter_accepts_summary_and_concept_pages(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            summary = root / "docs/product/wiki/summaries/spec-workflow.md"
            concept = root / "docs/product/wiki/concepts/spec-workflow.md"
            summary.parent.mkdir(parents=True)
            concept.parent.mkdir(parents=True)
            summary.write_text(
                "---\n"
                "type: summary\n"
                "title: Spec workflow source\n"
                "status: current\n"
                "confidence: high\n"
                "source_status: verified\n"
                "owner: product-docs\n"
                "last_reviewed: 2026-05-29\n"
                "review_due: 2026-08-27\n"
                "sources:\n"
                "  - docs/product/raw/spec-workflow.md\n"
                "---\n"
                "# Spec workflow source\n",
                encoding="utf-8",
            )
            concept.write_text(
                "---\n"
                "type: concept\n"
                "title: 自动 spec workflow\n"
                "status: current\n"
                "confidence: high\n"
                "source_status: verified\n"
                "owner: product-docs\n"
                "last_reviewed: 2026-05-29\n"
                "review_due: 2026-08-27\n"
                "sources:\n"
                "  - docs/product/raw/spec-workflow.md\n"
                "---\n"
                "# 自动 spec workflow\n",
                encoding="utf-8",
            )

            validator.validate_frontmatter(root)

    def test_frontmatter_rejects_missing_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            summary = root / "docs/product/wiki/summaries/spec-workflow.md"
            summary.parent.mkdir(parents=True)
            summary.write_text(
                "---\n"
                "type: summary\n"
                "title: Spec workflow source\n"
                "status: current\n"
                "confidence: high\n"
                "source_status: verified\n"
                "owner: product-docs\n"
                "last_reviewed: 2026-05-29\n"
                "review_due: 2026-08-27\n"
                "sources:\n"
                "---\n"
                "# Spec workflow source\n",
                encoding="utf-8",
            )

            with self.assertRaises(SystemExit):
                validator.validate_frontmatter(root)

    def test_frontmatter_rejects_invalid_review_date_value(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            summary = root / "docs/product/wiki/summaries/spec-workflow.md"
            summary.parent.mkdir(parents=True)
            summary.write_text(
                "---\n"
                "type: summary\n"
                "title: Spec workflow source\n"
                "status: current\n"
                "confidence: high\n"
                "source_status: verified\n"
                "owner: product-docs\n"
                "last_reviewed: 2026-02-31\n"
                "review_due: 2026-08-27\n"
                "sources:\n"
                "  - docs/product/raw/spec-workflow.md\n"
                "---\n"
                "# Spec workflow source\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(SystemExit, "last_reviewed must be a valid date"):
                validator.validate_frontmatter(root)

    def test_frontmatter_rejects_review_due_before_last_reviewed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            summary = root / "docs/product/wiki/summaries/spec-workflow.md"
            summary.parent.mkdir(parents=True)
            summary.write_text(
                "---\n"
                "type: summary\n"
                "title: Spec workflow source\n"
                "status: current\n"
                "confidence: high\n"
                "source_status: verified\n"
                "owner: product-docs\n"
                "last_reviewed: 2026-05-29\n"
                "review_due: 2026-05-28\n"
                "sources:\n"
                "  - docs/product/raw/spec-workflow.md\n"
                "---\n"
                "# Spec workflow source\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(SystemExit, "review_due must not be before last_reviewed"):
                validator.validate_frontmatter(root)

    def write_minimal_linked_wiki(self, root: Path) -> None:
        files = {
            "docs/product/wiki/AGENTS.md": "# Agents\n",
            "docs/product/wiki/schema/README.md": "# Schema\n",
            "docs/product/wiki/schema/page-types.md": "# Page types\n",
            "docs/product/wiki/schema/linking.md": "# Linking\n",
            "docs/product/wiki/schema/query.md": "# Query\n",
            "docs/product/wiki/schema/staging.md": "# Staging\n",
            "docs/product/wiki/log.md": "# Log\n",
            "docs/product/wiki/summaries/spec-workflow.md": (
                "---\n"
                "type: summary\n"
                "title: Spec workflow source\n"
                "status: current\n"
                "confidence: high\n"
                "source_status: verified\n"
                "owner: product-docs\n"
                "last_reviewed: 2026-05-29\n"
                "review_due: 2026-08-27\n"
                "sources:\n"
                "  - docs/product/raw/spec-workflow.md\n"
                "---\n"
                "# Spec workflow source\n"
                "- Concept: [自动 spec workflow](../concepts/spec-workflow.md)\n"
            ),
            "docs/product/wiki/concepts/spec-workflow.md": (
                "---\n"
                "type: concept\n"
                "title: 自动 spec workflow\n"
                "status: current\n"
                "confidence: high\n"
                "source_status: verified\n"
                "owner: product-docs\n"
                "last_reviewed: 2026-05-29\n"
                "review_due: 2026-08-27\n"
                "sources:\n"
                "  - docs/product/raw/spec-workflow.md\n"
                "---\n"
                "# 自动 spec workflow\n"
                "- Source: [Spec workflow source](../summaries/spec-workflow.md)\n"
            ),
        }
        index_links = [
            "[AGENTS](AGENTS.md)",
            "[Log](log.md)",
            "[Schema](schema/README.md)",
            "[Page types](schema/page-types.md)",
            "[Linking](schema/linking.md)",
            "[Query](schema/query.md)",
            "[Staging](schema/staging.md)",
            "[Spec workflow source](summaries/spec-workflow.md)",
            "[自动 spec workflow](concepts/spec-workflow.md)",
        ]
        files["docs/product/wiki/index.md"] = "# Index\n\n" + "\n".join(f"- {link}" for link in index_links) + "\n"
        for path, content in files.items():
            file_path = root / path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")

    def test_link_contract_accepts_index_summary_and_concept_links(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_minimal_linked_wiki(root)

            validator.validate_link_contract(root)

    def test_link_contract_rejects_index_missing_concept_link(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_minimal_linked_wiki(root)
            (root / "docs/product/wiki/index.md").write_text(
                "# Index\n\n"
                "- [AGENTS](AGENTS.md)\n"
                "- [Log](log.md)\n"
                "- [Schema](schema/README.md)\n"
                "- [Page types](schema/page-types.md)\n"
                "- [Linking](schema/linking.md)\n"
                "- [Query](schema/query.md)\n"
                "- [Staging](schema/staging.md)\n"
                "- [Spec workflow source](summaries/spec-workflow.md)\n",
                encoding="utf-8",
            )

            with self.assertRaises(SystemExit):
                validator.validate_link_contract(root)

    def test_link_contract_requires_summary_and_concept_when_raw_sources_exist(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            raw = root / "docs/product/raw/spec-workflow.md"
            raw.parent.mkdir(parents=True)
            raw.write_text("# Spec workflow\n", encoding="utf-8")
            wiki_files = {
                "docs/product/wiki/AGENTS.md": "# Agents\n",
                "docs/product/wiki/log.md": "# Log\n",
                "docs/product/wiki/schema/README.md": "# Schema\n",
                "docs/product/wiki/schema/page-types.md": "# Page types\n",
                "docs/product/wiki/schema/linking.md": "# Linking\n",
                "docs/product/wiki/schema/query.md": "# Query\n",
                "docs/product/wiki/schema/staging.md": "# Staging\n",
                "docs/product/wiki/index.md": (
                    "# Index\n\n"
                    "- [AGENTS](AGENTS.md)\n"
                    "- [Log](log.md)\n"
                    "- [Schema](schema/README.md)\n"
                    "- [Page types](schema/page-types.md)\n"
                    "- [Linking](schema/linking.md)\n"
                    "- [Query](schema/query.md)\n"
                    "- [Staging](schema/staging.md)\n"
                ),
            }
            for path, content in wiki_files.items():
                file_path = root / path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content, encoding="utf-8")

            with self.assertRaises(SystemExit):
                validator.validate_link_contract(root)

    def test_link_contract_rejects_disconnected_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_minimal_linked_wiki(root)
            (root / "docs/product/wiki/summaries/spec-workflow.md").write_text(
                "---\n"
                "type: summary\n"
                "title: Spec workflow source\n"
                "status: current\n"
                "confidence: high\n"
                "source_status: verified\n"
                "owner: product-docs\n"
                "last_reviewed: 2026-05-29\n"
                "review_due: 2026-08-27\n"
                "sources:\n"
                "  - docs/product/raw/spec-workflow.md\n"
                "---\n"
                "# Spec workflow source\n",
                encoding="utf-8",
            )

            with self.assertRaises(SystemExit):
                validator.validate_link_contract(root)

    def test_frontmatter_rejects_missing_status_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            summary = root / "docs/product/wiki/summaries/spec-workflow.md"
            summary.parent.mkdir(parents=True)
            summary.write_text(
                "---\n"
                "type: summary\n"
                "title: Spec workflow source\n"
                "sources:\n"
                "  - docs/product/raw/spec-workflow.md\n"
                "---\n"
                "# Spec workflow source\n",
                encoding="utf-8",
            )

            with self.assertRaises(SystemExit):
                validator.validate_frontmatter(root)

    def test_health_contract_rejects_duplicate_titles(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_minimal_linked_wiki(root)
            duplicate = root / "docs/product/wiki/concepts/duplicate.md"
            duplicate.write_text(
                "---\n"
                "type: concept\n"
                "title: 自动 spec workflow\n"
                "status: current\n"
                "confidence: high\n"
                "source_status: verified\n"
                "owner: product-docs\n"
                "last_reviewed: 2026-05-29\n"
                "review_due: 2026-08-27\n"
                "sources:\n"
                "  - docs/product/raw/spec-workflow.md\n"
                "---\n"
                "# 自动 spec workflow copy\n",
                encoding="utf-8",
            )

            with self.assertRaises(SystemExit):
                validator.validate_health_contract(root)

    def test_health_contract_rejects_unsectioned_review_marker(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_minimal_linked_wiki(root)
            concept = root / "docs/product/wiki/concepts/spec-workflow.md"
            concept.write_text(concept.read_text(encoding="utf-8") + "\n- 待确认：needs source.\n", encoding="utf-8")

            with self.assertRaises(SystemExit):
                validator.validate_health_contract(root)

    def test_main_writes_changed_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            self.write_minimal_linked_wiki(root)
            github_output = root / "github-output.txt"

            with patch.object(validator, "changed_paths", return_value=["docs/product/wiki/index.md"]):
                with patch(
                    "sys.argv",
                    [
                        "validate_product_wiki_compile.py",
                        "--root",
                        str(root),
                        "--github-output",
                        str(github_output),
                    ],
                ):
                    self.assertEqual(validator.main(), 0)

            output = github_output.read_text(encoding="utf-8")
            self.assertIn("changed=true", output)
            self.assertIn("changed_files=docs/product/wiki/index.md", output)

    def test_pr_body_summarizes_wiki_sections(self) -> None:
        body = body_writer.build_body(
            [
                "docs/product/wiki/AGENTS.md",
                "docs/product/wiki/index.md",
                "docs/product/wiki/summaries/spec-workflow.md",
                "docs/product/wiki/concepts/spec-workflow.md",
                "docs/product/wiki/schema/README.md",
                "docs/product/wiki/log.md",
            ]
        )

        self.assertIn("source root: `docs/product/raw/`", body)
        self.assertIn("target root: `docs/product/wiki/`", body)
        self.assertIn("AGENTS guide updated: `yes`", body)
        self.assertIn("summaries updated: `yes`", body)
        self.assertIn("concepts updated: `yes`", body)
        self.assertIn("schema updated: `yes`", body)
        self.assertIn("compile log updated: `yes`", body)
        self.assertIn("待确认", body)


class ProductWikiCompileWorkflowTest(unittest.TestCase):
    def test_workflow_runs_on_schedule_and_manual_dispatch_only(self) -> None:
        data = workflow()
        triggers = data[True]

        self.assertIn("workflow_dispatch", triggers)
        self.assertIn("schedule", triggers)
        self.assertEqual(triggers["schedule"], [{"cron": "10 3 * * *"}])
        self.assertNotIn("push", triggers)
        self.assertNotIn("pull_request", triggers)
        self.assertEqual(data["permissions"]["contents"], "write")
        self.assertEqual(data["permissions"]["pull-requests"], "write")

    def test_workflow_uses_fixed_branch_and_validates_before_pr(self) -> None:
        data = workflow()
        steps = data["jobs"]["compile"]["steps"]
        names = [step.get("name") or step.get("uses") for step in steps]

        self.assertLess(names.index("Initialize product wiki branch"), names.index("Compile product wiki"))
        self.assertLess(names.index("Compile product wiki"), names.index("Validate raw product docs integrity"))
        self.assertLess(names.index("Validate raw product docs integrity"), names.index("Validate product wiki compile"))
        self.assertLess(names.index("Validate product wiki compile"), names.index("Create or update product wiki pull request"))

        init_step = next(step for step in steps if step.get("name") == "Initialize product wiki branch")
        validate_step = next(step for step in steps if step.get("name") == "Validate product wiki compile")
        create_step = next(step for step in steps if step.get("name") == "Create or update product wiki pull request")
        self.assertIn('branch="docs/product-wiki-compile"', init_step["run"])
        self.assertIn('git rebase "$base"', init_step["run"])
        self.assertIn("validate_product_wiki_compile.py", validate_step["run"])
        self.assertIn("steps.wiki_status.outputs.changed == 'true'", create_step["if"])
        self.assertIn('branch="$WIKI_BRANCH"', create_step["run"])
        self.assertLess(
            create_step["run"].index("write_product_wiki_compile_pr_body.py"),
            create_step["run"].index("git commit -m"),
        )
        self.assertIn("--state open", create_step["run"])

    def test_workflow_prompt_defines_llm_wiki_contract(self) -> None:
        data = workflow()
        steps = data["jobs"]["compile"]["steps"]
        codex_step = next(step for step in steps if step.get("name") == "Compile product wiki")
        prompt = codex_step["with"]["prompt"]

        self.assertIn(".github/skills/product-wiki/SKILL.md", prompt)
        self.assertIn("docs/product/wiki/AGENTS.md", prompt)
        self.assertIn("docs/product/wiki/summaries/*.md", prompt)
        self.assertIn("docs/product/wiki/concepts/*.md", prompt)
        self.assertIn("docs/product/wiki/schema/page-types.md", prompt)
        self.assertIn("Modify only Markdown files under docs/product/wiki/.", prompt)
        self.assertIn("Do not modify docs/product/raw", prompt)


if __name__ == "__main__":
    unittest.main()
