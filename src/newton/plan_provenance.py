from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class PlanProvenanceError(ValueError):
    pass


def plan_provenance_path(input_path: Path, agent: str, out_dir: Path) -> Path:
    return out_dir / f"{input_path.stem}.{agent}.plan.json"


def load_plan_provenance(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text())
    except OSError as exc:
        raise PlanProvenanceError(f"could not read plan provenance: {path}") from exc
    except json.JSONDecodeError as exc:
        raise PlanProvenanceError(f"invalid plan provenance JSON: {path}") from exc

    if not isinstance(payload, dict):
        raise PlanProvenanceError(f"plan provenance must be a JSON object: {path}")
    if payload.get("validation_status") != "accepted":
        raise PlanProvenanceError("plan provenance must be accepted before it can be linked to a run")
    return payload


def _same_path(left: str, right: Path) -> bool:
    return Path(left).expanduser().resolve(strict=False) == right.expanduser().resolve(strict=False)


def planning_metadata_from_provenance(path: Path, scenario_path: Path | None = None) -> dict[str, str]:
    payload = load_plan_provenance(path)
    accepted_scenario_path = payload.get("accepted_scenario_path")
    if accepted_scenario_path is None:
        raise PlanProvenanceError("accepted plan provenance must include accepted_scenario_path")
    if scenario_path is not None:
        if not _same_path(str(accepted_scenario_path), scenario_path):
            raise PlanProvenanceError("plan provenance accepted scenario path does not match scenario path")
    metadata = {
        "provenance_path": str(path),
        "agent": payload.get("agent"),
        "input_path": payload.get("input_path"),
        "accepted_scenario_path": payload.get("accepted_scenario_path"),
        "validation_status": payload.get("validation_status"),
    }
    return {key: str(value) for key, value in metadata.items() if value is not None}


def write_plan_provenance(
    *,
    input_path: Path,
    agent: str,
    target: str,
    out_dir: Path,
    base_url: str,
    prompt_path: Path | None,
    raw_output_path: Path | None,
    accepted_scenario_path: Path | None,
    validation_status: str,
    validation_error: str | None,
) -> Path:
    provenance_path = plan_provenance_path(input_path, agent, out_dir)
    provenance_path.write_text(
        json.dumps(
            {
                "agent": agent,
                "input_path": str(input_path),
                "target": target,
                "base_url": base_url,
                "prompt_path": str(prompt_path) if prompt_path is not None else None,
                "raw_output_path": str(raw_output_path) if raw_output_path is not None else None,
                "accepted_scenario_path": str(accepted_scenario_path) if accepted_scenario_path is not None else None,
                "validation_status": validation_status,
                "validation_error": validation_error,
            },
            indent=2,
        )
        + "\n"
    )
    return provenance_path
