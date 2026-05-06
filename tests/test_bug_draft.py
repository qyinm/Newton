from __future__ import annotations

from pathlib import Path

import pytest

from newton.bug_draft import BugDraftError, write_bug_ticket_draft


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
    assert "# Bug Ticket Draft: User sees Dashboard" in draft
    assert "## Failed Checklist Item" in draft
    assert "User sees Dashboard" in draft
    assert "Environment: stg" in draft
    assert "Status: failed" in draft
    assert "Dashboard never appears after submit" in draft
    assert "## Reproduction Steps" in draft


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
