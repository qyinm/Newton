from __future__ import annotations

import csv
import io
import json
import re
import shlex
import subprocess
from pathlib import Path
from typing import Callable, Sequence

from newton.planning_bundle import _extract_title, _slugify
from newton.models import ARTIFACT_CONTRACT_VERSION
from newton.planning_bundle_validation import PlanningBundleValidationError, validate_planning_bundle

AgentRun = Callable[..., subprocess.CompletedProcess[str]]


class AgentPlanningBundleError(RuntimeError):
    """Raised when an agent-backed planning bundle cannot be generated."""


def generate_planning_bundle_with_agent(
    input_path: Path,
    *,
    out_dir: Path,
    source_paths: list[Path] | None = None,
    agent: str,
    command: Sequence[str] | str | None = None,
    run: AgentRun = subprocess.run,
) -> Path:
    normalized_agent = agent.strip().lower()
    if normalized_agent not in {"codex", "claude"}:
        raise AgentPlanningBundleError(f"unsupported planning bundle agent: {agent}")

    all_source_paths = [input_path, *(source_paths or [])]
    markdown_by_path = _read_sources(all_source_paths)
    plan_id = _slugify(_extract_title(markdown_by_path[0][1]))
    bundle_dir = out_dir / plan_id
    bundle_dir.mkdir(parents=True, exist_ok=True)

    prompt = build_planning_bundle_prompt(markdown_by_path, expected_plan_id=plan_id)
    prompt_path = bundle_dir / f"bundle-generation.{normalized_agent}.prompt.txt"
    raw_output_path = bundle_dir / f"bundle-generation.{normalized_agent}.raw.txt"
    accepted_json_path = bundle_dir / f"bundle-generation.{normalized_agent}.json"
    prompt_path.write_text(prompt)

    codex_last_message_path = (
        bundle_dir / f"bundle-generation.{normalized_agent}.last-message.txt"
        if normalized_agent == "codex" and command is None
        else None
    )
    argv, prompt_via_stdin = _agent_command(normalized_agent, command, codex_last_message_path)
    try:
        completed = run(
            argv,
            input=prompt if prompt_via_stdin else None,
            text=True,
            capture_output=True,
            check=True,
        )
    except FileNotFoundError as exc:
        raise AgentPlanningBundleError(
            f"{normalized_agent} planning bundle command not found: {argv[0]}. Install/authenticate it or use --agent template."
        ) from exc
    except subprocess.CalledProcessError as exc:
        raw = (exc.stdout or "") + (exc.stderr or "")
        raw_output_path.write_text(raw)
        raise AgentPlanningBundleError(
            f"{normalized_agent} planning bundle command failed; raw output saved to {raw_output_path}"
        ) from exc

    raw_output = (completed.stdout or "") + (completed.stderr or "")
    raw_output_path.write_text(raw_output)
    parse_output = (
        codex_last_message_path.read_text()
        if codex_last_message_path is not None and codex_last_message_path.exists()
        else completed.stdout
    )
    try:
        payload = _validate_agent_bundle_payload(
            _extract_json(parse_output), expected_plan_id=plan_id, source_paths=all_source_paths
        )
    except AgentPlanningBundleError as exc:
        raise AgentPlanningBundleError(
            f"agent planning bundle output did not validate; raw output saved to {raw_output_path}: {exc}"
        ) from exc

    _write_bundle_artifacts(
        bundle_dir=bundle_dir,
        input_path=input_path,
        source_paths=all_source_paths,
        agent=normalized_agent,
        prompt_path=prompt_path,
        raw_output_path=raw_output_path,
        accepted_json_path=accepted_json_path,
        payload=payload,
    )
    accepted_json_path.write_text(json.dumps(payload, indent=2) + "\n")

    try:
        validate_planning_bundle(bundle_dir)
    except PlanningBundleValidationError as exc:
        raise AgentPlanningBundleError(f"agent planning bundle failed structural validation: {exc}") from exc

    return bundle_dir


def build_planning_bundle_prompt(markdown_by_path: list[tuple[Path, str]], *, expected_plan_id: str) -> str:
    sources = "\n\n".join(
        f"## Source: {path}\n\n```markdown\n{markdown}\n```" for path, markdown in markdown_by_path
    )
    return f"""Generate a Newton QA planning bundle from the provided sprint/product context.

You are the QA planning agent. Newton will validate and materialize your output; do not write files.

Output only JSON with this exact high-level shape:
{{
  "plan_id": "lowercase-dash-id",
  "title": "Human title",
  "qa_scope": {{
    "goal": "one sentence",
    "in_scope": ["..."],
    "out_of_scope": ["..."]
  }},
  "checklist": [
    {{"title": "...", "risk_category": "functional", "priority": "P0", "source_reference": "..."}}
  ],
  "test_cases": [
    {{"id": "TC-001", "title": "...", "priority": "P0", "precondition": "...", "steps": "...", "expected_result": "...", "environment": "dev/stg/prod", "risk_category": "functional", "source_reference": "..."}}
  ],
  "risk_map": [
    {{"area": "functional", "priority": "P0", "rationale": "..."}}
  ],
  "qa_estimate": {{
    "size": "S|M|L",
    "reasoning": ["..."],
    "manual_qa_time": ["..."],
    "assumptions": ["..."],
    "evidence_factors": [
      {{"factor": "screens|policy_rules|roles|states|environments|integrations|regression|data_setup|retest_count|checklist_items", "value": "...", "evidence": "...", "source_reference": "provided source path or filename"}}
    ]
  }},
  "automation_candidates": [
    {{"title": "...", "recommendation": "Recommended|Manual For Now", "reason": "..."}}
  ]
}}

Rules:
- Set "plan_id" to exactly "{expected_plan_id}".
- Keep checklist and test_cases counts equal.
- Include risk_map rows for at least: functional, edge case, network failure, permission/role, policy conflict, regression.
- qa_estimate.evidence_factors must cite provided source paths or filenames in source_reference.
- Use evidence_factors for concrete estimate drivers: screens, policy rules, roles, states, environments, integrations, regression, data setup, and retest count.
- Do not include markdown fences around the JSON.

Sources:

{sources}
"""


def _read_sources(paths: list[Path]) -> list[tuple[Path, str]]:
    sources: list[tuple[Path, str]] = []
    for path in paths:
        if not path.exists():
            raise AgentPlanningBundleError(f"input markdown not found: {path}")
        sources.append((path, path.read_text()))
    return sources


def _agent_command(
    agent: str,
    command: Sequence[str] | str | None,
    codex_last_message_path: Path | None = None,
) -> tuple[list[str], bool]:
    if command is not None:
        if isinstance(command, str):
            return shlex.split(command), True
        return list(command), True
    if agent == "codex":
        argv = ["codex", "exec", "--sandbox", "read-only"]
        if codex_last_message_path is not None:
            argv.extend(["--output-last-message", str(codex_last_message_path)])
        argv.append("-")
        return argv, True
    if agent == "claude":
        return ["claude", "-p", "--tools", ""], True
    raise AgentPlanningBundleError(f"unsupported planning bundle agent: {agent}")


def _extract_json(output: str) -> object:
    fenced = re.search(r"```(?:json)?\s*(.*?)```", output, flags=re.DOTALL | re.IGNORECASE)
    raw_json = fenced.group(1).strip() if fenced else output.strip()
    try:
        return json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise AgentPlanningBundleError(f"invalid planning bundle JSON: {exc.msg}") from exc


def _validate_agent_bundle_payload(
    payload: object, *, expected_plan_id: str, source_paths: list[Path]
) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise AgentPlanningBundleError("planning bundle output must be a JSON object")
    plan_id = _required_str(payload, "plan_id")
    if plan_id != expected_plan_id:
        raise AgentPlanningBundleError(f"plan_id must be {expected_plan_id}")
    _required_str(payload, "title")
    _validate_scope(payload.get("qa_scope"))
    checklist = _required_list(payload, "checklist")
    test_cases = _required_list(payload, "test_cases")
    risk_map = _required_list(payload, "risk_map")
    _validate_estimate(payload.get("qa_estimate"), source_paths=source_paths)
    automation_candidates = _required_list(payload, "automation_candidates")
    if len(checklist) != len(test_cases):
        raise AgentPlanningBundleError("checklist and test_cases counts must match")
    for item in checklist:
        _validate_object_fields(item, ["title", "risk_category", "priority", "source_reference"], "checklist item")
    for item in test_cases:
        _validate_object_fields(
            item,
            [
                "id",
                "title",
                "priority",
                "precondition",
                "steps",
                "expected_result",
                "environment",
                "risk_category",
                "source_reference",
            ],
            "test case",
        )
    for item in risk_map:
        _validate_object_fields(item, ["area", "priority", "rationale"], "risk map item")
    for item in automation_candidates:
        _validate_object_fields(item, ["title", "recommendation", "reason"], "automation candidate")
    return payload


def _validate_scope(scope: object) -> None:
    if not isinstance(scope, dict):
        raise AgentPlanningBundleError("qa_scope must be an object")
    _required_str(scope, "goal")
    for key in ["in_scope", "out_of_scope"]:
        values = scope.get(key)
        if not isinstance(values, list) or not all(isinstance(value, str) and value for value in values):
            raise AgentPlanningBundleError(f"qa_scope.{key} must be a list of non-empty strings")


def _validate_estimate(estimate: object, *, source_paths: list[Path]) -> None:
    if not isinstance(estimate, dict):
        raise AgentPlanningBundleError("qa_estimate must be an object")
    _required_str(estimate, "size")
    for key in ["reasoning", "manual_qa_time", "assumptions"]:
        values = estimate.get(key)
        if not isinstance(values, list) or not all(isinstance(value, str) and value for value in values):
            raise AgentPlanningBundleError(f"qa_estimate.{key} must be a list of non-empty strings")
    evidence_factors = estimate.get("evidence_factors")
    if not isinstance(evidence_factors, list) or not evidence_factors:
        raise AgentPlanningBundleError("qa_estimate.evidence_factors must be a non-empty list")
    for index, factor in enumerate(evidence_factors, start=1):
        label = f"qa_estimate.evidence_factors[{index}]"
        _validate_object_fields(factor, ["factor", "value", "evidence", "source_reference"], label)
        assert isinstance(factor, dict)
        source_reference = str(factor["source_reference"])
        if not _source_reference_matches(source_reference, source_paths):
            raise AgentPlanningBundleError(
                f"{label}.source_reference must cite one of the provided source paths or filenames"
            )


def _source_reference_matches(source_reference: str, source_paths: list[Path]) -> bool:
    return any(str(path) in source_reference or path.name in source_reference for path in source_paths)


def _required_str(payload: dict[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise AgentPlanningBundleError(f"{key} must be a non-empty string")
    return value


def _required_list(payload: dict[str, object], key: str) -> list[object]:
    value = payload.get(key)
    if not isinstance(value, list) or not value:
        raise AgentPlanningBundleError(f"{key} must be a non-empty list")
    return value


def _validate_object_fields(value: object, fields: list[str], label: str) -> None:
    if not isinstance(value, dict):
        raise AgentPlanningBundleError(f"{label} must be an object")
    for field in fields:
        if not isinstance(value.get(field), str) or not value.get(field):
            raise AgentPlanningBundleError(f"{label}.{field} must be a non-empty string")


def _write_bundle_artifacts(
    *,
    bundle_dir: Path,
    input_path: Path,
    source_paths: list[Path],
    agent: str,
    prompt_path: Path,
    raw_output_path: Path,
    accepted_json_path: Path,
    payload: dict[str, object],
) -> None:
    title = str(payload["title"])
    plan_id = str(payload["plan_id"])
    checklist = payload["checklist"]
    assert isinstance(checklist, list)
    test_cases = payload["test_cases"]
    assert isinstance(test_cases, list)
    risk_map = payload["risk_map"]
    assert isinstance(risk_map, list)
    estimate = payload["qa_estimate"]
    assert isinstance(estimate, dict)
    automation_candidates = payload["automation_candidates"]
    assert isinstance(automation_candidates, list)

    paths = {
        "qa_scope": bundle_dir / "qa-scope.md",
        "checklist": bundle_dir / "checklist.md",
        "test_cases": bundle_dir / "test-cases.csv",
        "risk_map": bundle_dir / "risk-map.md",
        "qa_estimate": bundle_dir / "qa-estimate.md",
        "automation_candidates": bundle_dir / "automation-candidates.md",
        "qa_run_tracker": bundle_dir / "qa-run-tracker.md",
    }
    paths["qa_scope"].write_text(_render_scope(title, payload["qa_scope"], source_paths))
    paths["checklist"].write_text(_render_checklist(title, checklist))
    paths["test_cases"].write_text(_render_test_cases_csv(test_cases))
    paths["risk_map"].write_text(_render_risk_map(title, risk_map))
    paths["qa_estimate"].write_text(_render_estimate(title, estimate))
    paths["automation_candidates"].write_text(_render_automation_candidates(title, automation_candidates))
    paths["qa_run_tracker"].write_text(_render_run_tracker(title, checklist))
    (bundle_dir / "manifest.json").write_text(
        json.dumps(
            {
                "contract_version": ARTIFACT_CONTRACT_VERSION,
                "plan_id": plan_id,
                "input_path": str(input_path),
                "source_paths": [str(source_path) for source_path in source_paths],
                "agent": agent,
                "generation": {
                    "prompt_path": str(prompt_path),
                    "raw_output_path": str(raw_output_path),
                    "accepted_json_path": str(accepted_json_path),
                    "validation_status": "accepted",
                },
                "artifacts": {key: str(path) for key, path in paths.items()},
            },
            indent=2,
        )
        + "\n"
    )


def _render_scope(title: str, scope: object, source_paths: list[Path]) -> str:
    assert isinstance(scope, dict)
    sources = "\n".join(f"- `{source_path}`" for source_path in source_paths)
    in_scope = "\n".join(f"- {item}" for item in scope["in_scope"])
    out_of_scope = "\n".join(f"- {item}" for item in scope["out_of_scope"])
    return f"""# QA Scope: {title}

## Sources

{sources}

## Goal

{scope['goal']}

## In Scope

{in_scope}

## Out of Scope

{out_of_scope}
"""


def _render_checklist(title: str, checklist: list[object]) -> str:
    lines = []
    for item in checklist:
        assert isinstance(item, dict)
        lines.append(f"- [ ] {item['title']}")
    return f"""# QA Checklist: {title}

{chr(10).join(lines)}
"""


def _render_test_cases_csv(test_cases: list[object]) -> str:
    output = io.StringIO()
    fieldnames = [
        "ID",
        "title",
        "priority",
        "precondition",
        "steps",
        "expected_result",
        "environment",
        "risk_category",
        "source_reference",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for test_case in test_cases:
        assert isinstance(test_case, dict)
        writer.writerow(
            {
                "ID": test_case["id"],
                "title": test_case["title"],
                "priority": test_case["priority"],
                "precondition": test_case["precondition"],
                "steps": test_case["steps"],
                "expected_result": test_case["expected_result"],
                "environment": test_case["environment"],
                "risk_category": test_case["risk_category"],
                "source_reference": test_case["source_reference"],
            }
        )
    return output.getvalue()


def _render_risk_map(title: str, risk_map: list[object]) -> str:
    rows = []
    for risk in risk_map:
        assert isinstance(risk, dict)
        rows.append(f"| {risk['area']} | {risk['priority']} | {risk['rationale']} |")
    return f"""# Risk Map: {title}

| Area | Priority | Rationale |
| --- | --- | --- |
{chr(10).join(rows)}

Source: agent-generated planning bundle
"""


def _render_estimate(title: str, estimate: dict[str, object]) -> str:
    reasoning = "\n".join(f"- {item}" for item in estimate["reasoning"])
    manual_qa_time = "\n".join(f"- {item}" for item in estimate["manual_qa_time"])
    assumptions = "\n".join(f"- {item}" for item in estimate["assumptions"])
    evidence_rows = []
    for factor in estimate["evidence_factors"]:
        assert isinstance(factor, dict)
        evidence_rows.append(
            "| {factor} | {value} | {evidence} | {source} |".format(
                factor=_escape_table_cell(str(factor["factor"])),
                value=_escape_table_cell(str(factor["value"])),
                evidence=_escape_table_cell(str(factor["evidence"])),
                source=_escape_table_cell(str(factor["source_reference"])),
            )
        )
    return f"""# QA Estimate: {title}

## Summary

Estimated QA effort: {estimate['size']}

## Reasoning

{reasoning}

## Evidence Factors

| Factor | Value | Evidence | Source |
| --- | --- | --- | --- |
{chr(10).join(evidence_rows)}

## Suggested Manual QA Time

{manual_qa_time}

## Assumptions

{assumptions}
"""


def _escape_table_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _render_automation_candidates(title: str, candidates: list[object]) -> str:
    recommended: list[str] = []
    manual: list[str] = []
    for index, candidate in enumerate(candidates, start=1):
        assert isinstance(candidate, dict)
        rendered = f"- {candidate['title']}\n  - Source: checklist item {index}\n  - Recommendation: {candidate['recommendation']}\n  - Reason: {candidate['reason']}"
        if candidate["recommendation"] == "Recommended":
            recommended.append(rendered)
        else:
            manual.append(rendered)
    return f"""# Automation Candidates: {title}

## Recommended

{chr(10).join(recommended) if recommended else '- No recommended automation candidates.'}

## Manual For Now

{chr(10).join(manual) if manual else '- No manual-only candidates.'}
"""


def _render_run_tracker(title: str, checklist: list[object]) -> str:
    status_lines = []
    for item in checklist:
        assert isinstance(item, dict)
        status_lines.append(f"- [ ] {item['title']}\n  - env: dev\n  - status: not run\n  - notes:")
    return f"""# QA Run Tracker: {title}

## Environment Status

- dev: not run
- stg: not run
- prod: not run

## Checklist Status

{chr(10).join(status_lines)}
"""
