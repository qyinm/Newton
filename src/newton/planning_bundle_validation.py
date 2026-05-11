from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

from newton.models import ArtifactContractVersionError, require_artifact_contract_version


class PlanningBundleValidationError(ValueError):
    """Raised when a planning bundle does not satisfy Newton's artifact contract."""


@dataclass(frozen=True)
class PlanningBundleValidationResult:
    plan_id: str
    artifact_count: int
    checklist_items: int
    test_cases: int
    tracker_items: int


@dataclass(frozen=True)
class _TrackerItem:
    text: str
    environments: frozenset[str]
    statuses: dict[str, str]


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
TRACKER_ENVS = ("dev", "stg", "prod")
TRACKER_STATUSES = {"not run", "passed", "failed", "blocked", "needs retest"}


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

    try:
        require_artifact_contract_version(manifest, artifact_name="manifest.json")
    except ArtifactContractVersionError as exc:
        raise PlanningBundleValidationError(str(exc)) from exc

    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, dict):
        raise PlanningBundleValidationError("manifest missing artifacts")

    resolved_artifacts = _validate_artifact_paths(bundle_dir, artifacts)
    checklist_items = _read_checklist_items(resolved_artifacts["checklist"])
    checklist_count = len(checklist_items)
    test_case_count = _count_test_cases(resolved_artifacts["test_cases"])
    tracker_items = _read_tracker_items(resolved_artifacts["qa_run_tracker"])
    tracker_count = len(tracker_items)

    if checklist_count != test_case_count:
        raise PlanningBundleValidationError(
            f"checklist/test-cases count mismatch: {checklist_count} != {test_case_count}"
        )
    if checklist_count != tracker_count:
        raise PlanningBundleValidationError(
            f"checklist/tracker count mismatch: {checklist_count} != {tracker_count}"
        )
    _validate_tracker_items(checklist_items, tracker_items)

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
    return len(_read_checklist_items(checklist_path))


def _count_tracker_items(tracker_path: Path) -> int:
    return len(_read_tracker_items(tracker_path))


def _read_checklist_items(checklist_path: Path) -> list[str]:
    return [
        _checkbox_item_text(line.strip())
        for line in checklist_path.read_text().splitlines()
        if _is_checkbox(line)
    ]


def _read_tracker_items(tracker_path: Path) -> list[_TrackerItem]:
    lines = tracker_path.read_text().splitlines()
    item_starts = [index for index, line in enumerate(lines) if _is_checkbox(line)]
    items: list[_TrackerItem] = []
    for item_index, start in enumerate(item_starts):
        end = item_starts[item_index + 1] if item_index + 1 < len(item_starts) else len(lines)
        items.append(_parse_tracker_item(lines[start], lines[start + 1 : end]))
    return items


def _parse_tracker_item(item_line: str, detail_lines: list[str]) -> _TrackerItem:
    text = _checkbox_item_text(item_line.strip())
    environments: set[str] = set()
    statuses: dict[str, str] = {}
    current_env: str | None = None

    for line in detail_lines:
        stripped = line.strip()
        env = _tracker_environment_heading(stripped)
        if env is not None:
            environments.add(env)
            current_env = env
            continue
        if current_env is None or not stripped.startswith("- status:"):
            continue
        status = stripped.removeprefix("- status:").strip().lower()
        statuses[current_env] = status

    return _TrackerItem(text=text, environments=frozenset(environments), statuses=statuses)


def _validate_tracker_items(checklist_items: list[str], tracker_items: list[_TrackerItem]) -> None:
    for index, (checklist_item, tracker_item) in enumerate(
        zip(checklist_items, tracker_items, strict=True),
        start=1,
    ):
        if tracker_item.text != checklist_item:
            raise PlanningBundleValidationError(
                "tracker/checklist item mismatch at item "
                f"{index}: {tracker_item.text} != {checklist_item}"
            )
        for env in TRACKER_ENVS:
            if env not in tracker_item.environments:
                raise PlanningBundleValidationError(f"tracker item {index} missing environment: {env}")
            status = tracker_item.statuses.get(env)
            if status is None:
                raise PlanningBundleValidationError(
                    f"tracker item {index} missing status for environment: {env}"
                )
            if status not in TRACKER_STATUSES:
                raise PlanningBundleValidationError(
                    f"tracker item {index} invalid status for environment {env}: {status}"
                )


def _is_checkbox(line: str) -> bool:
    return line.strip().startswith(("- [ ] ", "- [x] ", "- [X] "))


def _checkbox_item_text(stripped_line: str) -> str:
    for prefix in ("- [ ] ", "- [x] ", "- [X] "):
        if stripped_line.startswith(prefix):
            return stripped_line.removeprefix(prefix).strip()
    raise PlanningBundleValidationError("unsupported tracker checklist format")


def _tracker_environment_heading(stripped_line: str) -> str | None:
    for env in TRACKER_ENVS:
        if stripped_line == f"- {env}:":
            return env
    return None


def _count_test_cases(test_cases_path: Path) -> int:
    with test_cases_path.open(newline="") as csv_file:
        return sum(1 for _ in csv.DictReader(csv_file))


def _validate_baseline_risks(risk_map_path: Path) -> None:
    risk_map = risk_map_path.read_text().lower()
    for risk in BASELINE_RISKS:
        if f"| {risk} |" not in risk_map:
            raise PlanningBundleValidationError(f"missing baseline risk: {risk}")
