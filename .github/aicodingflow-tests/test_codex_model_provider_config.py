from __future__ import annotations

import unittest

import yaml

from script_imports import ROOT


CODEX_WORKFLOWS = (
    ".github/workflows/create-implementation-from-issue.yml",
    ".github/workflows/create-spec-from-issue.yml",
    ".github/workflows/respond-to-pr-comment.yml",
    ".github/workflows/review-pr.yml",
    ".github/workflows/triage-issue.yml",
    ".github/workflows/update-dedupe.yml",
    ".github/workflows/update-pr-review.yml",
    ".github/workflows/update-triage.yml",
    ".github/workflows/nightly-codebase-review.yml",
)
PINNED_REVIEW_ACTION = "uses: openai/codex-action@52fe01ec70a42f454c9d2ebd47598f9fd6893d56"
PINNED_CLAUDE_ACTION = "anthropics/claude-code-action@c0949c50a78c1ec8ce2647db36629b870e715d0c"


class CodexModelProviderConfigTest(unittest.TestCase):
    def test_all_codex_workflows_use_shared_provider_configuration(self) -> None:
        for path in CODEX_WORKFLOWS:
            with self.subTest(path=path):
                contents = (ROOT / path).read_text(encoding="utf-8")
                if path.endswith("/review-pr.yml"):
                    self.assertEqual(contents.count(PINNED_REVIEW_ACTION), 1)
                else:
                    self.assertEqual(contents.count("uses: openai/codex-action@v1"), 1)
                self.assertEqual(contents.count("openai-api-key: ${{ secrets.CODEX_API_KEY }}"), 1)
                self.assertEqual(
                    contents.count("model: ${{ vars.CODEX_MODEL }}"),
                    1,
                )
                self.assertEqual(contents.count("CODEX_API_ENDPOINT: ${{ vars.CODEX_API_ENDPOINT }}"), 1)
                self.assertIn('endpoint="${CODEX_API_ENDPOINT%/}"', contents)
                self.assertIn("*/responses", contents)
                self.assertIn("$endpoint/responses", contents)
                self.assertIn("CODEX_API_ENDPOINT is not set", contents)
                self.assertIn(f"uses: {PINNED_CLAUDE_ACTION}", contents)
                self.assertIn("anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}", contents)
                self.assertIn("claude_args:", contents)
                self.assertIn("prompt: &agent_prompt |", contents)
                self.assertIn("prompt: *agent_prompt", contents)
                self.assertIn("vars.AI_PROVIDER == 'claude'", contents)
                self.assertIn("vars.AI_PROVIDER == '' || vars.AI_PROVIDER == 'codex'", contents)
                self.assertIn(".github/scripts/validate_ai_provider.py", contents)

    def test_nightly_review_normalizes_both_provider_outputs(self) -> None:
        contents = (ROOT / ".github/workflows/nightly-codebase-review.yml").read_text(encoding="utf-8")
        self.assertIn("steps.codex.outputs.final-message || steps.claude.outputs.structured_output", contents)
        self.assertIn("--json-schema", contents)
        self.assertIn("--allowedTools Read,Glob,Grep", contents)

    def test_both_actions_receive_the_same_prompt_and_exclusive_gates(self) -> None:
        for path in CODEX_WORKFLOWS:
            with self.subTest(path=path):
                workflow = yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))
                for job in workflow["jobs"].values():
                    steps = job.get("steps", [])
                    codex = next((step for step in steps if str(step.get("uses", "")).startswith("openai/codex-action@")), None)
                    if codex is None:
                        continue
                    claude = next(step for step in steps if step.get("uses") == PINNED_CLAUDE_ACTION)
                    self.assertEqual(codex["with"]["prompt"], claude["with"]["prompt"])
                    self.assertIn("AI_PROVIDER == 'codex'", codex["if"])
                    self.assertIn("AI_PROVIDER == 'claude'", claude["if"])

    def test_workflows_do_not_read_the_legacy_endpoint_environment_directly(self) -> None:
        for path in CODEX_WORKFLOWS:
            with self.subTest(path=path):
                contents = (ROOT / path).read_text(encoding="utf-8")
                self.assertNotIn("OPENAI_", contents)


if __name__ == "__main__":
    unittest.main()
