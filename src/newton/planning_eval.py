from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from newton.planning_bundle import PlanningBundleError, generate_planning_bundle
from newton.planning_bundle_validation import PlanningBundleValidationError, validate_planning_bundle


class PlanningEvalError(ValueError):
    """Raised when a planning eval cannot be loaded or executed."""


@dataclass(frozen=True)
class PlanningEvalRun:
    report_json_path: Path
    report_markdown_path: Path
    passed: bool
    score: int
    case_count: int


def evaluate_planning_cases(cases_root: Path, out_dir: Path, *, min_score: int = 80) -> PlanningEvalRun:
    case_dirs = _discover_case_dirs(cases_root)
    out_dir.mkdir(parents=True, exist_ok=True)

    case_results = []
    for case_dir in case_dirs:
        case_results.append(_evaluate_case(case_dir, out_dir=out_dir, min_score=min_score))

    score = round(sum(case["score"] for case in case_results) / len(case_results))
    passed = all(case["passed"] for case in case_results) and score >= min_score
    summary: dict[str, Any] = {
        "score": score,
        "min_score": min_score,
        "passed": passed,
        "case_count": len(case_results),
        "cases": case_results,
    }

    report_json_path = out_dir / "planning-eval-report.json"
    report_markdown_path = out_dir / "planning-eval-report.md"
    report_json_path.write_text(json.dumps(summary, indent=2) + "\n")
    report_markdown_path.write_text(_render_markdown_report(summary))
    return PlanningEvalRun(
        report_json_path=report_json_path,
        report_markdown_path=report_markdown_path,
        passed=passed,
        score=score,
        case_count=len(case_results),
    )


def _discover_case_dirs(cases_root: Path) -> list[Path]:
    if not cases_root.exists():
        raise PlanningEvalError(f"planning eval cases path not found: {cases_root}")
    if (cases_root / "expected.json").exists():
        return [cases_root]

    case_dirs = sorted(path for path in cases_root.iterdir() if (path / "expected.json").exists())
    if not case_dirs:
        raise PlanningEvalError(f"no planning eval cases found under: {cases_root}")
    return case_dirs


def _evaluate_case(case_dir: Path, *, out_dir: Path, min_score: int) -> dict[str, Any]:
    expected = _load_expected(case_dir / "expected.json")
    case_id = str(expected.get("id") or case_dir.name)
    input_path = case_dir / str(expected.get("input", "input.md"))
    if not input_path.exists():
        raise PlanningEvalError(f"planning eval case {case_id!r} missing input markdown: {input_path}")

    source_paths = _case_source_paths(case_dir, expected)
    case_out_dir = out_dir / case_id
    try:
        bundle_dir = generate_planning_bundle(
            input_path,
            out_dir=case_out_dir,
            source_paths=source_paths,
            bundle_dir_name="bundle",
        )
        validate_planning_bundle(bundle_dir)
        validation_error = None
    except (PlanningBundleError, PlanningBundleValidationError) as exc:
        bundle_dir = case_out_dir / "bundle"
        validation_error = str(exc)

    checks = _evaluate_bundle_checks(bundle_dir, expected, validation_error=validation_error)
    score = round(100 * sum(1 for check in checks if check["passed"]) / len(checks))
    case_min_score = int(expected.get("min_score", min_score))
    passed = score >= case_min_score and all(check["passed"] for check in checks)
    return {
        "id": case_id,
        "description": expected.get("description", ""),
        "score": score,
        "min_score": case_min_score,
        "passed": passed,
        "bundle_dir": str(bundle_dir),
        "checks": checks,
    }


def _load_expected(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text())
    except FileNotFoundError as exc:
        raise PlanningEvalError(f"planning eval expected file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise PlanningEvalError(f"invalid planning eval expected JSON at {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise PlanningEvalError(f"planning eval expected JSON must be an object: {path}")
    return payload


def _case_source_paths(case_dir: Path, expected: dict[str, Any]) -> list[Path]:
    configured_sources = expected.get("sources")
    if configured_sources is not None:
        if not isinstance(configured_sources, list) or not all(
            isinstance(source, str) for source in configured_sources
        ):
            raise PlanningEvalError("planning eval 'sources' must be a list of strings")
        return [case_dir / source for source in configured_sources]

    sources_dir = case_dir / "sources"
    if not sources_dir.exists():
        return []
    return sorted(sources_dir.glob("*.md"))


def _evaluate_bundle_checks(
    bundle_dir: Path,
    expected: dict[str, Any],
    *,
    validation_error: str | None,
) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    checks.append(
        {
            "name": "bundle_valid",
            "passed": validation_error is None,
            "details": {"error": validation_error},
        }
    )
    if validation_error is not None:
        return checks

    bundle_text = _combined_bundle_text(bundle_dir)
    checklist_text = (bundle_dir / "checklist.md").read_text()
    risk_map = (bundle_dir / "risk-map.md").read_text()
    estimate = (bundle_dir / "qa-estimate.md").read_text()

    min_checklist_items = int(expected.get("min_checklist_items", 0))
    if min_checklist_items:
        checklist_count = len(re.findall(r"^- \[[ xX]\] ", checklist_text, flags=re.MULTILINE))
        checks.append(
            {
                "name": "min_checklist_items",
                "passed": checklist_count >= min_checklist_items,
                "details": {"actual": checklist_count, "expected_min": min_checklist_items},
            }
        )

    required_terms = _string_list(expected, "required_terms")
    if required_terms:
        missing_terms = [term for term in required_terms if term.casefold() not in bundle_text.casefold()]
        checks.append(
            {
                "name": "required_terms",
                "passed": not missing_terms,
                "details": {"missing": missing_terms, "expected": required_terms},
            }
        )

    required_risks = _string_list(expected, "required_risk_categories")
    if required_risks:
        risk_categories = _risk_categories(risk_map)
        missing_risks = [risk for risk in required_risks if risk.casefold() not in risk_categories]
        checks.append(
            {
                "name": "required_risk_categories",
                "passed": not missing_risks,
                "details": {
                    "actual": sorted(risk_categories),
                    "missing": missing_risks,
                    "expected": required_risks,
                },
            }
        )

    allowed_estimate_sizes = _string_list(expected, "allowed_estimate_sizes")
    if allowed_estimate_sizes:
        estimate_size = _estimate_size(estimate)
        allowed = {size.casefold() for size in allowed_estimate_sizes}
        checks.append(
            {
                "name": "allowed_estimate_size",
                "passed": estimate_size.casefold() in allowed,
                "details": {"actual": estimate_size, "allowed": allowed_estimate_sizes},
            }
        )

    min_source_refs = int(expected.get("min_source_references", 0))
    if min_source_refs:
        source_refs = _source_references(bundle_text)
        checks.append(
            {
                "name": "min_source_references",
                "passed": len(source_refs) >= min_source_refs,
                "details": {"actual": len(source_refs), "expected_min": min_source_refs},
            }
        )

    return checks


def _string_list(expected: dict[str, Any], key: str) -> list[str]:
    value = expected.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise PlanningEvalError(f"planning eval {key!r} must be a list of strings")
    return value


def _combined_bundle_text(bundle_dir: Path) -> str:
    artifact_names = (
        "qa-scope.md",
        "checklist.md",
        "test-cases.csv",
        "risk-map.md",
        "qa-estimate.md",
        "automation-candidates.md",
        "qa-run-tracker.md",
        "manifest.json",
    )
    return "\n".join((bundle_dir / name).read_text() for name in artifact_names)


def _risk_categories(risk_map: str) -> set[str]:
    categories = set()
    for line in risk_map.splitlines():
        match = re.match(r"^\|\s*([^|]+?)\s*\|", line)
        if not match:
            continue
        category = match.group(1).strip()
        if category and category not in {"Area", "---"}:
            categories.add(category.casefold())
    return categories


def _estimate_size(estimate: str) -> str:
    match = re.search(r"Estimated QA effort:\s*([A-Z])\b", estimate)
    return match.group(1) if match else ""


def _source_references(bundle_text: str) -> set[str]:
    return {match.group(1) for match in re.finditer(r"`([^`]+#[^`]+)`", bundle_text)}


def _render_markdown_report(summary: dict[str, Any]) -> str:
    lines = [
        "# Planning Eval Report",
        "",
        f"Score: {summary['score']}",
        f"Minimum score: {summary['min_score']}",
        f"Passed: {'yes' if summary['passed'] else 'no'}",
        "",
        "| Case | Score | Min | Passed | Bundle |",
        "| --- | ---: | ---: | --- | --- |",
    ]
    for case in summary["cases"]:
        lines.append(
            f"| {case['id']} | {case['score']} | {case['min_score']} | "
            f"{'yes' if case['passed'] else 'no'} | `{case['bundle_dir']}` |"
        )
    lines.append("")
    for case in summary["cases"]:
        lines.extend([f"## {case['id']}", ""])
        if case.get("description"):
            lines.extend([str(case["description"]), ""])
        for check in case["checks"]:
            lines.append(f"- [{'x' if check['passed'] else ' '}] {check['name']}: `{check['details']}`")
        lines.append("")
    return "\n".join(lines)
