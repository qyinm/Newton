from __future__ import annotations

from pathlib import Path

import pytest

from newton.tracker_update import TrackerUpdateError, update_tracker_item


TRACKER = """# QA Run Tracker: Login

## Environment Status

- dev: not run
- stg: not run
- prod: not run

## Checklist Status

- [ ] User can open login page
  - env: dev
  - status: not run
  - notes:
- [ ] User sees Dashboard
  - env: dev
  - status: not run
  - notes:
"""


def test_update_tracker_item_updates_generated_tracker_block(tmp_path: Path):
    tracker_path = tmp_path / "qa-run-tracker.md"
    tracker_path.write_text(TRACKER)

    updated_path = update_tracker_item(
        tracker_path,
        item_number=2,
        env="stg",
        status="failed",
        notes="Dashboard never appears after submit",
    )

    assert updated_path == tracker_path
    updated = tracker_path.read_text()
    assert "- dev: not run" in updated
    assert "- stg: failed" in updated
    assert "- prod: not run" in updated
    assert "- [ ] User can open login page\n  - env: dev\n  - status: not run\n  - notes:" in updated
    assert "- [x] User sees Dashboard\n  - env: stg\n  - status: failed\n  - notes: Dashboard never appears after submit" in updated


def test_update_tracker_item_rejects_invalid_status(tmp_path: Path):
    tracker_path = tmp_path / "qa-run-tracker.md"
    tracker_path.write_text(TRACKER)

    with pytest.raises(TrackerUpdateError, match="invalid tracker status"):
        update_tracker_item(
            tracker_path,
            item_number=1,
            env="stg",
            status="done",
            notes="ok",
        )


def test_update_tracker_item_rejects_missing_item_number(tmp_path: Path):
    tracker_path = tmp_path / "qa-run-tracker.md"
    tracker_path.write_text(TRACKER)

    with pytest.raises(TrackerUpdateError, match="tracker item not found: 3"):
        update_tracker_item(
            tracker_path,
            item_number=3,
            env="stg",
            status="passed",
            notes="ok",
        )
