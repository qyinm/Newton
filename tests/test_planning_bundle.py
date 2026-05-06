from __future__ import annotations

import json
from pathlib import Path

from newton.planning_bundle import generate_planning_bundle


def test_generate_planning_bundle_writes_minimal_prd_artifacts(tmp_path: Path):
    bundle_dir = generate_planning_bundle(
        Path("tests/fixtures/inputs/login_ticket.md"),
        out_dir=tmp_path,
    )

    assert bundle_dir == tmp_path / "login"
    expected_files = {
        "qa-scope.md",
        "checklist.md",
        "risk-map.md",
        "manifest.json",
    }
    assert {path.name for path in bundle_dir.iterdir()} == expected_files

    manifest = json.loads((bundle_dir / "manifest.json").read_text())
    assert manifest == {
        "plan_id": "login",
        "input_path": "tests/fixtures/inputs/login_ticket.md",
        "artifacts": {
            "qa_scope": str(bundle_dir / "qa-scope.md"),
            "checklist": str(bundle_dir / "checklist.md"),
            "risk_map": str(bundle_dir / "risk-map.md"),
        },
    }

    scope = (bundle_dir / "qa-scope.md").read_text()
    assert "# QA Scope: Login" in scope
    assert "Users should be able to log in with email and password." in scope

    checklist = (bundle_dir / "checklist.md").read_text()
    assert "# QA Checklist: Login" in checklist
    assert "- [ ] User can open login page" in checklist
    assert "- [ ] User sees Dashboard" in checklist

    risk_map = (bundle_dir / "risk-map.md").read_text()
    assert "# Risk Map: Login" in risk_map
    assert "| functional | P0 | Login flow blocks core user access |" in risk_map


def test_generate_planning_bundle_rejects_empty_input(tmp_path: Path):
    empty = tmp_path / "empty.md"
    empty.write_text("\n")

    try:
        generate_planning_bundle(empty, out_dir=tmp_path / "plans")
    except ValueError as exc:
        assert "input markdown is empty" in str(exc)
    else:
        raise AssertionError("expected empty markdown to be rejected")
