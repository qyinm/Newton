from __future__ import annotations

from pathlib import Path

import pytest

from newton.bug_draft import BugDraftError, write_bug_ticket_draft
from newton.tracker_update import update_tracker_item_from_run


def test_write_bug_ticket_draft_from_first_failed_tracker_item(tmp_path: Path):
    tracker_path = tmp_path / "qa-run-tracker.md"
    tracker_path.write_text(
        """# QA Run Tracker: Login

## Environment Status

- dev: not run
- stg: not run
- prod: not run

## Checklist Status

- [ ] User can open login page
  - env: dev
  - status: passed
  - notes: ok
- [ ] User sees Dashboard
  - env: stg
  - status: failed
  - notes: Dashboard never appears after submit
- [ ] User can log out
  - env: stg
  - status: not run
  - notes:
"""
    )

    output_path = write_bug_ticket_draft(tracker_path)

    assert output_path == tmp_path / "bug-ticket-draft.md"
    draft = output_path.read_text()
    assert "# Bug Ticket Draft: [stg] User sees Dashboard" in draft
    assert "## Issue Fields" in draft
    assert "- Title: [stg] User sees Dashboard" in draft
    assert "- Severity: S2 - Major" in draft
    assert "- Priority: P1" in draft
    assert "- Environment: stg" in draft
    assert "- Failed Step: User sees Dashboard" in draft
    assert "- Suspected Owner/Area: QA triage / Login flow" in draft
    assert "## Failed Checklist Item" in draft
    assert "- Item: User sees Dashboard" in draft
    assert "- Status: failed" in draft
    assert "Dashboard never appears after submit" in draft
    assert "## Reproduction Steps" in draft
    assert "## Expected Result" in draft
    assert "## Actual Result" in draft
    assert "## Source References" in draft
    assert f"- Tracker: `{tracker_path}`" in draft
    assert "## Evidence Paths" in draft
    assert "- Not linked in tracker notes." in draft


def test_write_bug_ticket_draft_rejects_tracker_without_failed_item(tmp_path: Path):
    tracker_path = tmp_path / "qa-run-tracker.md"
    tracker_path.write_text(
        """# QA Run Tracker: Login

## Checklist Status

- [ ] User can open login page
  - env: dev
  - status: not run
  - notes:
"""
    )

    with pytest.raises(BugDraftError, match="no failed tracker item found"):
        write_bug_ticket_draft(tracker_path)


def test_write_bug_ticket_draft_reads_environment_matrix_tracker(tmp_path: Path):
    tracker_path = tmp_path / "qa-run-tracker.md"
    tracker_path.write_text(
        """# QA Run Tracker: Login

## Checklist Status

- [ ] User sees Dashboard
  - dev:
    - status: passed
    - notes: ok
    - runs:
  - stg:
    - status: failed
    - notes: Dashboard never appears after submit
    - runs:
      - Run run_123 failed; report: /tmp/run_123/qa-report.md
  - prod:
    - status: not run
    - notes:
    - runs:
"""
    )

    output_path = write_bug_ticket_draft(tracker_path)

    draft = output_path.read_text()
    assert "# Bug Ticket Draft: [stg] User sees Dashboard" in draft
    assert "- Environment: stg" in draft
    assert "Dashboard never appears after submit" in draft


def test_write_bug_ticket_draft_uses_run_evidence_from_tracker_update(tmp_path: Path):
    tracker_path = tmp_path / "qa-run-tracker.md"
    tracker_path.write_text(
        """# QA Run Tracker: Login

## Checklist Status

- [ ] User sees Dashboard
  - dev:
    - status: not run
    - notes:
    - runs:
  - stg:
    - status: not run
    - notes:
    - runs:
  - prod:
    - status: not run
    - notes:
    - runs:
"""
    )
    run_path = tmp_path / "runs" / "run_123"
    run_path.mkdir(parents=True)
    (run_path / "result.json").write_text(
        """{
  "contract_version": "v0.1",
  "run_id": "run_123",
  "scenario_id": "login-smoke",
  "target_id": "web",
  "platform": "web",
  "status": "failed",
  "steps": [
    {"id": "open-login", "action": "navigate", "status": "passed", "error": null, "evidence": []},
    {"id": "submit", "action": "tap", "status": "passed", "error": null, "evidence": []},
    {
      "id": "assert-dashboard",
      "action": "assert_visible",
      "status": "failed",
      "error": "Dashboard text never became visible",
      "evidence": [
        {
          "kind": "screenshot",
          "path": "failure-step-003-assert-dashboard.png",
          "description": "Failure screenshot"
        }
      ]
    }
  ],
  "evidence": [
    {"kind": "trace", "path": "playwright-trace.zip", "description": "Playwright trace"}
  ],
  "planning": {
    "input_path": "qa/inputs/login-ticket.md",
    "accepted_scenario_path": "qa/scenario/login-smoke.yaml",
    "provenance_path": "qa/scenario/login-smoke.plan.json"
  }
}
"""
    )
    (run_path / "qa-report.md").write_text("# report")

    update_tracker_item_from_run(tracker_path, item_number=1, env="stg", run_path=run_path)
    output_path = write_bug_ticket_draft(tracker_path)

    draft = output_path.read_text()
    assert output_path == tmp_path / "bug-ticket-draft.md"
    assert "# Bug Ticket Draft: [stg] login-smoke failed on web" in draft
    assert "- Failed Step: assert-dashboard (assert_visible)" in draft
    assert "- Suspected Owner/Area: Web / login-smoke" in draft
    assert "1. navigate: `open-login`" in draft
    assert "2. tap: `submit`" in draft
    assert "3. assert_visible: `assert-dashboard`" in draft
    assert "Dashboard text never became visible" in draft
    assert f"- Run result: `{run_path / 'result.json'}`" in draft
    assert f"- Run report: `{run_path / 'qa-report.md'}`" in draft
    assert "- Planning input: `qa/inputs/login-ticket.md`" in draft
    assert f"- `{run_path / 'failure-step-003-assert-dashboard.png'}`" in draft
    assert f"- `{run_path / 'playwright-trace.zip'}`" in draft


def test_write_bug_ticket_draft_from_run_does_not_echo_tracker_notes(tmp_path: Path):
    tracker_path = tmp_path / "qa-run-tracker.md"
    run_path = tmp_path / "runs" / "run_123"
    run_path.mkdir(parents=True)
    (run_path / "result.json").write_text(
        """{
  "contract_version": "v0.1",
  "run_id": "run_123",
  "scenario_id": "secure-login",
  "target_id": "web",
  "platform": "web",
  "status": "failed",
  "steps": [
    {
      "id": "password",
      "action": "fill",
      "status": "failed",
      "error": "[secure value redacted]",
      "evidence": []
    }
  ],
  "evidence": []
}
"""
    )
    tracker_path.write_text(
        f"""# QA Run Tracker: Login

## Checklist Status

- [ ] User can securely log in
  - dev:
    - status: failed
    - notes: Run run_123 failed; report: {run_path / "qa-report.md"}; result: {run_path / "result.json"}; operator note: typed super-secret-password
    - runs:
      - Run run_123 failed; report: {run_path / "qa-report.md"}; result: {run_path / "result.json"}
  - stg:
    - status: not run
    - notes:
    - runs:
  - prod:
    - status: not run
    - notes:
    - runs:
"""
    )

    output_path = write_bug_ticket_draft(tracker_path)

    draft = output_path.read_text()
    assert "super-secret-password" not in draft
    assert "[secure value redacted]" in draft
    assert "Run-derived draft; see Source References." in draft


@pytest.mark.parametrize(
    ("output_format", "heading", "title_label"),
    [
        ("linear", "# Linear Issue Draft", "Title: [stg] User sees Dashboard"),
        ("jira", "# Jira Issue Draft", "Summary: [stg] User sees Dashboard"),
    ],
)
def test_write_bug_ticket_draft_supports_issue_tracker_file_first_formats(
    tmp_path: Path,
    output_format: str,
    heading: str,
    title_label: str,
):
    tracker_path = tmp_path / "qa-run-tracker.md"
    tracker_path.write_text(
        """# QA Run Tracker: Login

## Checklist Status

- [ ] User sees Dashboard
  - env: stg
  - status: failed
  - notes: Dashboard never appears after submit
"""
    )

    output_path = write_bug_ticket_draft(tracker_path, output_format=output_format)

    draft = output_path.read_text()
    assert output_path == tmp_path / "bug-ticket-draft.md"
    assert heading in draft
    assert title_label in draft
    assert "Priority: P1" in draft
    assert "Labels: qa, bug, stg" in draft
