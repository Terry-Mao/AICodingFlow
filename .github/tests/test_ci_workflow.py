from __future__ import annotations

import unittest

import yaml

from script_imports import ROOT


def workflow(path: str) -> dict:
    return yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))


def steps(workflow_data: dict, job: str) -> list[dict]:
    return workflow_data["jobs"][job]["steps"]


class CiWorkflowTest(unittest.TestCase):
    def test_ci_dispatches_review_only_after_tests_pass(self) -> None:
        data = workflow(".github/workflows/ci.yml")
        triggers = data[True]

        self.assertEqual(triggers["pull_request"]["types"], ["opened", "reopened", "synchronize", "ready_for_review"])
        self.assertEqual(data["permissions"]["actions"], "write")
        self.assertEqual(data["permissions"]["contents"], "read")
        self.assertNotIn("pull-requests", data["permissions"])
        self.assertNotIn("statuses", data["permissions"])
        self.assertEqual(set(data["jobs"]), {"test", "ai-review"})

        self.assertEqual(data["jobs"]["test"]["if"], "github.event.pull_request.draft == false")
        self.assertEqual(data["jobs"]["ai-review"]["needs"], "test")
        self.assertIn("needs.test.result == 'success'", data["jobs"]["ai-review"]["if"])
        self.assertIn("github.event.pull_request.head.repo.full_name == github.repository", data["jobs"]["ai-review"]["if"])

        test_steps = steps(data, "test")
        dependencies = next(step for step in test_steps if step.get("name") == "Install Python test dependencies")
        self.assertIn('python3 -m venv "$RUNNER_TEMP/aicodingflow-venv"', dependencies["run"])
        self.assertIn('aicodingflow-venv/bin/python" -m pip install', dependencies["run"])
        self.assertIn('"PyYAML==6.0.3"', dependencies["run"])

        project_tests = next(step for step in test_steps if step.get("name") == "Run repository unit tests")
        delivery_tests = next(step for step in test_steps if step.get("name") == "Run delivered unit tests")
        self.assertIn("python3 -m unittest discover -s .github/tests", project_tests["run"])
        self.assertIn("python3 -m unittest discover -s .github/aicodingflow-tests", delivery_tests["run"])

        install_actionlint = next(step for step in test_steps if step.get("name") == "Install actionlint")
        self.assertEqual(install_actionlint["env"]["ACTIONLINT_VERSION"], "1.7.12")
        self.assertIn("sha256sum --check", install_actionlint["run"])

        lint_workflows = next(step for step in test_steps if step.get("name") == "Lint GitHub Actions workflows")
        self.assertIn("find .github/workflows", lint_workflows["run"])
        self.assertIn("-name '*.yml'", lint_workflows["run"])
        self.assertIn("-name '*.yaml'", lint_workflows["run"])
        self.assertIn('actionlint "${workflow_files[@]}"', lint_workflows["run"])

        dispatch_step = next(step for step in steps(data, "ai-review") if step.get("name") == "Dispatch AI PR Review")
        self.assertEqual(dispatch_step["env"]["GH_TOKEN"], "${{ github.token }}")
        self.assertEqual(dispatch_step["env"]["PR_NUMBER"], "${{ github.event.pull_request.number }}")
        self.assertIn("gh workflow run review-pr.yml --repo \"${{ github.repository }}\" -f pr_number=\"$PR_NUMBER\"", dispatch_step["run"])

    def test_ci_uses_node24_action_runtime(self) -> None:
        data = workflow(".github/workflows/ci.yml")
        for job_name in ("test", "ai-review"):
            self.assertEqual(data["jobs"][job_name]["env"]["FORCE_JAVASCRIPT_ACTIONS_TO_NODE24"], "true")

        used_actions = [step.get("uses", "") for step in steps(data, "test") if "uses" in step]
        self.assertNotIn("actions/checkout@v4", used_actions)
        for action in used_actions:
            if action.startswith("actions/checkout@"):
                self.assertEqual(action, "actions/checkout@v6")


if __name__ == "__main__":
    unittest.main()
