from __future__ import annotations

import json
from pathlib import Path

import pytest

from newton.planning_bundle import generate_planning_bundle
from newton.planning_bundle_validation import PlanningBundleValidationError, validate_planning_bundle


def test_validate_planning_bundle_accepts_generated_bundle(tmp_path: Path):
    bundle_dir = generate_planning_bundle(
        Path("tests/fixtures/inputs/login_ticket.md"),
        out_dir=tmp_path,
    )

    result = validate_planning_bundle(bundle_dir)

    assert result.plan_id == "login"
    assert result.artifact_count == 8
    assert result.checklist_items == 5
    assert result.test_cases == 5
    assert result.tracker_items == 5


def test_validate_planning_bundle_rejects_missing_artifact(tmp_path: Path):
    bundle_dir = generate_planning_bundle(
        Path("tests/fixtures/inputs/login_ticket.md"),
        out_dir=tmp_path,
    )
    (bundle_dir / "qa-estimate.md").unlink()

    with pytest.raises(PlanningBundleValidationError, match="missing artifact: qa-estimate.md"):
        validate_planning_bundle(bundle_dir)


def test_validate_planning_bundle_rejects_test_case_count_mismatch(tmp_path: Path):
    bundle_dir = generate_planning_bundle(
        Path("tests/fixtures/inputs/login_ticket.md"),
        out_dir=tmp_path,
    )
    rows = (bundle_dir / "test-cases.csv").read_text().splitlines()
    (bundle_dir / "test-cases.csv").write_text("\n".join(rows[:-1]) + "\n")

    with pytest.raises(
        PlanningBundleValidationError,
        match="checklist/test-cases count mismatch: 5 != 4",
    ):
        validate_planning_bundle(bundle_dir)


def test_validate_planning_bundle_rejects_tracker_count_mismatch(tmp_path: Path):
    bundle_dir = generate_planning_bundle(
        Path("tests/fixtures/inputs/login_ticket.md"),
        out_dir=tmp_path,
    )
    tracker = (bundle_dir / "qa-run-tracker.md").read_text()
    tracker = tracker.replace("- [ ] User sees Dashboard\n  - env: dev\n  - status: not run\n  - notes:\n", "")
    (bundle_dir / "qa-run-tracker.md").write_text(tracker)

    with pytest.raises(
        PlanningBundleValidationError,
        match="checklist/tracker count mismatch: 5 != 4",
    ):
        validate_planning_bundle(bundle_dir)


def test_validate_planning_bundle_rejects_missing_baseline_risk(tmp_path: Path):
    bundle_dir = generate_planning_bundle(
        Path("tests/fixtures/inputs/login_ticket.md"),
        out_dir=tmp_path,
    )
    risk_map = (bundle_dir / "risk-map.md").read_text()
    risk_map = risk_map.replace(
        "| network failure | P1 | Slow, offline, timeout, and retry states can hide incomplete error handling |\n",
        "",
    )
    (bundle_dir / "risk-map.md").write_text(risk_map)

    with pytest.raises(PlanningBundleValidationError, match="missing baseline risk: network failure"):
        validate_planning_bundle(bundle_dir)


def test_validate_planning_bundle_rejects_manifest_path_that_does_not_match_artifact(tmp_path: Path):
    bundle_dir = generate_planning_bundle(
        Path("tests/fixtures/inputs/login_ticket.md"),
        out_dir=tmp_path,
    )
    manifest_path = bundle_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["artifacts"]["checklist"] = str(bundle_dir / "wrong-checklist.md")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    with pytest.raises(PlanningBundleValidationError, match="missing artifact: checklist.md"):
        validate_planning_bundle(bundle_dir)
