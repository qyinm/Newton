from __future__ import annotations

from pathlib import Path

import yaml

from newton.models import EvidenceArtifact, RunResult, Scenario, ScenarioTarget, StepResult


def compile_maestro_flow(scenario: Scenario, target: ScenarioTarget) -> dict[str, object]:
    if not target.bundle_id:
        raise ValueError("Maestro iOS target requires bundle_id")

    commands: list[dict[str, object]] = [{"launchApp": {}}]
    for step in scenario.steps:
        binding = step.target.ios if step.target and step.target.ios else {}
        if step.action == "tap":
            commands.append({"tapOn": _maestro_selector(binding)})
        elif step.action == "input_text":
            commands.append({"tapOn": _maestro_selector(binding)})
            commands.append({"inputText": step.value or ""})
        elif step.action == "assert_visible":
            if "text" in binding:
                commands.append({"assertVisible": binding["text"]})
            else:
                commands.append({"assertVisible": _maestro_selector(binding)})
        elif step.action == "launch_app":
            commands.append({"launchApp": {}})
        elif step.action == "navigate":
            commands.append({"openLink": _maestro_link(binding)})
        else:
            raise ValueError(f"unsupported iOS action for Maestro: {step.action}")

    return {"appId": target.bundle_id, "---": commands}


def _maestro_selector(binding: dict[str, object]) -> dict[str, str] | str:
    if "accessibility_id" in binding:
        return {"id": str(binding["accessibility_id"])}
    if "text" in binding:
        return str(binding["text"])
    raise ValueError(f"unsupported iOS binding: {binding}")


def _maestro_link(binding: dict[str, object]) -> str:
    for key in ("url", "deep_link"):
        if key in binding:
            return str(binding[key])
    raise ValueError(f"navigate step requires ios.url or ios.deep_link binding: {binding}")


class MaestroCompileBackend:
    def run(self, scenario: Scenario, target: ScenarioTarget, run_dir: Path) -> RunResult:
        run_dir.mkdir(parents=True, exist_ok=True)
        flow = compile_maestro_flow(scenario, target)
        flow_path = run_dir / "maestro-flow.yaml"
        flow_path.write_text(yaml.safe_dump(flow, sort_keys=False))
        steps = [StepResult(id=step.id, action=step.action, status="passed") for step in scenario.steps]
        return RunResult(
            run_id=run_dir.name,
            scenario_id=scenario.meta.id,
            target_id=target.id,
            platform=target.platform,
            status="passed",
            steps=steps,
            evidence=[EvidenceArtifact(kind="maestro_flow", path=str(flow_path), description="Compiled Maestro flow")],
        )
