from __future__ import annotations

import unittest


def configured_login(input_login: str = "", variable_login: str = "codex") -> str:
    return input_login or variable_login


def mentions_agent(comment: str, input_login: str = "", variable_login: str = "codex") -> bool:
    login = configured_login(input_login, variable_login)
    return bool(login and f"@{login}" in comment)


def issue_event_gate(
    *,
    event_name: str,
    action: str = "",
    label: str = "",
    assignee: str = "",
    labels: list[str] | None = None,
    assignees: list[str] | None = None,
    comment: str = "",
    ready_label: str,
    superseded_by_label: str = "",
    input_login: str = "",
    variable_login: str = "codex",
    is_pull_request_issue: bool = False,
) -> bool:
    if event_name == "workflow_dispatch":
        return True
    if is_pull_request_issue:
        return False
    if ready_label not in (labels or []):
        return False
    if superseded_by_label and superseded_by_label in (labels or []):
        return False

    login = configured_login(input_login, variable_login)
    if event_name == "issue_comment":
        return mentions_agent(comment, input_login, variable_login)
    if event_name == "issues" and action == "labeled":
        return label == ready_label and login in (assignees or [])
    if event_name == "issues" and action == "assigned":
        return assignee == login and ready_label in (labels or [])
    return False


class WorkflowTriggerGateTest(unittest.TestCase):
    def test_spec_issue_events_only_pass_when_ready_label_and_agent_assignment_meet(self) -> None:
        self.assertTrue(
            issue_event_gate(
                event_name="issues",
                action="labeled",
                label="ready-to-spec",
                labels=["ready-to-spec"],
                assignees=["codex"],
                ready_label="ready-to-spec",
                superseded_by_label="ready-to-implement",
            )
        )
        self.assertTrue(
            issue_event_gate(
                event_name="issues",
                action="assigned",
                assignee="codex",
                labels=["ready-to-spec"],
                ready_label="ready-to-spec",
                superseded_by_label="ready-to-implement",
            )
        )
        self.assertFalse(
            issue_event_gate(
                event_name="issues",
                action="labeled",
                label="ready-to-implement",
                labels=["ready-to-implement"],
                assignees=["codex"],
                ready_label="ready-to-spec",
                superseded_by_label="ready-to-implement",
            )
        )
        self.assertFalse(
            issue_event_gate(
                event_name="issues",
                action="assigned",
                assignee="alice",
                labels=["ready-to-spec"],
                assignees=["codex", "alice"],
                ready_label="ready-to-spec",
                superseded_by_label="ready-to-implement",
            )
        )
        self.assertFalse(
            issue_event_gate(
                event_name="issues",
                action="assigned",
                assignee="codex",
                labels=["ready-to-spec", "ready-to-implement"],
                ready_label="ready-to-spec",
                superseded_by_label="ready-to-implement",
            )
        )

    def test_implementation_issue_events_only_pass_when_ready_label_and_agent_assignment_meet(self) -> None:
        self.assertTrue(
            issue_event_gate(
                event_name="issues",
                action="labeled",
                label="ready-to-implement",
                labels=["ready-to-implement"],
                assignees=["codex"],
                ready_label="ready-to-implement",
            )
        )
        self.assertTrue(
            issue_event_gate(
                event_name="issues",
                action="assigned",
                assignee="codex",
                labels=["ready-to-implement"],
                ready_label="ready-to-implement",
            )
        )
        self.assertFalse(
            issue_event_gate(
                event_name="issues",
                action="labeled",
                label="plan-approved",
                labels=["ready-to-implement"],
                assignees=["codex"],
                ready_label="ready-to-implement",
            )
        )

    def test_issue_comment_gate_requires_agent_mention_and_regular_issue(self) -> None:
        self.assertTrue(
            issue_event_gate(
                event_name="issue_comment",
                comment="@codex please continue",
                labels=["ready-to-spec"],
                ready_label="ready-to-spec",
            )
        )
        self.assertFalse(
            issue_event_gate(
                event_name="issue_comment",
                comment="please continue",
                labels=["ready-to-spec"],
                ready_label="ready-to-spec",
            )
        )
        self.assertFalse(
            issue_event_gate(
                event_name="issue_comment",
                comment="@codex please continue",
                labels=["ready-to-spec"],
                ready_label="ready-to-spec",
                is_pull_request_issue=True,
            )
        )
        self.assertFalse(
            issue_event_gate(
                event_name="issue_comment",
                comment="@codex please continue",
                labels=[],
                ready_label="ready-to-spec",
            )
        )

    def test_unconfigured_agent_login_does_not_match_comments(self) -> None:
        self.assertFalse(
            issue_event_gate(
                event_name="issue_comment",
                comment="@codex please continue",
                labels=["ready-to-spec"],
                ready_label="ready-to-spec",
                variable_login="",
            )
        )


if __name__ == "__main__":
    unittest.main()
