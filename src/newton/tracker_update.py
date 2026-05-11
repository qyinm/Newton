from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class TrackerUpdateError(ValueError):
    """Raised when a QA run tracker cannot be updated."""


VALID_STATUSES = {"not run", "passed", "failed", "blocked", "needs retest"}
VALID_ENVS = {"dev", "stg", "prod"}
ENV_ORDER = ("dev", "stg", "prod")


@dataclass
class _EnvironmentTracker:
    status: str = "not run"
    notes: str = ""
    runs: list[str] = field(default_factory=list)


def update_tracker_item(
    tracker_path: Path,
    *,
    item_number: int,
    env: str,
    status: str,
    notes: str,
) -> Path:
    return _update_tracker_item(
        tracker_path,
        item_number=item_number,
        env=env,
        status=status,
        notes=notes,
        run_note=None,
    )


def update_tracker_item_from_run(
    tracker_path: Path,
    *,
    item_number: int,
    env: str,
    run_path: Path,
) -> Path:
    result_path = run_path / "result.json"
    if not result_path.exists():
        raise TrackerUpdateError(f"run result not found: {result_path}")
    try:
        result = json.loads(result_path.read_text())
    except json.JSONDecodeError as exc:
        raise TrackerUpdateError(f"invalid run result JSON: {result_path}") from exc

    status = _tracker_status_from_run_result(result)
    run_id = str(result.get("run_id") or run_path.name)
    report_path = run_path / "qa-report.md"
    run_note = f"Run {run_id} {status}; report: {report_path}"
    return _update_tracker_item(
        tracker_path,
        item_number=item_number,
        env=env,
        status=status,
        notes=run_note,
        run_note=run_note,
    )


def _tracker_status_from_run_result(result: dict[str, Any]) -> str:
    status = str(result.get("status") or "").strip().lower()
    if status in {"passed", "failed"}:
        return status
    if status == "skipped":
        return "blocked"
    raise TrackerUpdateError(f"unsupported run result status: {status or '<missing>'}")


def _update_environment_status(lines: list[str], env: str, status: str) -> list[str]:
    updated: list[str] = []
    for line in lines:
        if line.startswith(f"- {env}:"):
            updated.append(f"- {env}: {status}")
        else:
            updated.append(line)
    return updated


def _update_tracker_item(
    tracker_path: Path,
    *,
    item_number: int,
    env: str,
    status: str,
    notes: str,
    run_note: str | None,
) -> Path:
    if not tracker_path.exists():
        raise TrackerUpdateError(f"qa run tracker not found: {tracker_path}")
    if item_number < 1:
        raise TrackerUpdateError(f"tracker item not found: {item_number}")

    normalized_env = env.strip().lower()
    normalized_status = status.strip().lower()
    if normalized_env not in VALID_ENVS:
        raise TrackerUpdateError(f"invalid tracker environment: {env}")
    if normalized_status not in VALID_STATUSES:
        raise TrackerUpdateError(f"invalid tracker status: {status}")

    lines = tracker_path.read_text().splitlines()
    updated_lines = _update_environment_status(lines, normalized_env, normalized_status)
    updated_lines = _update_checklist_item(
        updated_lines,
        item_number=item_number,
        env=normalized_env,
        status=normalized_status,
        notes=notes,
        run_note=run_note,
    )
    tracker_path.write_text("\n".join(updated_lines) + "\n")
    return tracker_path


def _update_checklist_item(
    lines: list[str],
    *,
    item_number: int,
    env: str,
    status: str,
    notes: str,
    run_note: str | None,
) -> list[str]:
    item_starts = [
        index
        for index, line in enumerate(lines)
        if line.strip().startswith("- [")
    ]
    if item_number > len(item_starts):
        raise TrackerUpdateError(f"tracker item not found: {item_number}")

    start = item_starts[item_number - 1]
    end = item_starts[item_number] if item_number < len(item_starts) else len(lines)
    item_text = _extract_item_text(lines[start])
    environments = _parse_environment_trackers(lines[start + 1 : end])
    environments[env].status = status
    environments[env].notes = _single_line(notes)
    if run_note is not None:
        environments[env].runs.append(_single_line(run_note))
    replacement = _render_checklist_item(item_text, environments)
    return [*lines[:start], *replacement, *lines[end:]]


def _extract_item_text(line: str) -> str:
    stripped = line.strip()
    for prefix in ("- [ ] ", "- [x] ", "- [X] "):
        if stripped.startswith(prefix):
            return stripped.removeprefix(prefix).strip()
    raise TrackerUpdateError("unsupported tracker checklist format")


def _parse_environment_trackers(lines: list[str]) -> dict[str, _EnvironmentTracker]:
    environments = {env: _EnvironmentTracker() for env in ENV_ORDER}
    current_env: str | None = None
    legacy_env = "dev"
    legacy_status: str | None = None
    legacy_notes: str | None = None
    in_runs = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        env = _environment_heading(stripped)
        if env is not None:
            current_env = env
            in_runs = False
            continue
        if current_env is not None:
            if stripped.startswith("- status:"):
                parsed_status = stripped.removeprefix("- status:").strip().lower()
                if parsed_status in VALID_STATUSES:
                    environments[current_env].status = parsed_status
                in_runs = False
                continue
            if stripped.startswith("- notes:"):
                environments[current_env].notes = stripped.removeprefix("- notes:").strip()
                in_runs = False
                continue
            if stripped == "- runs:":
                in_runs = True
                continue
            if in_runs and stripped.startswith("- "):
                environments[current_env].runs.append(stripped.removeprefix("- ").strip())
                continue

        if stripped.startswith("- env:"):
            parsed_env = stripped.removeprefix("- env:").strip().lower()
            if parsed_env in VALID_ENVS:
                legacy_env = parsed_env
            continue
        if stripped.startswith("- status:"):
            legacy_status = stripped.removeprefix("- status:").strip().lower()
            continue
        if stripped.startswith("- notes:"):
            legacy_notes = stripped.removeprefix("- notes:").strip()

    if legacy_status is not None or legacy_notes is not None:
        if legacy_status in VALID_STATUSES:
            environments[legacy_env].status = legacy_status
        environments[legacy_env].notes = legacy_notes or ""
        if legacy_notes and legacy_notes.startswith("Run ") and "report:" in legacy_notes:
            environments[legacy_env].runs.append(legacy_notes)

    return environments


def _environment_heading(stripped: str) -> str | None:
    for env in ENV_ORDER:
        if stripped == f"- {env}:":
            return env
    return None


def _render_checklist_item(item_text: str, environments: dict[str, _EnvironmentTracker]) -> list[str]:
    checkbox = "[x]" if all(environments[env].status == "passed" for env in ENV_ORDER) else "[ ]"
    rendered = [f"- {checkbox} {item_text}"]
    for env in ENV_ORDER:
        state = environments[env]
        rendered.extend(
            [
                f"  - {env}:",
                f"    - status: {state.status}",
                f"    - notes:{f' {state.notes}' if state.notes else ''}",
                "    - runs:",
            ]
        )
        rendered.extend(f"      - {run}" for run in state.runs)
    return rendered


def _single_line(value: str) -> str:
    return " ".join(value.splitlines()).strip()
