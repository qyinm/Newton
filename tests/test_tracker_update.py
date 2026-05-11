from __future__ import annotations

from pathlib import Path

import pytest

from newton.tracker_update import TrackerUpdateError, update_tracker_item, update_tracker_item_from_run


TRACKER = """# QA Run Tracker: Login

## Environment Status

- dev: not run
- stg: not run
- prod: not run

## Checklist Status

- [ ] User can open login page
  - dev:
    - status: not run
    - notes:
    - runs:
  - stg:
    - status: not run
    - notes:
    - runs:
      - Run old_stg failed; report: /tmp/old-report.md
  - prod:
    - status: not run
    - notes:
    - runs:
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
    assert "- [ ] User can open login page\n  - dev:\n    - status: not run" in updated
    assert "      - Run old_stg failed; report: /tmp/old-report.md" in updated
    assert "- [ ] User sees Dashboard" in updated
    assert "  - dev:\n    - status: not run\n    - notes:\n    - runs:" in updated
    assert "  - stg:\n    - status: failed\n    - notes: Dashboard never appears after submit\n    - runs:" in updated
    assert "  - prod:\n    - status: not run\n    - notes:\n    - runs:" in updated
    assert "  - env:" not in updated


def test_update_tracker_item_from_run_maps_result_status_and_preserves_run_history(tmp_path: Path):
    tracker_path = tmp_path / "qa-run-tracker.md"
    tracker_path.write_text(TRACKER)
    run_path = tmp_path / "runs" / "run_123"
    run_path.mkdir(parents=True)
    (run_path / "result.json").write_text(
        '{"run_id":"run_123","scenario_id":"web-login-smoke","target_id":"web","platform":"web","status":"passed","steps":[],"evidence":[]}'
    )
    (run_path / "qa-report.md").write_text("# report")

    update_tracker_item_from_run(tracker_path, item_number=1, env="stg", run_path=run_path)

    updated = tracker_path.read_text()
    assert "- stg: passed" in updated
    assert "- [ ] User can open login page" in updated
    assert "  - stg:\n    - status: passed\n    - notes: Run run_123 passed; report:" in updated
    assert "      - Run old_stg failed; report: /tmp/old-report.md" in updated
    assert "      - Run run_123 passed; report:" in updated
    assert str(run_path / "qa-report.md") in updated


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
