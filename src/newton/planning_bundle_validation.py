from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path


class PlanningBundleValidationError(ValueError):
    """Raised when a planning bundle does not satisfy Newton's artifact contract."""


@dataclass(frozen=True)
class PlanningBundleValidationResult:
    plan_id: str
    artifact_count: int
    checklist_items: int
    test_cases: int
    tracker_items: int


REQUIRED_ARTIFACTS = {
    "qa_scope": "qa-scope.md",
    "checklist": "checklist.md",
    "test_cases": "test-cases.csv",
    "risk_map": "risk-map.md",
    "qa_estimate": "qa-estimate.md",
    "automation_candidates": "automation-candidates.md",
    "qa_run_tracker": "qa-run-tracker.md",
}

BASELINE_RISKS = [
    "functional",
    "edge case",
    "network failure",
    "permission/role",
    "policy conflict",
    "regression",
]


def validate_planning_bundle(bundle_dir: Path) -> PlanningBundleValidationResult:
    if not bundle_dir.exists() or not bundle_dir.is_dir():
        raise PlanningBundleValidationError(f"planning bundle not found: {bundle_dir}")

    manifest_path = bundle_dir / "manifest.json"
    if not manifest_path.exists():
        raise PlanningBundleValidationError("missing artifact: manifest.json")

    try:
        manifest = json.loads(manifest_path.read_text())
    except json.JSONDecodeError as exc:
        raise PlanningBundleValidationError(f"invalid manifest.json: {exc.msg}") from exc

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict):
        raise PlanningBundleValidationError("manifest missing artifacts")

    resolved_artifacts = _validate_artifact_paths(bundle_dir, artifacts)
    checklist_count = _count_checklist_items(resolved_artifacts["checklist"])
    test_case_count = _count_test_cases(resolved_artifacts["test_cases"])
    tracker_count = _count_tracker_items(resolved_artifacts["qa_run_tracker"])

    if checklist_count != test_case_count:
        raise PlanningBundleValidationError(
            f"checklist/test-cases count mismatch: {checklist_count} != {test_case_count}"
        )
    if checklist_count != tracker_count:
        raise PlanningBundleValidationError(
            f"checklist/tracker count mismatch: {checklist_count} != {tracker_count}"
        )

    _validate_baseline_risks(resolved_artifacts["risk_map"])

    plan_id = manifest.get("plan_id")
    if not isinstance(plan_id, str) or not plan_id:
        raise PlanningBundleValidationError("manifest missing plan_id")

    return PlanningBundleValidationResult(
        plan_id=plan_id,
        artifact_count=len(REQUIRED_ARTIFACTS) + 1,
        checklist_items=checklist_count,
        test_cases=test_case_count,
        tracker_items=tracker_count,
    )


def _validate_artifact_paths(bundle_dir: Path, artifacts: dict[str, object]) -> dict[str, Path]:
    resolved: dict[str, Path] = {}
    for key, filename in REQUIRED_ARTIFACTS.items():
        raw_path = artifacts.get(key)
        if not isinstance(raw_path, str) or not raw_path:
            raise PlanningBundleValidationError(f"missing artifact: {filename}")
        artifact_path = Path(raw_path)
        if not artifact_path.is_absolute():
            artifact_path = Path(artifact_path)
        if artifact_path.name != filename or not artifact_path.exists():
            raise PlanningBundleValidationError(f"missing artifact: {filename}")
        resolved[key] = artifact_path
    return resolved


def _count_checklist_items(checklist_path: Path) -> int:
    return _count_markdown_checkbox_items(checklist_path.read_text())


def _count_tracker_items(tracker_path: Path) -> int:
    return _count_markdown_checkbox_items(tracker_path.read_text())


def _count_markdown_checkbox_items(markdown: str) -> int:
    return sum(
        1
        for line in markdown.splitlines()
        if line.strip().startswith(("- [ ] ", "- [x] ", "- [X] "))
    )


def _count_test_cases(test_cases_path: Path) -> int:
    with test_cases_path.open(newline="") as csv_file:
        return sum(1 for _ in csv.DictReader(csv_file))


def _validate_baseline_risks(risk_map_path: Path) -> None:
    risk_map = risk_map_path.read_text().lower()
    for risk in BASELINE_RISKS:
        if f"| {risk} |" not in risk_map:
            raise PlanningBundleValidationError(f"missing baseline risk: {risk}")
