from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml


DOGFOOD_ROOT = Path("qa/dogfood/login")


def test_login_dogfood_package_has_full_qa_loop_artifacts():
    required_paths = [
        DOGFOOD_ROOT / "inputs" / "ticket.md",
        DOGFOOD_ROOT / "inputs" / "policy.md",
        DOGFOOD_ROOT / "inputs" / "design-notes.md",
        DOGFOOD_ROOT / "plan" / "qa-scope.md",
        DOGFOOD_ROOT / "plan" / "qa-estimate.md",
        DOGFOOD_ROOT / "plan" / "checklist.md",
        DOGFOOD_ROOT / "plan" / "test-cases.csv",
        DOGFOOD_ROOT / "plan" / "risk-map.md",
        DOGFOOD_ROOT / "plan" / "automation-candidates.md",
        DOGFOOD_ROOT / "plan" / "qa-run-tracker.md",
        DOGFOOD_ROOT / "plan" / "manifest.json",
        DOGFOOD_ROOT / "scenario" / "login-smoke.generated.yaml",
        DOGFOOD_ROOT / "scenario" / "login_ticket.template.plan.json",
        DOGFOOD_ROOT / "bug-ticket-draft.md",
    ]

    missing = [path for path in required_paths if not path.exists()]

    assert missing == []


def test_login_dogfood_plan_cites_multi_source_evidence():
    estimate = (DOGFOOD_ROOT / "plan" / "qa-estimate.md").read_text()

    assert "## Evidence Factors" in estimate
    assert "`qa/dogfood/login/inputs/ticket.md`" in estimate
    assert "`qa/dogfood/login/inputs/policy.md`" in estimate
    assert "`qa/dogfood/login/inputs/design-notes.md`" in estimate


def test_login_dogfood_scenario_and_provenance_are_linked():
    scenario_path = DOGFOOD_ROOT / "scenario" / "login-smoke.generated.yaml"
    provenance_path = DOGFOOD_ROOT / "scenario" / "login_ticket.template.plan.json"

    scenario = yaml.safe_load(scenario_path.read_text())
    provenance = json.loads(provenance_path.read_text())

    assert scenario["scenario"]["id"] == "login-smoke"
    assert provenance["validation_status"] == "accepted"
    assert Path(provenance["accepted_scenario_path"]) == scenario_path


def test_login_dogfood_has_passing_and_failing_runs_with_evidence():
    run_results = sorted((DOGFOOD_ROOT / "runs").glob("run_*/result.json"))
    assert len(run_results) >= 2

    payloads = [json.loads(path.read_text()) for path in run_results]
    statuses = {payload["status"] for payload in payloads}

    assert "passed" in statuses
    assert "failed" in statuses

    failed_payload = next(payload for payload in payloads if payload["status"] == "failed")
    failed_run_dir = next(path.parent for path in run_results if json.loads(path.read_text())["status"] == "failed")
    evidence_paths = [
        artifact["path"]
        for artifact in failed_payload["evidence"]
        + [artifact for step in failed_payload["steps"] for artifact in step.get("evidence", [])]
    ]

    assert any(path.endswith(".png") for path in evidence_paths)
    assert "playwright-trace.zip" in evidence_paths
    for evidence_path in evidence_paths:
        assert (failed_run_dir / evidence_path).exists()


def test_login_dogfood_tracker_links_failed_run_and_bug_draft():
    tracker = (DOGFOOD_ROOT / "plan" / "qa-run-tracker.md").read_text()
    bug_draft = (DOGFOOD_ROOT / "bug-ticket-draft.md").read_text()

    assert "qa/dogfood/login/runs/run_" in tracker
    assert "## Reproduction Steps" in bug_draft
    assert "Environment: stg" in bug_draft


@pytest.mark.parametrize(
    "snippet",
    [
        "newton qa plan-bundle qa/dogfood/login/inputs/ticket.md",
        "newton qa plan qa/dogfood/login/inputs/ticket.md",
        "newton qa run qa/dogfood/login/scenario/login-smoke.generated.yaml",
        "newton qa tracker-update-from-run qa/dogfood/login/plan/qa-run-tracker.md",
        "newton qa bug-draft qa/dogfood/login/plan/qa-run-tracker.md",
    ],
)
def test_readme_documents_login_dogfood_loop(snippet: str):
    readme = Path("README.md").read_text()

    assert "Dogfood: full QA loop" in readme
    assert snippet in readme
