from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class HandoffError(Exception):
    """Raised when a QA handoff packet cannot be built."""


@dataclass(frozen=True)
class HandoffPacket:
    bundle_path: Path | None = None
    scenario_path: Path | None = None
    run_id: str | None = None
    report_path: Path | None = None
    evidence_paths: tuple[Path, ...] = ()
    tracker_path: Path | None = None
    bug_draft_path: Path | None = None


def build_handoff_packet(
    workspace: Path,
    *,
    bundle_path: Path | None = None,
    scenario_path: Path | None = None,
    run_path: Path | None = None,
    tracker_path: Path | None = None,
    bug_draft_path: Path | None = None,
) -> HandoffPacket:
    if not workspace.exists():
        raise HandoffError(f"handoff workspace not found: {workspace}")

    detected_run_path = run_path or _detect_run_path(workspace)
    result = _read_result_json(detected_run_path) if detected_run_path is not None else None
    detected_bundle_path = bundle_path or _detect_bundle_path(workspace)
    detected_tracker_path = tracker_path or _detect_tracker_path(workspace, detected_bundle_path)

    return HandoffPacket(
        bundle_path=detected_bundle_path,
        scenario_path=scenario_path or _detect_scenario_path(workspace, result),
        run_id=_string_value(result, "run_id"),
        report_path=_detect_report_path(detected_run_path, result),
        evidence_paths=_collect_evidence_paths(detected_run_path, result),
        tracker_path=detected_tracker_path,
        bug_draft_path=bug_draft_path or _detect_bug_draft_path(workspace, detected_bundle_path, detected_tracker_path),
    )


def render_handoff_packet(packet: HandoffPacket) -> str:
    lines = ["# Newton QA Handoff"]
    _append_path(lines, "bundle_path", packet.bundle_path)
    _append_path(lines, "scenario_path", packet.scenario_path)
    if packet.run_id:
        lines.append(f"run_id: {packet.run_id}")
    _append_path(lines, "report_path", packet.report_path)
    if packet.evidence_paths:
        lines.append("evidence_paths:")
        for path in packet.evidence_paths:
            lines.append(f"  - {path}")
    _append_path(lines, "tracker_path", packet.tracker_path)
    _append_path(lines, "bug_draft_path", packet.bug_draft_path)
    return "\n".join(lines) + "\n"


def write_handoff_packet(packet: HandoffPacket, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_handoff_packet(packet))
    return output_path


def _detect_bundle_path(workspace: Path) -> Path | None:
    candidates = [
        workspace if (workspace / "manifest.json").exists() else None,
        workspace / "plan" if (workspace / "plan" / "manifest.json").exists() else None,
    ]
    candidates.extend(path.parent for path in sorted(workspace.glob("*/manifest.json")))
    return _first_existing_directory(candidates)


def _detect_run_path(workspace: Path) -> Path | None:
    if (workspace / "result.json").exists():
        return workspace

    index_path = workspace / "runs" / "index.jsonl"
    if index_path.exists():
        entries = [json.loads(line) for line in index_path.read_text().splitlines() if line.strip()]
        if entries:
            result_path = _path_value(entries[-1], "result_path")
            if result_path is not None:
                return result_path.parent

    run_paths = sorted(path for path in (workspace / "runs").glob("run_*") if path.is_dir())
    return run_paths[-1] if run_paths else None


def _detect_scenario_path(workspace: Path, result: dict[str, Any] | None) -> Path | None:
    planning = result.get("planning") if result else None
    if isinstance(planning, dict):
        accepted_path = _path_value(planning, "accepted_scenario_path")
        if accepted_path is not None:
            return accepted_path

    candidates = sorted((workspace / "scenario").glob("*.generated.yaml"))
    candidates.extend(sorted((workspace / "scenario").glob("*.yaml")))
    candidates.extend(sorted((workspace / "scenarios").glob("*.yaml")))
    return candidates[0] if candidates else None


def _detect_report_path(run_path: Path | None, result: dict[str, Any] | None) -> Path | None:
    if run_path is None:
        return None
    report_path = run_path / "qa-report.md"
    if report_path.exists():
        return report_path

    report_value = _path_value(result, "report_path") if result else None
    return report_value if report_value and report_value.exists() else None


def _detect_tracker_path(workspace: Path, bundle_path: Path | None) -> Path | None:
    manifest = _read_manifest(bundle_path) if bundle_path is not None else None
    artifacts = manifest.get("artifacts") if manifest else None
    if isinstance(artifacts, dict):
        tracker_path = _path_value(artifacts, "qa_run_tracker")
        if tracker_path is not None and tracker_path.exists():
            return tracker_path

    candidates = [
        bundle_path / "qa-run-tracker.md" if bundle_path is not None else None,
        workspace / "qa-run-tracker.md",
        workspace / "plan" / "qa-run-tracker.md",
    ]
    return _first_existing_file(candidates)


def _detect_bug_draft_path(workspace: Path, bundle_path: Path | None, tracker_path: Path | None) -> Path | None:
    candidates = [
        workspace / "bug-ticket-draft.md",
        bundle_path / "bug-ticket-draft.md" if bundle_path is not None else None,
        bundle_path.parent / "bug-ticket-draft.md" if bundle_path is not None else None,
        tracker_path.parent / "bug-ticket-draft.md" if tracker_path is not None else None,
    ]
    return _first_existing_file(candidates)


def _collect_evidence_paths(run_path: Path | None, result: dict[str, Any] | None) -> tuple[Path, ...]:
    if run_path is None or result is None:
        return ()

    evidence_paths: list[Path] = []
    seen: set[str] = set()

    def append_artifacts(artifacts: object) -> None:
        if not isinstance(artifacts, list):
            return
        for artifact in artifacts:
            if not isinstance(artifact, dict):
                continue
            artifact_path = _path_value(artifact, "path")
            if artifact_path is None:
                continue
            if not artifact_path.is_absolute():
                artifact_path = run_path / artifact_path
            key = str(artifact_path)
            if key not in seen:
                seen.add(key)
                evidence_paths.append(artifact_path)

    append_artifacts(result.get("evidence"))
    steps = result.get("steps")
    if isinstance(steps, list):
        for step in steps:
            if isinstance(step, dict):
                append_artifacts(step.get("evidence"))

    return tuple(evidence_paths)


def _read_result_json(run_path: Path) -> dict[str, Any]:
    result_path = run_path / "result.json"
    if not result_path.exists():
        raise HandoffError(f"run result not found: {result_path}")
    return _read_json_object(result_path)


def _read_manifest(bundle_path: Path | None) -> dict[str, Any]:
    if bundle_path is None:
        return {}
    manifest_path = bundle_path / "manifest.json"
    if not manifest_path.exists():
        return {}
    return _read_json_object(manifest_path)


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise HandoffError(f"invalid JSON artifact: {path}") from exc
    if not isinstance(payload, dict):
        raise HandoffError(f"JSON artifact must be an object: {path}")
    return payload


def _path_value(payload: dict[str, Any], key: str) -> Path | None:
    value = payload.get(key)
    return Path(value) if isinstance(value, str) and value else None


def _string_value(payload: dict[str, Any] | None, key: str) -> str | None:
    if payload is None:
        return None
    value = payload.get(key)
    return value if isinstance(value, str) and value else None


def _first_existing_directory(paths: list[Path | None]) -> Path | None:
    for path in paths:
        if path is not None and path.is_dir():
            return path
    return None


def _first_existing_file(paths: list[Path | None]) -> Path | None:
    for path in paths:
        if path is not None and path.is_file():
            return path
    return None


def _append_path(lines: list[str], key: str, path: Path | None) -> None:
    if path is not None:
        lines.append(f"{key}: {path}")
