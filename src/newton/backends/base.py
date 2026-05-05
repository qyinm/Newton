from __future__ import annotations

from pathlib import Path
from typing import Protocol

from newton.models import RunResult, Scenario, ScenarioTarget, StepResult


class ExecutionBackend(Protocol):
    def run(self, scenario: Scenario, target: ScenarioTarget, run_dir: Path) -> RunResult:
        """Execute a scenario target and return a normalized result."""


class DryRunBackend:
    def run(self, scenario: Scenario, target: ScenarioTarget, run_dir: Path) -> RunResult:
        run_dir.mkdir(parents=True, exist_ok=True)
        steps = [StepResult(id=step.id, action=step.action, status="passed") for step in scenario.steps]
        return RunResult(
            run_id=run_dir.name,
            scenario_id=scenario.meta.id,
            target_id=target.id,
            platform=target.platform,
            status="passed",
            steps=steps,
        )
