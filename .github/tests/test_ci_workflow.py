from __future__ import annotations

import unittest

import yaml

from script_imports import ROOT


def workflow(path: str) -> dict:
    return yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))


def steps(workflow_data: dict, job: str) -> list[dict]:
    return workflow_data["jobs"][job]["steps"]


class CiWorkflowTest(unittest.TestCase):
    def test_ci_queues_review_before_tests_and_dispatches_after_success(self) -> None:
        data = workflow(".github/workflows/ci.yml")
        triggers = data[True]

        self.assertEqual(triggers["pull_request"]["types"], ["opened", "reopened", "synchronize", "ready_for_review"])
        self.assertEqual(data["permissions"]["actions"], "write")
        self.assertEqual(data["permissions"]["contents"], "read")
        self.assertEqual(data["permissions"]["pull-requests"], "read")
        self.assertEqual(data["permissions"]["statuses"], "write")

        queue_job = data["jobs"]["queue-ai-review"]
        self.assertIn("github.event.pull_request.draft == false", queue_job["if"])
        queue_step = next(step for step in steps(data, "queue-ai-review") if step.get("name") == "Mark AI PR Review waiting for CI")
        self.assertEqual(queue_step["if"], "github.event.pull_request.head.repo.full_name == github.repository")
        self.assertEqual(queue_step["env"]["GH_TOKEN"], "${{ github.token }}")
        self.assertEqual(queue_step["env"]["HEAD_SHA"], "${{ github.event.pull_request.head.sha }}")
        self.assertIn("repos/${{ github.repository }}/statuses/$HEAD_SHA", queue_step["run"])
        self.assertIn('state="pending"', queue_step["run"])
        self.assertIn('context="AI PR Review"', queue_step["run"])
        self.assertIn('description="AI PR review is waiting for CI"', queue_step["run"])

        fork_step = next(step for step in steps(data, "queue-ai-review") if step.get("name") == "Skip AI PR Review status for fork PR")
        self.assertEqual(fork_step["if"], "github.event.pull_request.head.repo.full_name != github.repository")

        self.assertEqual(data["jobs"]["test"]["needs"], "queue-ai-review")
        self.assertEqual(data["jobs"]["ai-review"]["needs"], ["queue-ai-review", "test"])
        self.assertIn("github.event.pull_request.draft == false", data["jobs"]["test"]["if"])
        self.assertIn("needs.queue-ai-review.result == 'success'", data["jobs"]["test"]["if"])
        self.assertIn("needs.queue-ai-review.result == 'success'", data["jobs"]["ai-review"]["if"])
        self.assertIn("needs.test.result == 'success'", data["jobs"]["ai-review"]["if"])
        self.assertIn("github.event.pull_request.head.repo.full_name == github.repository", data["jobs"]["ai-review"]["if"])

        test_steps = steps(data, "test")
        project_tests = next(step for step in test_steps if step.get("name") == "Run repository unit tests")
        delivery_tests = next(step for step in test_steps if step.get("name") == "Run delivered unit tests")
        self.assertIn("python3 -m unittest discover -s .github/tests", project_tests["run"])
        self.assertIn("python3 -m unittest discover -s .github/aicodingflow-tests", delivery_tests["run"])

        dispatch_step = next(step for step in steps(data, "ai-review") if step.get("name") == "Dispatch AI PR Review")
        self.assertEqual(dispatch_step["env"]["GH_TOKEN"], "${{ github.token }}")
        self.assertEqual(dispatch_step["env"]["PR_NUMBER"], "${{ github.event.pull_request.number }}")
        self.assertIn("gh workflow run review-pr.yml --repo \"${{ github.repository }}\" -f pr_number=\"$PR_NUMBER\"", dispatch_step["run"])

        finalize_job = data["jobs"]["finalize-skipped-ai-review"]
        self.assertEqual(finalize_job["needs"], ["queue-ai-review", "test"])
        self.assertIn("always()", finalize_job["if"])
        self.assertIn("needs.queue-ai-review.result == 'success'", finalize_job["if"])
        self.assertIn("needs.test.result != 'success'", finalize_job["if"])
        self.assertIn("github.event.pull_request.head.repo.full_name == github.repository", finalize_job["if"])
        finalize_step = next(step for step in steps(data, "finalize-skipped-ai-review") if step.get("name") == "Mark AI PR Review blocked by CI")
        self.assertIn('state="failure"', finalize_step["run"])
        self.assertIn('context="AI PR Review"', finalize_step["run"])
        self.assertIn('description="CI did not pass before AI PR review"', finalize_step["run"])

    def test_ci_uses_node24_action_runtime(self) -> None:
        data = workflow(".github/workflows/ci.yml")
        for job_name in ("queue-ai-review", "test", "ai-review", "finalize-skipped-ai-review"):
            self.assertEqual(data["jobs"][job_name]["env"]["FORCE_JAVASCRIPT_ACTIONS_TO_NODE24"], "true")

        used_actions = [step.get("uses", "") for step in steps(data, "test") if "uses" in step]
        self.assertNotIn("actions/checkout@v4", used_actions)
        for action in used_actions:
            if action.startswith("actions/checkout@"):
                self.assertEqual(action, "actions/checkout@v6")


if __name__ == "__main__":
    unittest.main()
