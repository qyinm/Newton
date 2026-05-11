from __future__ import annotations

import csv
import json
import re
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from newton.planning_bundle_validation import PlanningBundleValidationError, validate_planning_bundle

AgentRun = Callable[..., subprocess.CompletedProcess[str]]


class BundleReviewError(RuntimeError):
    """Raised when a QA bundle advisory review cannot be produced."""


REVIEW_CATEGORIES = (
    "coverage",
    "source_grounding",
    "estimate_clarity",
    "risk_usefulness",
    "automation_suitability",
)
DEFAULT_GATE_THRESHOLD = 80


@dataclass(frozen=True)
class BundleReviewResult:
    agent: str
    score: int
    verdict: str
    category_scores: dict[str, int]
    review_json_path: Path
    review_markdown_path: Path
    prompt_path: Path | None = None
    raw_output_path: Path | None = None
    gate: bool = False
    gate_threshold: int | None = None
    gate_passed: bool | None = None


def review_planning_bundle(
    bundle_dir: Path,
    *,
    agent: str = "template",
    command: Sequence[str] | str | None = None,
    run: AgentRun = subprocess.run,
    gate: bool = False,
    gate_threshold: int = DEFAULT_GATE_THRESHOLD,
) -> BundleReviewResult:
    normalized_agent = agent.strip().lower()
    if normalized_agent not in {"template", "codex", "claude"}:
        raise BundleReviewError(f"unsupported bundle review agent: {agent}")
    if gate and (gate_threshold < 0 or gate_threshold > 100):
        raise BundleReviewError("gate threshold must be an integer from 0 to 100")

    try:
        validation = validate_planning_bundle(bundle_dir)
    except PlanningBundleValidationError as exc:
        raise BundleReviewError(f"bundle validation failed: {exc}") from exc

    if normalized_agent == "template":
        payload = _template_review_payload(bundle_dir)
        return _write_review_artifacts(
            bundle_dir,
            agent=normalized_agent,
            plan_id=validation.plan_id,
            payload=payload,
            gate=gate,
            gate_threshold=gate_threshold,
        )

    prompt = build_bundle_review_prompt(bundle_dir)
    prompt_path = bundle_dir / f"bundle-review.{normalized_agent}.prompt.txt"
    raw_output_path = bundle_dir / f"bundle-review.{normalized_agent}.raw.txt"
    prompt_path.write_text(prompt)
    argv, prompt_via_stdin = _agent_command(normalized_agent, command)

    try:
        completed = run(
            argv,
            input=prompt if prompt_via_stdin else None,
            text=True,
            capture_output=True,
            check=True,
        )
    except FileNotFoundError as exc:
        raise BundleReviewError(
            f"{normalized_agent} review command not found: {argv[0]}. Install/authenticate it or use --agent template."
        ) from exc
    except subprocess.CalledProcessError as exc:
        raw = (exc.stdout or "") + (exc.stderr or "")
        raw_output_path.write_text(raw)
        raise BundleReviewError(f"{normalized_agent} review command failed; raw output saved to {raw_output_path}") from exc

    raw_output_path.write_text(completed.stdout)
    try:
        payload = _validate_agent_review_payload(_extract_json(completed.stdout), agent=normalized_agent, bundle_dir=bundle_dir)
    except BundleReviewError as exc:
        raise BundleReviewError(
            f"agent review output did not validate: {exc}; raw output saved to {raw_output_path}"
        ) from exc

    return _write_review_artifacts(
        bundle_dir,
        agent=normalized_agent,
        plan_id=validation.plan_id,
        payload=payload,
        prompt_path=prompt_path,
        raw_output_path=raw_output_path,
        gate=gate,
        gate_threshold=gate_threshold,
    )


def build_bundle_review_prompt(bundle_dir: Path) -> str:
    artifact_sections = []
    for filename in [
        "qa-scope.md",
        "checklist.md",
        "test-cases.csv",
        "risk-map.md",
        "qa-estimate.md",
        "automation-candidates.md",
        "qa-run-tracker.md",
        "manifest.json",
    ]:
        path = bundle_dir / filename
        artifact_sections.append(f"## {filename}\n\n```\n{path.read_text()}\n```")

    artifacts = "\n\n".join(artifact_sections)
    categories = ", ".join(REVIEW_CATEGORIES)
    return f"""Review this Newton QA planning bundle as a senior QA reviewer.

Bundle path: {bundle_dir}

Score planning quality across these release-gate categories: {categories}.
Do not rewrite artifacts. Identify coverage, source-grounding, estimate, risk, and automation quality gaps.

Output only JSON with this exact shape:
{{
  "score": <integer 0-100>,
  "verdict": "advisory_pass" | "needs_improvement",
  "category_scores": {{
    "coverage": <integer 0-100>,
    "source_grounding": <integer 0-100>,
    "estimate_clarity": <integer 0-100>,
    "risk_usefulness": <integer 0-100>,
    "automation_suitability": <integer 0-100>
  }},
  "findings": [
    {{
      "severity": "low" | "medium" | "high",
      "artifact": "<artifact filename>",
      "finding": "<concise issue>",
      "suggestion": "<actionable suggestion>"
    }}
  ]
}}

Artifacts:

{artifacts}
"""


def _template_review_payload(bundle_dir: Path) -> dict[str, object]:
    quality = _score_planning_quality(bundle_dir)
    return {
        "agent": "template",
        "bundle_path": str(bundle_dir),
        "score": quality["score"],
        "verdict": "advisory_pass" if int(quality["score"]) >= DEFAULT_GATE_THRESHOLD else "needs_improvement",
        "category_scores": quality["category_scores"],
        "findings": quality["findings"],
    }


def _write_review_artifacts(
    bundle_dir: Path,
    *,
    agent: str,
    plan_id: str,
    payload: dict[str, object],
    prompt_path: Path | None = None,
    raw_output_path: Path | None = None,
    gate: bool = False,
    gate_threshold: int = DEFAULT_GATE_THRESHOLD,
) -> BundleReviewResult:
    normalized_payload = _validate_agent_review_payload(payload, agent=agent, bundle_dir=bundle_dir)
    gate_payload = _gate_payload(score=int(normalized_payload["score"]), gate=gate, gate_threshold=gate_threshold)
    normalized_payload["gate"] = gate_payload
    json_path = bundle_dir / f"bundle-review.{agent}.json"
    markdown_path = bundle_dir / f"bundle-review.{agent}.md"
    json_path.write_text(json.dumps(normalized_payload, indent=2) + "\n")
    markdown_path.write_text(_render_review_markdown(plan_id, normalized_payload))
    return BundleReviewResult(
        agent=agent,
        score=int(normalized_payload["score"]),
        verdict=str(normalized_payload["verdict"]),
        category_scores=dict(normalized_payload["category_scores"]),
        review_json_path=json_path,
        review_markdown_path=markdown_path,
        prompt_path=prompt_path,
        raw_output_path=raw_output_path,
        gate=gate,
        gate_threshold=gate_payload["threshold"],
        gate_passed=gate_payload["passed"],
    )


def _validate_agent_review_payload(payload: object, *, agent: str, bundle_dir: Path) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise BundleReviewError("review output must be a JSON object")
    score = payload.get("score")
    verdict = payload.get("verdict")
    category_scores = payload.get("category_scores")
    findings = payload.get("findings")
    if not isinstance(score, int) or score < 0 or score > 100:
        raise BundleReviewError("review score must be an integer from 0 to 100")
    if verdict not in {"advisory_pass", "needs_improvement"}:
        raise BundleReviewError("review verdict must be advisory_pass or needs_improvement")
    normalized_category_scores = _validate_category_scores(category_scores)
    if not isinstance(findings, list):
        raise BundleReviewError("review findings must be a list")

    normalized_findings: list[dict[str, str]] = []
    for finding in findings:
        if not isinstance(finding, dict):
            raise BundleReviewError("review finding must be an object")
        severity = finding.get("severity")
        artifact = finding.get("artifact")
        finding_text = finding.get("finding")
        suggestion = finding.get("suggestion")
        if severity not in {"low", "medium", "high"}:
            raise BundleReviewError("review finding severity must be low, medium, or high")
        if not all(isinstance(value, str) and value for value in [artifact, finding_text, suggestion]):
            raise BundleReviewError("review finding fields must be non-empty strings")
        normalized_findings.append(
            {
                "severity": severity,
                "artifact": artifact,
                "finding": finding_text,
                "suggestion": suggestion,
            }
        )

    return {
        "agent": agent,
        "bundle_path": str(bundle_dir),
        "score": score,
        "verdict": verdict,
        "category_scores": normalized_category_scores,
        "findings": normalized_findings,
    }


def _validate_category_scores(category_scores: object) -> dict[str, int]:
    if not isinstance(category_scores, dict):
        raise BundleReviewError("review category_scores must be an object")

    missing = [category for category in REVIEW_CATEGORIES if category not in category_scores]
    if missing:
        raise BundleReviewError("category_scores missing required categories: " + ", ".join(missing))

    unknown = sorted(str(category) for category in category_scores if category not in REVIEW_CATEGORIES)
    if unknown:
        raise BundleReviewError("category_scores contains unknown categories: " + ", ".join(unknown))

    normalized: dict[str, int] = {}
    for category in REVIEW_CATEGORIES:
        score = category_scores[category]
        if not isinstance(score, int) or score < 0 or score > 100:
            raise BundleReviewError(f"category_scores.{category} must be an integer from 0 to 100")
        normalized[category] = score
    return normalized


def _gate_payload(*, score: int, gate: bool, gate_threshold: int) -> dict[str, object]:
    if not gate:
        return {"enabled": False, "threshold": None, "passed": None}
    return {"enabled": True, "threshold": gate_threshold, "passed": score >= gate_threshold}


def _render_review_markdown(plan_id: str, payload: dict[str, object]) -> str:
    findings = payload["findings"]
    finding_lines = []
    for index, finding in enumerate(findings, start=1):
        assert isinstance(finding, dict)
        finding_lines.append(
            f"{index}. **{finding['severity']}** — `{finding['artifact']}`\n"
            f"   - Finding: {finding['finding']}\n"
            f"   - Suggestion: {finding['suggestion']}"
        )
    rendered_findings = "\n".join(finding_lines) if finding_lines else "No findings."
    category_scores = payload["category_scores"]
    assert isinstance(category_scores, dict)
    category_lines = ["| Category | Score |", "| --- | ---: |"]
    for category in REVIEW_CATEGORIES:
        category_lines.append(f"| {category} | {category_scores[category]} |")
    rendered_category_scores = "\n".join(category_lines)
    gate_payload = payload["gate"]
    assert isinstance(gate_payload, dict)
    mode = "release gate" if gate_payload["enabled"] else "advisory"
    intro = (
        "This is a release gate review. Deterministic `bundle-validate` remains the required structural contract check."
        if gate_payload["enabled"]
        else "This is an advisory review. Deterministic `bundle-validate` remains the required structural contract check."
    )
    gate_lines = ""
    if gate_payload["enabled"]:
        gate_result = "passed" if gate_payload["passed"] else "failed"
        gate_lines = f"- Gate threshold: {gate_payload['threshold']}\n- Gate result: {gate_result}\n"
    return f"""# QA Bundle Review: {plan_id}

{intro}

- Mode: {mode}
- Agent: {payload['agent']}
- Bundle: `{payload['bundle_path']}`
- Score: {payload['score']}
- Verdict: {payload['verdict']}
{gate_lines}
## Category Scores

{rendered_category_scores}

## Findings

{rendered_findings}
"""


def _score_planning_quality(bundle_dir: Path) -> dict[str, object]:
    checklist_items = _read_checklist_items(bundle_dir / "checklist.md")
    test_cases = _read_test_cases(bundle_dir / "test-cases.csv")
    risk_map = (bundle_dir / "risk-map.md").read_text()
    estimate = (bundle_dir / "qa-estimate.md").read_text()
    automation = (bundle_dir / "automation-candidates.md").read_text()
    manifest = json.loads((bundle_dir / "manifest.json").read_text())
    source_paths = [str(path) for path in manifest.get("source_paths", []) if isinstance(path, str)]

    category_scores = {
        "coverage": _coverage_score(checklist_items, test_cases),
        "source_grounding": _source_grounding_score(bundle_dir, test_cases, estimate, source_paths),
        "estimate_clarity": _estimate_clarity_score(estimate),
        "risk_usefulness": _risk_usefulness_score(risk_map),
        "automation_suitability": _automation_suitability_score(automation),
    }
    score = round(sum(category_scores.values()) / len(category_scores))
    return {
        "score": score,
        "category_scores": category_scores,
        "findings": _template_findings(category_scores),
    }


def _read_checklist_items(checklist_path: Path) -> list[str]:
    return [
        line.strip().removeprefix("- [ ] ").removeprefix("- [x] ").removeprefix("- [X] ").strip()
        for line in checklist_path.read_text().splitlines()
        if line.strip().startswith(("- [ ] ", "- [x] ", "- [X] "))
    ]


def _read_test_cases(test_cases_path: Path) -> list[dict[str, str]]:
    with test_cases_path.open(newline="") as csv_file:
        return [dict(row) for row in csv.DictReader(csv_file)]


def _coverage_score(checklist_items: list[str], test_cases: list[dict[str, str]]) -> int:
    score = 0
    if checklist_items and len(checklist_items) == len(test_cases):
        score += 40
    if test_cases and all(row.get("priority") in {"P0", "P1", "P2"} for row in test_cases):
        score += 20
    if test_cases and all(row.get("steps") and row.get("expected_result") for row in test_cases):
        score += 20
    if len(checklist_items) >= 5:
        score += 20
    return score


def _source_grounding_score(
    bundle_dir: Path,
    test_cases: list[dict[str, str]],
    estimate: str,
    source_paths: list[str],
) -> int:
    score = 0
    scope = (bundle_dir / "qa-scope.md").read_text()
    source_names = {Path(source_path).name for source_path in source_paths}
    source_needles = {*source_paths, *source_names}
    if source_paths:
        score += 25
    if "## Sources" in scope and any(needle in scope for needle in source_needles):
        score += 25
    if any(needle in estimate for needle in source_needles):
        score += 20
    if test_cases and all(row.get("source_reference") for row in test_cases):
        score += 10
    if test_cases and any(
        any(needle in str(row.get("source_reference", "")) for needle in source_needles) for row in test_cases
    ):
        score += 20
    return score


def _estimate_clarity_score(estimate: str) -> int:
    score = 0
    if "Estimated QA effort:" in estimate:
        score += 25
    if "## Evidence Factors" in estimate and "| Factor |" in estimate:
        score += 25
    if "## Suggested Manual QA Time" in estimate:
        score += 20
    if "## Assumptions" in estimate:
        score += 10
    if "Score band:" in estimate or "Total score:" in estimate:
        score += 10
    return score


def _risk_usefulness_score(risk_map: str) -> int:
    risk_map_lower = risk_map.lower()
    score = 0
    baseline_risks = [
        "functional",
        "edge case",
        "network failure",
        "permission/role",
        "policy conflict",
        "regression",
    ]
    if all(f"| {risk} |" in risk_map_lower for risk in baseline_risks):
        score += 30

    rows = [line for line in risk_map.splitlines() if line.startswith("| ") and " --- " not in line]
    body_rows = [row for row in rows if "| Area |" not in row]
    if "| P0 |" in risk_map and "| P1 |" in risk_map:
        score += 20
    if any(len(_table_cell(row, 2)) >= 30 for row in body_rows):
        score += 20
    if any(_table_cell(row, 3) for row in body_rows):
        score += 10
    if len(body_rows) > len(baseline_risks):
        score += 20
    return score


def _automation_suitability_score(automation: str) -> int:
    score = 0
    if "## Recommended" in automation:
        score += 25
    if "Suggested automation:" in automation:
        score += 25
    if "## Manual For Now" in automation:
        score += 20
    if "Reason:" in automation:
        score += 10

    recommended_section = automation.split("## Manual For Now", maxsplit=1)[0]
    recommended_items = [line for line in recommended_section.splitlines() if line.startswith("- ")]
    if len(recommended_items) >= 2:
        score += 20
    return score


def _table_cell(row: str, index: int) -> str:
    cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
    if index >= len(cells):
        return ""
    return cells[index]


def _template_findings(category_scores: dict[str, int]) -> list[dict[str, str]]:
    findings = []
    for category in REVIEW_CATEGORIES:
        score = category_scores[category]
        if score >= 100:
            continue
        findings.append(_category_finding(category, score))
    return findings or [
        {
            "severity": "low",
            "artifact": "manifest.json",
            "finding": "Planning quality rubric found no deterministic gaps.",
            "suggestion": "Use --agent codex or --agent claude when semantic review is needed before release.",
        }
    ]


def _category_finding(category: str, score: int) -> dict[str, str]:
    severity = "high" if score < 60 else "medium" if score < 80 else "low"
    artifact_by_category = {
        "coverage": "test-cases.csv",
        "source_grounding": "manifest.json",
        "estimate_clarity": "qa-estimate.md",
        "risk_usefulness": "risk-map.md",
        "automation_suitability": "automation-candidates.md",
    }
    suggestion_by_category = {
        "coverage": "Add missing checklist, test case, priority, step, or expected-result detail.",
        "source_grounding": "Cite the original source files directly in source references and evidence fields.",
        "estimate_clarity": "Include effort size, evidence factors, manual QA time, assumptions, and score-band rationale.",
        "risk_usefulness": "Keep baseline risks while adding source-specific priorities, rationale, and evidence.",
        "automation_suitability": "Separate recommended automation from manual coverage with priority and reason fields.",
    }
    return {
        "severity": severity,
        "artifact": artifact_by_category[category],
        "finding": f"{category} scored {score}/100 in the deterministic planning quality rubric.",
        "suggestion": suggestion_by_category[category],
    }


def _agent_command(agent: str, command: Sequence[str] | str | None) -> tuple[list[str], bool]:
    if command is not None:
        if isinstance(command, str):
            return shlex.split(command), True
        return list(command), True
    if agent == "codex":
        return ["codex", "exec", "--sandbox", "read-only", "-"], True
    if agent == "claude":
        return ["claude", "-p", "--tools", ""], True
    raise BundleReviewError(f"unsupported bundle review agent: {agent}")


def _extract_json(output: str) -> object:
    fenced = re.search(r"```(?:json)?\s*(.*?)```", output, flags=re.DOTALL | re.IGNORECASE)
    raw_json = fenced.group(1).strip() if fenced else output.strip()
    try:
        return json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise BundleReviewError(f"invalid review JSON: {exc.msg}") from exc
