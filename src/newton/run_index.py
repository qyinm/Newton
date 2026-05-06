from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from newton.models import RunResult


def run_index_path(run_dir: Path) -> Path:
    return run_dir / "index.jsonl"


def run_index_entry(*, result: RunResult, run_dir: Path) -> dict[str, Any]:
    run_path = run_dir / result.run_id
    planning = result.planning or {}
    return {
        "run_id": result.run_id,
        "scenario_id": result.scenario_id,
        "target_id": result.target_id,
        "status": result.status,
        "result_path": str(run_path / "result.json"),
        "report_path": str(run_path / "qa-report.md"),
        "planning_provenance_path": planning.get("provenance_path"),
    }


def append_run_index(*, result: RunResult, run_dir: Path) -> Path:
    index_path = run_index_path(run_dir)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    entry = run_index_entry(result=result, run_dir=run_dir)
    with index_path.open("a") as file:
        file.write(json.dumps(entry, sort_keys=True) + "\n")
    return index_path


def read_run_index(run_dir: Path) -> list[dict[str, Any]]:
    index_path = run_index_path(run_dir)
    if not index_path.exists():
        return []
    entries: list[dict[str, Any]] = []
    for line in index_path.read_text().splitlines():
        if not line.strip():
            continue
        entries.append(json.loads(line))
    return entries
