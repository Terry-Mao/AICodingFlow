from __future__ import annotations

import unittest

import yaml

from script_imports import ROOT


def workflow(path: str) -> dict:
    return yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))


def steps(workflow_data: dict, job: str) -> list[dict]:
    return workflow_data["jobs"][job]["steps"]


class ReviewWorkflowDispatchTest(unittest.TestCase):
    def test_workflows_use_node24_action_runtime(self) -> None:
        workflow_jobs = {
            ".github/workflows/create-implementation-from-issue.yml": "create-implementation",
            ".github/workflows/create-spec-from-issue.yml": "create-spec",
            ".github/workflows/review-pr.yml": "review",
            ".github/workflows/respond-to-pr-comment.yml": "respond",
            ".github/workflows/triage-issue.yml": "generate",
            ".github/workflows/update-dedupe.yml": "update",
            ".github/workflows/update-pr-review.yml": "update",
        }

        for path, job_name in workflow_jobs.items():
            with self.subTest(path=path):
                data = workflow(path)
                job = data["jobs"][job_name]
                self.assertEqual(job["env"]["FORCE_JAVASCRIPT_ACTIONS_TO_NODE24"], "true")
                used_actions = [step.get("uses", "") for step in steps(data, job_name) if "uses" in step]
                self.assertNotIn("actions/checkout@v4", used_actions)
                self.assertNotIn("actions/upload-artifact@v4", used_actions)

                for action in used_actions:
                    if action.startswith("actions/checkout@"):
                        self.assertEqual(action, "actions/checkout@v6")
                    if action.startswith("actions/upload-artifact@"):
                        self.assertEqual(action, "actions/upload-artifact@v7")

    def test_review_workflow_uses_manual_and_comment_triggers_only(self) -> None:
        data = workflow(".github/workflows/review-pr.yml")
        triggers = data[True]

        self.assertNotIn("pull_request", triggers)
        self.assertNotIn("pull_request_target", triggers)
        self.assertEqual(data["permissions"]["statuses"], "write")
        self.assertEqual(triggers["issue_comment"]["types"], ["created"])
        self.assertTrue(triggers["workflow_dispatch"]["inputs"]["pr_number"]["required"])
        job_gate = data["jobs"]["preflight"]["if"]
        self.assertIn("github.event_name == 'workflow_dispatch'", job_gate)
        self.assertNotIn("github.event_name == 'pull_request'", job_gate)
        self.assertNotIn("github.event.pull_request.head.repo.full_name == github.repository", job_gate)
        self.assertIn("github.event_name == 'issue_comment'", job_gate)
        self.assertIn("github.event.issue.pull_request != null", job_gate)
        self.assertIn("contains(github.event.comment.body, format('@{0}', vars.AGENT_LOGIN))", job_gate)
        self.assertIn("contains(github.event.comment.body, '/review')", job_gate)
        self.assertEqual(data["jobs"]["review"]["needs"], "preflight")
        self.assertEqual(data["jobs"]["review"]["if"], "needs.preflight.outputs.reviewable == 'true'")

    def test_review_workflow_resolves_pr_before_checkout_and_uses_normalized_event(self) -> None:
        data = workflow(".github/workflows/review-pr.yml")
        names = [step.get("name") or step.get("uses") for step in steps(data, "review")]

        self.assertLess(names.index("Checkout workflow scripts"), names.index("Resolve pull request"))
        self.assertLess(names.index("Resolve pull request"), names.index("Checkout PR head"))

        review_steps = steps(data, "review")
        checkout_pr_head = next(step for step in review_steps if step.get("name") == "Checkout PR head")
        self.assertEqual(checkout_pr_head["with"]["persist-credentials"], False)
        self.assertEqual(checkout_pr_head["with"]["repository"], "${{ steps.pr.outputs.head_repo }}")
        self.assertEqual(checkout_pr_head["with"]["ref"], "${{ steps.pr.outputs.head_sha }}")
        self.assertEqual(checkout_pr_head["with"]["path"], "pr-worktree")

        resolve_step = next(step for step in review_steps if step.get("name") == "Resolve pull request")
        self.assertIn(".github/scripts/resolve_pr_event.py", resolve_step["run"])
        self.assertIn("--output \"$RUNNER_TEMP/pr_event.json\"", resolve_step["run"])
        self.assertIn("--agent-login \"${{ vars.AGENT_LOGIN }}\"", resolve_step["run"])

        pending_status_step = next(step for step in review_steps if step.get("name") == "Mark PR review status pending")
        self.assertIn("github.event_name != 'pull_request'", pending_status_step["if"])
        self.assertIn("steps.pr.outputs.head_sha != ''", pending_status_step["if"])
        self.assertIn("steps.pr.outputs.head_repo == github.repository", pending_status_step["if"])
        self.assertEqual(pending_status_step["env"]["HEAD_SHA"], "${{ steps.pr.outputs.head_sha }}")
        self.assertIn("repos/${{ github.repository }}/statuses/$HEAD_SHA", pending_status_step["run"])
        self.assertIn('state="pending"', pending_status_step["run"])

        preflight_steps = steps(data, "preflight")
        preflight_resolve = next(step for step in preflight_steps if step.get("name") == "Resolve pull request")
        self.assertIn(".github/scripts/resolve_pr_event.py", preflight_resolve["run"])
        self.assertIn("--github-output \"$GITHUB_OUTPUT\"", preflight_resolve["run"])
        self.assertIn("--agent-login \"${{ vars.AGENT_LOGIN }}\"", preflight_resolve["run"])
        self.assertIn("reviewable", data["jobs"]["preflight"]["outputs"])
        self.assertIn("skip_reason", data["jobs"]["preflight"]["outputs"])

        description_step = next(step for step in review_steps if step.get("name") == "Snapshot PR description")
        spec_context_step = next(step for step in review_steps if step.get("name") == "Snapshot spec context")
        post_step = next(step for step in review_steps if step.get("name") == "Post PR review")
        self.assertEqual(description_step["env"]["PR_EVENT_PATH"], "${{ steps.pr.outputs.event_path }}")
        self.assertIn("--output pr-worktree/pr_description.txt", description_step["run"])
        self.assertEqual(spec_context_step["env"]["PR_EVENT_PATH"], "${{ steps.pr.outputs.event_path }}")
        self.assertIn("--changed-files-from-diff pr-worktree/pr_diff.txt", spec_context_step["run"])
        self.assertIn("--output pr-worktree/spec_context.md", spec_context_step["run"])
        self.assertEqual(post_step["env"]["PR_EVENT_PATH"], "${{ steps.pr.outputs.event_path }}")
        self.assertEqual(post_step["env"]["REVIEW_BOT_LOGIN"], "${{ vars.REVIEW_BOT_LOGIN }}")
        self.assertIn("--review pr-worktree/review.json", post_step["run"])
        self.assertIn("--diff pr-worktree/pr_diff.txt", post_step["run"])

        diff_step = next(step for step in review_steps if step.get("name") == "Snapshot PR diff")
        self.assertEqual(diff_step["working-directory"], "pr-worktree")
        self.assertEqual(diff_step["env"]["GITHUB_TOKEN"], "${{ github.token }}")
        self.assertIn("git_config=\"$(mktemp)\"", diff_step["run"])
        self.assertIn("trap 'rm -f \"$git_config\"' EXIT", diff_step["run"])
        self.assertIn("chmod 600 \"$git_config\"", diff_step["run"])
        self.assertIn("[http \"https://github.com/\"]", diff_step["run"])
        self.assertIn("extraheader = AUTHORIZATION: basic", diff_step["run"])
        self.assertIn("AUTHORIZATION: basic", diff_step["run"])
        self.assertIn("GIT_CONFIG_GLOBAL=\"$git_config\" GIT_TERMINAL_PROMPT=0", diff_step["run"])
        self.assertIn("fetch --no-tags --depth=1", diff_step["run"])
        self.assertIn("\"https://github.com/${GITHUB_REPOSITORY}.git\"", diff_step["run"])
        self.assertNotIn("git remote add base", diff_step["run"])
        self.assertNotIn("git -c \"http.https://github.com/.extraheader", diff_step["run"])
        self.assertNotIn("${auth_header}", diff_step["run"])
        self.assertNotIn("x-access-token:${GITHUB_TOKEN}@github.com", diff_step["run"])
        self.assertIn("../.github/scripts/build_pr_diff.py", diff_step["run"])
        self.assertIn("--output pr_diff.txt", diff_step["run"])

        select_step = next(step for step in review_steps if step.get("name") == "Select review skill")
        self.assertIn("--diff pr-worktree/pr_diff.txt", select_step["run"])

        prepare_step = next(step for step in review_steps if step.get("name") == "Prepare review workspace")
        self.assertIn("rm -rf pr-worktree/.agents/skills", prepare_step["run"])
        self.assertIn("cp -R .agents/skills pr-worktree/.agents/skills", prepare_step["run"])

        ai_step = next(step for step in review_steps if step.get("name") == "Run AI review")
        self.assertEqual(ai_step["with"]["allow-bot-users"], "github-actions[bot]")
        self.assertIn("First change directory to pr-worktree", ai_step["with"]["prompt"])
        self.assertIn("Write review.json in pr-worktree", ai_step["with"]["prompt"])
        self.assertIn("target pr-worktree/review.json explicitly", ai_step["with"]["prompt"])

        normalize_step = next(step for step in review_steps if step.get("name") == "Normalize review output path")
        self.assertIn("[ ! -f pr-worktree/review.json ] && [ -f review.json ]", normalize_step["run"])
        self.assertIn("mv review.json pr-worktree/review.json", normalize_step["run"])

        validate_step = next(step for step in review_steps if step.get("name") == "Validate review output")
        self.assertIn("pr-worktree/pr_diff.txt pr-worktree/review.json", validate_step["run"])

        complete_status_step = next(step for step in review_steps if step.get("name") == "Mark PR review status complete")
        self.assertIn("always()", complete_status_step["if"])
        self.assertIn("github.event_name != 'pull_request'", complete_status_step["if"])
        self.assertIn("steps.pr.outputs.head_sha != ''", complete_status_step["if"])
        self.assertIn("steps.pr.outputs.head_repo == github.repository", complete_status_step["if"])
        self.assertEqual(complete_status_step["env"]["STATE"], "${{ job.status == 'success' && 'success' || 'failure' }}")
        self.assertIn("repos/${{ github.repository }}/statuses/$HEAD_SHA", complete_status_step["run"])

    def test_triage_workflow_allows_regular_issue_authors_through_preflight(self) -> None:
        data = workflow(".github/workflows/triage-issue.yml")
        triggers = data[True]

        self.assertEqual(triggers["issues"]["types"], ["opened", "reopened"])
        self.assertEqual(triggers["issue_comment"]["types"], ["created"])

        job_gate = data["jobs"]["generate"]["if"]
        self.assertIn("github.event.issue.pull_request == null", job_gate)
        self.assertIn("github.event_name == 'issues'", job_gate)
        self.assertIn("github.event_name == 'issue_comment'", job_gate)
        self.assertIn("github.event.action == 'created'", job_gate)
        self.assertIn("github.event.comment.user.type != 'Bot'", job_gate)
        self.assertNotIn("github.event.comment.author_association", job_gate)
        self.assertNotIn("contains(github.event.comment.body, '/triage')", job_gate)

        triage = next(step for step in steps(data, "generate") if step.get("name") == "Triage issue")
        self.assertEqual(triage["with"]["allow-users"], "*")

    def test_create_spec_workflow_does_not_dispatch_review_after_pr_creation(self) -> None:
        data = workflow(".github/workflows/create-spec-from-issue.yml")
        self.assertNotIn("actions", data["permissions"])

        create_steps = steps(data, "create-spec")
        create_pr = next(step for step in create_steps if step.get("name") == "Create or update spec pull request")
        step_names = [step.get("name") for step in create_steps]

        self.assertIn(".github/scripts/finalize_spec_pr.py", create_pr["run"])
        self.assertNotIn("--github-output", create_pr["run"])
        self.assertNotIn("id", create_pr)
        self.assertNotIn("Dispatch AI PR review", step_names)

    def test_create_implementation_workflow_does_not_dispatch_review_after_pr_creation(self) -> None:
        data = workflow(".github/workflows/create-implementation-from-issue.yml")
        self.assertNotIn("actions", data["permissions"])

        create_steps = steps(data, "create-implementation")
        workflow_update = next(step for step in create_steps if step.get("name") == "Check whether workflow update token is required")
        app_token = next(step for step in create_steps if step.get("name") == "Create GitHub App token for workflow updates")
        commit = next(step for step in create_steps if step.get("name") == "Commit and push implementation branch")
        create_pr = next(step for step in create_steps if step.get("name") == "Create or update implementation pull request")
        step_names = [step.get("name") for step in create_steps]

        self.assertLess(step_names.index("Check whether workflow update token is required"), step_names.index("Create GitHub App token for workflow updates"))
        self.assertLess(step_names.index("Create GitHub App token for workflow updates"), step_names.index("Commit and push implementation branch"))
        self.assertEqual(workflow_update["id"], "workflow_update")
        self.assertEqual(workflow_update["if"], commit["if"])
        self.assertIn(".github/workflows/", workflow_update["run"])
        self.assertIn("pr-metadata.json", workflow_update["run"])
        self.assertEqual(app_token["id"], "app-token")
        self.assertEqual(app_token["uses"], "actions/create-github-app-token@v3")
        self.assertEqual(app_token["if"], commit["if"] + " && steps.workflow_update.outputs.required == 'true'")
        self.assertEqual(app_token["with"]["client-id"], "${{ vars.APP_CLIENT_ID }}")
        self.assertEqual(app_token["with"]["private-key"], "${{ secrets.APP_PRIVATE_KEY }}")
        self.assertEqual(app_token["with"]["permission-contents"], "write")
        self.assertEqual(app_token["with"]["permission-workflows"], "write")
        self.assertNotIn("steps.workflow_update.outputs.required", commit["if"])
        self.assertEqual(commit["env"]["WORKFLOW_UPDATE_TOKEN"], "${{ steps.app-token.outputs.token }}")
        self.assertEqual(create_pr["id"], "pr")
        self.assertIn("--github-output \"$GITHUB_OUTPUT\"", create_pr["run"])
        self.assertNotIn("Dispatch AI PR review", step_names)

    def test_update_dedupe_pr_body_includes_captured_evidence_summary(self) -> None:
        data = workflow(".github/workflows/update-dedupe.yml")
        update_steps = steps(data, "update")
        step_names = [step.get("name") for step in update_steps]

        self.assertLess(
            step_names.index("Capture dedupe guidance summary"),
            step_names.index("Remove temporary feedback"),
        )

        capture = next(step for step in update_steps if step.get("name") == "Capture dedupe guidance summary")
        self.assertEqual(capture["id"], "guidance")
        self.assertIn("update-dedupe-output/status.json", capture["run"])
        self.assertIn("GITHUB_OUTPUT", capture["run"])

        create_pr = next(step for step in update_steps if step.get("name") == "Create or update pull request")
        self.assertEqual(create_pr["env"]["GUIDANCE_REASON"], "${{ steps.guidance.outputs.reason }}")
        self.assertIn("body_file=\"$(mktemp)\"", create_pr["run"])
        self.assertIn("trap 'rm -f \"$body_file\"' EXIT", create_pr["run"])
        self.assertIn(".github/scripts/write_update_dedupe_pr_body.py --output \"$body_file\"", create_pr["run"])
        self.assertIn("--body-file \"$body_file\"", create_pr["run"])
        self.assertNotIn("--body \"$body\"", create_pr["run"])
        self.assertNotIn("${{ steps.guidance.outputs.reason }}", create_pr["run"])

        changes = next(step for step in update_steps if step.get("name") == "Check for guidance changes")
        self.assertIn("git status --porcelain -- .agents/skills/dedupe-issue-repo", changes["run"])

    def test_respond_to_pr_comment_workflow_has_secure_triggers_and_gates(self) -> None:
        data = workflow(".github/workflows/respond-to-pr-comment.yml")
        triggers = data[True]

        self.assertEqual(triggers["issue_comment"]["types"], ["created"])
        self.assertEqual(triggers["pull_request_review_comment"]["types"], ["created"])
        self.assertEqual(triggers["pull_request_review"]["types"], ["submitted", "edited"])
        self.assertEqual(data["permissions"]["contents"], "read")
        self.assertEqual(data["permissions"]["pull-requests"], "read")
        self.assertEqual(data["permissions"]["issues"], "read")

        preflight_job = data["jobs"]["preflight"]
        self.assertEqual(preflight_job["permissions"]["contents"], "read")
        self.assertIn("github.event.issue.pull_request != null", preflight_job["if"])
        self.assertIn("contains(github.event.comment.body, '/fix')", preflight_job["if"])
        self.assertIn("github.event.review.body != null", preflight_job["if"])
        self.assertIn("contains(github.event.review.body", preflight_job["if"])

        respond_job = data["jobs"]["respond"]
        self.assertEqual(respond_job["needs"], "preflight")
        self.assertIn("needs.preflight.outputs.should_run == 'true'", respond_job["if"])
        self.assertIn("needs.preflight.outputs.branch_strategy != 'blocked'", respond_job["if"])
        self.assertEqual(respond_job["permissions"]["contents"], "write")
        self.assertEqual(respond_job["permissions"]["pull-requests"], "write")
        self.assertEqual(respond_job["permissions"]["issues"], "write")

        preflight_steps = steps(data, "preflight")
        prepare = next(step for step in preflight_steps if step.get("name") == "Prepare PR comment context")
        self.assertIn(".github/scripts/prepare_pr_comment_context.py", prepare["run"])
        self.assertIn("--github-output \"$GITHUB_OUTPUT\"", prepare["run"])

        respond_steps = steps(data, "respond")
        checkout = next(step for step in respond_steps if step.get("name") == "Checkout PR head")
        self.assertIn("steps.context.outputs.should_run == 'true'", checkout["if"])
        self.assertIn("steps.context.outputs.branch_strategy != 'blocked'", checkout["if"])
        self.assertEqual(checkout["with"]["persist-credentials"], False)
        self.assertEqual(checkout["with"]["repository"], "${{ steps.context.outputs.head_repo }}")
        self.assertEqual(checkout["with"]["path"], "pr-worktree")
        self.assertNotIn("Configure push remote", [step.get("name") for step in respond_steps])

        diff_step = next(step for step in respond_steps if step.get("name") == "Snapshot PR diff")
        self.assertEqual(diff_step["working-directory"], "pr-worktree")
        self.assertEqual(diff_step["env"]["GITHUB_TOKEN"], "${{ github.token }}")
        self.assertIn("git_config=\"$(mktemp)\"", diff_step["run"])
        self.assertIn("trap 'rm -f \"$git_config\"' EXIT", diff_step["run"])
        self.assertIn("chmod 600 \"$git_config\"", diff_step["run"])
        self.assertIn("[http \"https://github.com/\"]", diff_step["run"])
        self.assertIn("extraheader = AUTHORIZATION: basic", diff_step["run"])
        self.assertIn("AUTHORIZATION: basic", diff_step["run"])
        self.assertIn("GIT_CONFIG_GLOBAL=\"$git_config\" GIT_TERMINAL_PROMPT=0", diff_step["run"])
        self.assertIn("fetch --no-tags --depth=1", diff_step["run"])
        self.assertIn("\"https://github.com/${GITHUB_REPOSITORY}.git\"", diff_step["run"])
        self.assertNotIn("git remote add base", diff_step["run"])
        self.assertNotIn("git -c \"http.https://github.com/.extraheader", diff_step["run"])
        self.assertNotIn("${auth_header}", diff_step["run"])
        self.assertNotIn("x-access-token:${GITHUB_TOKEN}@github.com", diff_step["run"])
        self.assertIn("../.github/scripts/build_pr_diff.py", diff_step["run"])
        self.assertIn("--output pr_diff.txt", diff_step["run"])

        prepare_workspace = next(step for step in respond_steps if step.get("name") == "Prepare implementation workspace")
        self.assertIn("rm -rf pr-worktree/.codex-runtime", prepare_workspace["run"])
        self.assertIn("cp -R .agents/skills pr-worktree/.codex-runtime/skills", prepare_workspace["run"])
        self.assertNotIn("pr-worktree/.agents/skills", prepare_workspace["run"])

        worktree = next(step for step in respond_steps if step.get("name") == "Check PR comment response worktree changes")
        self.assertIn("':!pr_comment_context.json'", worktree["run"])
        self.assertIn("':!pr_event.json'", worktree["run"])
        self.assertIn("':!review_comment_ids.json'", worktree["run"])
        self.assertIn("':!pr_diff.txt'", worktree["run"])

        gated_steps = [
            "Respond to PR comment",
            "Commit and push PR comment response branch",
            "Apply PR comment response result",
        ]
        for name in gated_steps:
            with self.subTest(step=name):
                step = next(item for item in respond_steps if item.get("name") == name)
                self.assertIn("steps.context.outputs.should_run == 'true'", step["if"])
                self.assertIn("steps.context.outputs.branch_strategy != 'blocked'", step["if"])

        ai_step = next(step for step in respond_steps if step.get("name") == "Respond to PR comment")
        prompt = ai_step["with"]["prompt"]
        self.assertIn("Treat PR body, PR comments, review bodies, review comments", prompt)
        self.assertIn("Do not stage files, commit, push", prompt)
        self.assertIn("pr_event.json", prompt)
        self.assertIn("pr_event.json includes the pull request title, body", prompt)
        self.assertIn("review_comment_ids.json", prompt)
        self.assertIn("resolved and outdated thread state", prompt)
        self.assertIn("address all inline comments", prompt)
        self.assertIn("unresolved comments", prompt)
        self.assertIn("handle every listed inline review", prompt)
        self.assertIn("is_resolved set to false", prompt)
        self.assertIn("do not guess unresolved state", prompt)
        self.assertIn("is_outdated only means the original diff position is", prompt)
        self.assertIn("do not skip an unresolved outdated comment solely", prompt)
        self.assertIn("underlying issue still exists", prompt)
        self.assertIn("Do not limit the", prompt)
        self.assertIn("resolves multiple inline review comments", prompt)
        self.assertIn("resolved_review_comments entry for each comment", prompt)
        self.assertIn("trigger_body", prompt)
        self.assertIn("Use only the stable local JSON and snapshot files", prompt)
        self.assertIn("do not fetch additional GitHub", prompt)
        self.assertIn("or call GitHub APIs", prompt)
        self.assertIn(".codex-runtime/skills/implement-specs/SKILL.md", prompt)
        self.assertNotIn(".codex-runtime/skills/implement-specs/scripts/fetch_github_context.py", prompt)
        self.assertNotIn(".agents/skills/implement-specs/SKILL.md", prompt)
        self.assertNotIn("GH_TOKEN", ai_step.get("env", {}))
        self.assertNotIn("GITHUB_TOKEN", ai_step.get("env", {}))

        commit = next(step for step in respond_steps if step.get("name") == "Commit and push PR comment response branch")
        workflow_update = next(step for step in respond_steps if step.get("name") == "Check whether workflow update token is required")
        app_token = next(step for step in respond_steps if step.get("name") == "Create GitHub App token for workflow updates")
        step_names = [step.get("name") for step in respond_steps]
        self.assertLess(step_names.index("Check whether workflow update token is required"), step_names.index("Create GitHub App token for workflow updates"))
        self.assertLess(step_names.index("Create GitHub App token for workflow updates"), step_names.index("Commit and push PR comment response branch"))
        self.assertEqual(workflow_update["id"], "workflow_update")
        self.assertEqual(workflow_update["if"], commit["if"])
        self.assertEqual(workflow_update["working-directory"], "pr-worktree")
        self.assertIn(".github/workflows/", workflow_update["run"])
        self.assertIn("pr-metadata.json", workflow_update["run"])
        self.assertEqual(app_token["id"], "app-token")
        self.assertEqual(app_token["uses"], "actions/create-github-app-token@v3")
        self.assertEqual(app_token["if"], commit["if"] + " && steps.workflow_update.outputs.required == 'true'")
        self.assertEqual(app_token["with"]["client-id"], "${{ vars.APP_CLIENT_ID }}")
        self.assertEqual(app_token["with"]["private-key"], "${{ secrets.APP_PRIVATE_KEY }}")
        self.assertEqual(app_token["with"]["permission-contents"], "write")
        self.assertEqual(app_token["with"]["permission-workflows"], "write")
        self.assertEqual(commit["env"]["GITHUB_TOKEN"], "${{ github.token }}")
        self.assertNotIn("steps.workflow_update.outputs.required", commit["if"])
        self.assertEqual(commit["env"]["WORKFLOW_UPDATE_TOKEN"], "${{ steps.app-token.outputs.token }}")


if __name__ == "__main__":
    unittest.main()
