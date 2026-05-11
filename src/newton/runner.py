from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from newton.backends.base import DryRunBackend, ExecutionBackend
from newton.models import Platform, RunResult, Scenario, ScenarioTarget
from newton.plan_provenance import planning_metadata_from_provenance
from newton.reporting import redact_run_result, render_markdown_report
from newton.run_index import append_run_index


def find_target(scenario: Scenario, target_id: str) -> ScenarioTarget:
    for target in scenario.targets:
        if target.id == target_id:
            return target
    raise ValueError(f"target not found: {target_id}")


def make_run_id() -> str:
    return f"run_{uuid4().hex[:12]}"


def get_backend(name: str) -> ExecutionBackend:
    if name == "dry-run":
        return DryRunBackend()
    if name == "playwright":
        from newton.backends.web_playwright import PlaywrightBackend

        return PlaywrightBackend()
    if name == "maestro":
        from newton.backends.ios_maestro import MaestroCompileBackend

        return MaestroCompileBackend()
    raise ValueError(f"unsupported backend: {name}")


def validate_backend_for_target(target: ScenarioTarget, backend_name: str) -> None:
    compatibility: dict[str, set[Platform]] = {
        "dry-run": {"web", "ios"},
        "playwright": {"web"},
        "maestro": {"ios"},
    }
    supported = compatibility.get(backend_name)
    if supported is None:
        raise ValueError(f"unsupported backend: {backend_name}")
    if target.platform not in supported:
        raise ValueError(
            f"backend '{backend_name}' does not support target '{target.id}' on platform '{target.platform}'"
        )


def run_scenario(
    scenario: Scenario,
    target_id: str,
    run_dir: Path,
    backend_name: str | None = None,
    base_url: str | None = None,
    plan_provenance_path: Path | None = None,
    scenario_path: Path | None = None,
) -> RunResult:
    target = find_target(scenario, target_id)
    if base_url is not None:
        target = ScenarioTarget.model_validate({**target.model_dump(), "base_url": base_url})
    resolved_backend = backend_name or target.backend
    validate_backend_for_target(target, resolved_backend)
    planning = None
    if plan_provenance_path is not None:
        planning = planning_metadata_from_provenance(plan_provenance_path, scenario_path=scenario_path)
    backend = get_backend(resolved_backend)
    actual_run_dir = run_dir / make_run_id()
    result = backend.run(scenario, target, actual_run_dir)
    result.planning = planning
    result = redact_run_result(result, scenario)

    actual_run_dir.mkdir(parents=True, exist_ok=True)
    (actual_run_dir / "result.json").write_text(result.model_dump_json(indent=2))
    (actual_run_dir / "qa-report.md").write_text(render_markdown_report(result))
    append_run_index(result=result, run_dir=run_dir)
    return result
