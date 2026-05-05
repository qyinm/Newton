from pathlib import Path
import subprocess

import pytest
import yaml

from newton.agent_planner import AgentPlanningError, plan_scenario_with_agent
from newton.scenario_loader import load_scenario


def _valid_agent_yaml() -> str:
    return yaml.safe_dump(
        {
            "scenario": {
                "id": "agent-login-smoke",
                "title": "Agent login smoke",
                "source_refs": ["agent"],
                "risk_category": "functional",
                "priority": "P0",
                "environments": ["local"],
            },
            "targets": [
                {
                    "id": "web",
                    "platform": "web",
                    "backend": "playwright",
                    "base_url": "http://127.0.0.1:8000",
                }
            ],
            "steps": [
                {"id": "open-login", "action": "navigate", "target": {"web": {"url": "/login.html"}}},
                {
                    "id": "assert-dashboard",
                    "action": "assert_visible",
                    "target": {"web": {"text": "Dashboard"}},
                },
            ],
            "evidence": {"screenshots": "on_failure", "video": False, "logs": True, "traces": True},
        },
        sort_keys=False,
    )


def test_agent_planner_accepts_valid_codex_yaml_from_shared_contract(tmp_path: Path):
    seen: dict[str, object] = {}

    def fake_run(command, *, input, text, capture_output, check):
        seen["command"] = command
        seen["prompt"] = input
        return subprocess.CompletedProcess(command, 0, stdout=_valid_agent_yaml(), stderr="")

    output = plan_scenario_with_agent(
        Path("tests/fixtures/inputs/login_ticket.md"),
        agent="codex",
        target="web",
        out_dir=tmp_path,
        base_url="http://127.0.0.1:8000",
        command=["codex", "exec", "-"],
        run=fake_run,
    )

    assert output == tmp_path / "agent-login-smoke.generated.yaml"
    scenario = load_scenario(output)
    assert scenario.meta.id == "agent-login-smoke"
    assert seen["command"] == ["codex", "exec", "-"]
    assert "Output only valid Newton scenario YAML" in str(seen["prompt"])
    assert "Agent: codex" in str(seen["prompt"])
    assert "Target: web" in str(seen["prompt"])


def test_agent_planner_supports_optional_claude_adapter_with_same_contract(tmp_path: Path):
    seen: dict[str, object] = {}

    def fake_run(command, *, input, text, capture_output, check):
        seen["command"] = command
        seen["prompt"] = input
        return subprocess.CompletedProcess(command, 0, stdout=f"```yaml\n{_valid_agent_yaml()}```", stderr="")

    output = plan_scenario_with_agent(
        Path("tests/fixtures/inputs/login_ticket.md"),
        agent="claude",
        target="web",
        out_dir=tmp_path,
        command=["claude", "-p"],
        run=fake_run,
    )

    assert output.exists()
    assert load_scenario(output).meta.id == "agent-login-smoke"
    assert seen["command"] == ["claude", "-p"]
    assert "Agent: claude" in str(seen["prompt"])


def test_agent_planner_rejects_invalid_yaml_and_preserves_raw_output(tmp_path: Path):
    def fake_run(command, *, input, text, capture_output, check):
        return subprocess.CompletedProcess(command, 0, stdout="not: a newton scenario\n", stderr="")

    with pytest.raises(AgentPlanningError, match="agent output did not validate"):
        plan_scenario_with_agent(
            Path("tests/fixtures/inputs/login_ticket.md"),
            agent="codex",
            target="web",
            out_dir=tmp_path,
            command=["codex", "exec", "-"],
            run=fake_run,
        )

    raw_output = tmp_path / "login_ticket.codex.raw.txt"
    assert raw_output.exists()
    assert raw_output.read_text() == "not: a newton scenario\n"
