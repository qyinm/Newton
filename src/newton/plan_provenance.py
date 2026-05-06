from __future__ import annotations

import json
from pathlib import Path


def plan_provenance_path(input_path: Path, agent: str, out_dir: Path) -> Path:
    return out_dir / f"{input_path.stem}.{agent}.plan.json"


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
