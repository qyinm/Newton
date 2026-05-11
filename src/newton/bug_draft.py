from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any


class BugDraftError(ValueError):
    """Raised when a tracker cannot produce a bug ticket draft."""


@dataclass(frozen=True)
class FailedTrackerItem:
    item: str
    env: str
    status: str
    notes: str
    tracker_title: str


@dataclass(frozen=True)
class RunReference:
    run_id: str
    report_path: str | None
    result_path: str | None
    evidence_paths: tuple[str, ...]


@dataclass(frozen=True)
class BugTicketDraft:
    title: str
    severity: str
    priority: str
    environment: str
    failed_step: str
    suspected_owner_area: str
    item: FailedTrackerItem
    reproduction_steps: tuple[str, ...]
    expected_result: str
    actual_result: str
    source_references: tuple[tuple[str, str], ...]
    evidence_paths: tuple[str, ...]


VALID_OUTPUT_FORMATS = {"markdown", "linear", "jira"}


def write_bug_ticket_draft(
    tracker_path: Path,
    output_path: Path | None = None,
    *,
    output_format: str = "markdown",
) -> Path:
    if not tracker_path.exists():
        raise BugDraftError(f"qa run tracker not found: {tracker_path}")
    normalized_format = output_format.strip().lower()
    if normalized_format not in VALID_OUTPUT_FORMATS:
        raise BugDraftError(f"unsupported bug draft format: {output_format}")

    failed_item = _first_failed_tracker_item(tracker_path.read_text())
    if failed_item is None:
        raise BugDraftError("no failed tracker item found")

    output_path = output_path or tracker_path.parent / "bug-ticket-draft.md"
    draft = _build_bug_ticket_draft(failed_item, tracker_path)
    output_path.write_text(_render_bug_ticket_draft(draft, normalized_format))
    return output_path


def _first_failed_tracker_item(markdown: str) -> FailedTrackerItem | None:
    current_item: str | None = None
    current_env = "dev"
    current_envs: dict[str, dict[str, str]] = {"dev": {"status": "not run", "notes": ""}}
    tracker_title = _tracker_title(markdown)

    def flush() -> FailedTrackerItem | None:
        if current_item is None:
            return None
        for env, state in current_envs.items():
            if state["status"].strip().lower() == "failed":
                return FailedTrackerItem(
                    item=current_item,
                    env=env.strip() or "dev",
                    status="failed",
                    notes=state["notes"].strip(),
                    tracker_title=tracker_title,
                )
        return None

    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith(("- [ ] ", "- [x] ", "- [X] ")):
            failed = flush()
            if failed is not None:
                return failed
            current_item = _tracker_item_text(stripped)
            current_env = "dev"
            current_envs = {"dev": {"status": "not run", "notes": ""}}
            continue
        if current_item is None:
            continue
        env_heading = _environment_heading(stripped)
        if env_heading is not None:
            current_env = env_heading
            current_envs.setdefault(current_env, {"status": "not run", "notes": ""})
            continue
        if stripped.startswith("- env:"):
            current_env = stripped.removeprefix("- env:").strip()
            current_envs.setdefault(current_env, {"status": "not run", "notes": ""})
        elif stripped.startswith("- status:"):
            current_envs.setdefault(current_env, {"status": "not run", "notes": ""})["status"] = (
                stripped.removeprefix("- status:").strip()
            )
        elif stripped.startswith("- notes:"):
            current_envs.setdefault(current_env, {"status": "not run", "notes": ""})["notes"] = (
                stripped.removeprefix("- notes:").strip()
            )

    return flush()


def _tracker_title(markdown: str) -> str:
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("# QA Run Tracker:"):
            return stripped.removeprefix("# QA Run Tracker:").strip() or "QA"
    return "QA"


def _environment_heading(stripped: str) -> str | None:
    for env in ("dev", "stg", "prod"):
        if stripped == f"- {env}:":
            return env
    return None


def _tracker_item_text(stripped_line: str) -> str:
    for prefix in ("- [ ] ", "- [x] ", "- [X] "):
        if stripped_line.startswith(prefix):
            return stripped_line.removeprefix(prefix).strip()
    return stripped_line


def _build_bug_ticket_draft(item: FailedTrackerItem, tracker_path: Path) -> BugTicketDraft:
    run_reference = _latest_run_reference(item)
    run_result = _load_run_result(run_reference, tracker_path) if run_reference else None
    if run_result is not None and run_reference is not None:
        return _build_run_derived_draft(item, tracker_path, run_reference, run_result)
    return _build_manual_draft(item, tracker_path)


def _build_manual_draft(item: FailedTrackerItem, tracker_path: Path) -> BugTicketDraft:
    notes = item.notes or "TBD"
    title = f"[{item.env}] {item.item}"
    owner_area = f"QA triage / {item.tracker_title} flow"
    return BugTicketDraft(
        title=title,
        severity="S2 - Major",
        priority="P1",
        environment=item.env,
        failed_step=item.item,
        suspected_owner_area=owner_area,
        item=item,
        reproduction_steps=(
            f"Open the {item.env} environment under test.",
            f"Execute the failed checklist item: {item.item}",
            "Record the actual result and attach evidence if available.",
        ),
        expected_result=f"The tracker item should pass: {item.item}.",
        actual_result=notes,
        source_references=(("Tracker", str(tracker_path)),),
        evidence_paths=(),
    )


def _build_run_derived_draft(
    item: FailedTrackerItem,
    tracker_path: Path,
    run_reference: RunReference,
    result: dict[str, Any],
) -> BugTicketDraft:
    scenario_id = str(result.get("scenario_id") or run_reference.run_id)
    platform = str(result.get("platform") or "unknown")
    title = f"[{item.env}] {scenario_id} failed on {platform}"
    failed_step = _first_failed_step(result)
    failed_step_label = _failed_step_label(failed_step) if failed_step else item.item
    reproduction_steps = tuple(_run_reproduction_steps(result)) or (
        f"Execute the failed checklist item: {item.item}",
    )
    actual_result = _failed_step_error(failed_step) or "Unknown failure"
    expected_result = "Scenario should complete all steps successfully."
    source_references = _run_source_references(tracker_path, run_reference, result)
    evidence_paths = _run_evidence_paths(run_reference, result)
    safe_item = replace(item, notes="Run-derived draft; see Source References.")
    return BugTicketDraft(
        title=title,
        severity="S2 - Major",
        priority="P1",
        environment=item.env,
        failed_step=failed_step_label,
        suspected_owner_area=f"{platform.title()} / {scenario_id}",
        item=safe_item,
        reproduction_steps=reproduction_steps,
        expected_result=expected_result,
        actual_result=actual_result,
        source_references=source_references,
        evidence_paths=evidence_paths,
    )


def _latest_run_reference(item: FailedTrackerItem) -> RunReference | None:
    if item.notes.startswith("Run "):
        return _parse_run_reference(item.notes)
    return None


def _parse_run_reference(run_note: str) -> RunReference | None:
    segments = [segment.strip() for segment in run_note.split(";") if segment.strip()]
    if not segments:
        return None
    heading_parts = segments[0].split()
    if len(heading_parts) < 3 or heading_parts[0] != "Run":
        return None
    metadata: dict[str, str] = {}
    for segment in segments[1:]:
        if ":" not in segment:
            continue
        key, value = segment.split(":", 1)
        metadata[key.strip().lower()] = value.strip()
    report_path = metadata.get("report")
    result_path = metadata.get("result")
    if result_path is None and report_path is not None:
        result_path = str(Path(report_path).parent / "result.json")
    evidence_paths = tuple(
        path.strip()
        for path in metadata.get("evidence", "").split(",")
        if path.strip()
    )
    return RunReference(
        run_id=heading_parts[1],
        report_path=report_path,
        result_path=result_path,
        evidence_paths=evidence_paths,
    )


def _load_run_result(reference: RunReference, tracker_path: Path) -> dict[str, Any] | None:
    if reference.result_path is None:
        return None
    result_path = _resolve_path(reference.result_path, tracker_path)
    if not result_path.exists():
        return None
    try:
        payload = json.loads(result_path.read_text())
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _resolve_path(path_value: str, tracker_path: Path) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    candidates = [
        path,
        tracker_path.parent / path,
        tracker_path.parent.parent / path,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return path


def _first_failed_step(result: dict[str, Any]) -> dict[str, Any] | None:
    for step in result.get("steps", []):
        if isinstance(step, dict) and str(step.get("status") or "").lower() == "failed":
            return step
    return None


def _failed_step_label(step: dict[str, Any]) -> str:
    step_id = str(step.get("id") or "unknown-step")
    action = str(step.get("action") or "").strip()
    return f"{step_id} ({action})" if action else step_id


def _failed_step_error(step: dict[str, Any] | None) -> str | None:
    if step is None:
        return None
    error = step.get("error")
    if isinstance(error, str) and error.strip():
        return error.strip()
    return None


def _run_reproduction_steps(result: dict[str, Any]) -> list[str]:
    reproduction_steps: list[str] = []
    for step in result.get("steps", []):
        if not isinstance(step, dict):
            continue
        step_id = str(step.get("id") or "unknown-step")
        action = str(step.get("action") or "execute")
        reproduction_steps.append(f"{action}: `{step_id}`")
    return reproduction_steps


def _run_source_references(
    tracker_path: Path,
    reference: RunReference,
    result: dict[str, Any],
) -> tuple[tuple[str, str], ...]:
    source_references: list[tuple[str, str]] = [("Tracker", str(tracker_path))]
    if reference.result_path:
        source_references.append(("Run result", reference.result_path))
    if reference.report_path:
        source_references.append(("Run report", reference.report_path))
    planning = result.get("planning")
    if isinstance(planning, dict):
        planning_sources = (
            ("Planning input", "input_path"),
            ("Accepted scenario", "accepted_scenario_path"),
            ("Plan provenance", "provenance_path"),
        )
        for label, key in planning_sources:
            value = planning.get(key)
            if isinstance(value, str) and value.strip():
                source_references.append((label, value.strip()))
    return tuple(source_references)


def _run_evidence_paths(reference: RunReference, result: dict[str, Any]) -> tuple[str, ...]:
    run_dir = Path(reference.result_path).parent if reference.result_path else None
    evidence_paths: list[str] = []
    for artifact in [*_artifact_dicts(result.get("evidence")), *_step_artifact_dicts(result)]:
        path_value = artifact.get("path")
        if not isinstance(path_value, str) or not path_value.strip():
            continue
        evidence_path = Path(path_value)
        rendered_path = str(evidence_path if evidence_path.is_absolute() or run_dir is None else run_dir / evidence_path)
        if rendered_path not in evidence_paths:
            evidence_paths.append(rendered_path)
    for path_value in reference.evidence_paths:
        if path_value not in evidence_paths:
            evidence_paths.append(path_value)
    return tuple(evidence_paths)


def _artifact_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [artifact for artifact in value if isinstance(artifact, dict)]


def _step_artifact_dicts(result: dict[str, Any]) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    for step in result.get("steps", []):
        if isinstance(step, dict):
            artifacts.extend(_artifact_dicts(step.get("evidence")))
    return artifacts


def _render_bug_ticket_draft(draft: BugTicketDraft, output_format: str) -> str:
    if output_format == "linear":
        return _render_linear_bug_ticket_draft(draft)
    if output_format == "jira":
        return _render_jira_bug_ticket_draft(draft)
    return _render_markdown_bug_ticket_draft(draft)


def _render_markdown_bug_ticket_draft(draft: BugTicketDraft) -> str:
    item = draft.item
    notes = item.notes or "TBD"
    return f"""# Bug Ticket Draft: {draft.title}

## Issue Fields

- Title: {draft.title}
- Severity: {draft.severity}
- Priority: {draft.priority}
- Environment: {draft.environment}
- Failed Step: {draft.failed_step}
- Suspected Owner/Area: {draft.suspected_owner_area}

## Failed Checklist Item

- Item: {item.item}
- Environment: {item.env}
- Status: {item.status}
- Notes: {notes}

## Reproduction Steps

{_numbered_lines(draft.reproduction_steps)}

## Expected Result

{draft.expected_result}

## Actual Result

{draft.actual_result}

## Source References

{_reference_lines(draft.source_references)}

## Evidence Paths

{_evidence_lines(draft.evidence_paths)}
"""


def _render_linear_bug_ticket_draft(draft: BugTicketDraft) -> str:
    return f"""# Linear Issue Draft

Title: {draft.title}
Priority: {draft.priority}
Labels: qa, bug, {draft.environment}
Team/Area: {draft.suspected_owner_area}

## Description

Severity: {draft.severity}
Environment: {draft.environment}
Failed Step: {draft.failed_step}

## Reproduction Steps

{_numbered_lines(draft.reproduction_steps)}

## Expected Result

{draft.expected_result}

## Actual Result

{draft.actual_result}

## Source References

{_reference_lines(draft.source_references)}

## Evidence Paths

{_evidence_lines(draft.evidence_paths)}
"""


def _render_jira_bug_ticket_draft(draft: BugTicketDraft) -> str:
    return f"""# Jira Issue Draft

Summary: {draft.title}
Issue Type: Bug
Priority: {draft.priority}
Labels: qa, bug, {draft.environment}
Components: {draft.suspected_owner_area}

## Description

Severity: {draft.severity}
Environment: {draft.environment}
Failed Step: {draft.failed_step}

## Steps to Reproduce

{_numbered_lines(draft.reproduction_steps)}

## Expected Result

{draft.expected_result}

## Actual Result

{draft.actual_result}

## Source References

{_reference_lines(draft.source_references)}

## Evidence Paths

{_evidence_lines(draft.evidence_paths)}
"""


def _numbered_lines(lines: tuple[str, ...]) -> str:
    return "\n".join(f"{index}. {line}" for index, line in enumerate(lines, start=1))


def _reference_lines(references: tuple[tuple[str, str], ...]) -> str:
    return "\n".join(f"- {label}: `{value}`" for label, value in references)


def _evidence_lines(evidence_paths: tuple[str, ...]) -> str:
    if not evidence_paths:
        return "- Not linked in tracker notes."
    return "\n".join(f"- `{path}`" for path in evidence_paths)
