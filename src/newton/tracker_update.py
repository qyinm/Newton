from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class TrackerUpdateError(ValueError):
    """Raised when a QA run tracker cannot be updated."""


VALID_STATUSES = {"not run", "passed", "failed", "blocked", "needs retest"}
VALID_ENVS = {"dev", "stg", "prod"}


def update_tracker_item(
    tracker_path: Path,
    *,
    item_number: int,
    env: str,
    status: str,
    notes: str,
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
    )
    tracker_path.write_text("\n".join(updated_lines) + "\n")
    return tracker_path


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
    notes = f"Run {run_id} {status}; report: {report_path}"
    return update_tracker_item(
        tracker_path,
        item_number=item_number,
        env=env,
        status=status,
        notes=notes,
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
        stripped = line.strip()
        if stripped.startswith(f"- {env}:"):
            updated.append(f"- {env}: {status}")
        else:
            updated.append(line)
    return updated


def _update_checklist_item(
    lines: list[str],
    *,
    item_number: int,
    env: str,
    status: str,
    notes: str,
) -> list[str]:
    item_starts = [index for index, line in enumerate(lines) if line.strip().startswith("- [")]
    if item_number > len(item_starts):
        raise TrackerUpdateError(f"tracker item not found: {item_number}")

    start = item_starts[item_number - 1]
    end = item_starts[item_number] if item_number < len(item_starts) else len(lines)
    item_text = _extract_item_text(lines[start])
    checkbox = "[ ]" if status == "not run" else "[x]"
    replacement = [
        f"- {checkbox} {item_text}",
        f"  - env: {env}",
        f"  - status: {status}",
        f"  - notes: {notes}",
    ]
    return [*lines[:start], *replacement, *lines[end:]]


def _extract_item_text(line: str) -> str:
    stripped = line.strip()
    for prefix in ("- [ ] ", "- [x] ", "- [X] "):
        if stripped.startswith(prefix):
            return stripped.removeprefix(prefix).strip()
    raise TrackerUpdateError("unsupported tracker checklist format")
