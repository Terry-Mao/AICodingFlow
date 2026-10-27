from __future__ import annotations

import unittest

import yaml

from script_imports import ROOT


def workflow(path: str) -> dict:
    return yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))


def steps(workflow_data: dict, job: str) -> list[dict]:
    return workflow_data["jobs"][job]["steps"]


class CiWorkflowTest(unittest.TestCase):
    def test_ci_checks_pr_body_and_runs_tests_without_dispatching_review(self) -> None:
        data = workflow(".github/workflows/ci.yml")
        triggers = data[True]

        self.assertEqual(triggers["pull_request"]["types"], ["opened", "reopened", "synchronize", "ready_for_review", "edited"])
        self.assertEqual(triggers["merge_group"]["types"], ["checks_requested"])
        self.assertNotIn("actions", data["permissions"])
        self.assertEqual(data["permissions"]["contents"], "read")
        self.assertNotIn("pull-requests", data["permissions"])
        self.assertNotIn("statuses", data["permissions"])
        self.assertEqual(set(data["jobs"]), {"pr-body", "test"})

        self.assertEqual(data["jobs"]["test"]["if"], "github.event_name == 'merge_group' || github.event.pull_request.draft == false")

        body_steps = steps(data, "pr-body")
        self.assertTrue(any("validate_pr_body" in step.get("run", "") for step in body_steps))

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

    def test_ci_uses_node24_action_runtime(self) -> None:
        data = workflow(".github/workflows/ci.yml")
        self.assertEqual(data["jobs"]["test"]["env"]["FORCE_JAVASCRIPT_ACTIONS_TO_NODE24"], "true")

        used_actions = [step.get("uses", "") for step in steps(data, "test") if "uses" in step]
        self.assertNotIn("actions/checkout@v4", used_actions)
        for action in used_actions:
            if action.startswith("actions/checkout@"):
                self.assertEqual(action, "actions/checkout@v6")


if __name__ == "__main__":
    unittest.main()
