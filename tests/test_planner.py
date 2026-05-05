from pathlib import Path

import yaml

from newton.planner import plan_scenario_from_markdown
from newton.scenario_loader import load_scenario


def test_plan_scenario_from_markdown_generates_valid_web_login_yaml(tmp_path: Path):
    output = plan_scenario_from_markdown(
        Path("tests/fixtures/inputs/login_ticket.md"),
        target="web",
        out_dir=tmp_path,
    )

    assert output == tmp_path / "login-smoke.generated.yaml"
    assert output.exists()

    raw = yaml.safe_load(output.read_text())
    assert raw["scenario"]["id"] == "login-smoke"
    assert raw["scenario"]["title"] == "Login smoke"
    assert raw["targets"] == [
        {
            "id": "web",
            "platform": "web",
            "backend": "playwright",
            "base_url": "http://127.0.0.1:8000",
        }
    ]
    assert [step["id"] for step in raw["steps"]] == [
        "open-login",
        "enter-email",
        "enter-password",
        "submit",
        "assert-dashboard",
    ]

    scenario = load_scenario(output)
    assert scenario.meta.id == "login-smoke"
    assert scenario.targets[0].platform == "web"


def test_plan_scenario_from_markdown_can_include_ios_bindings(tmp_path: Path):
    output = plan_scenario_from_markdown(
        Path("tests/fixtures/inputs/login_ticket.md"),
        target="web,ios",
        out_dir=tmp_path,
    )

    scenario = load_scenario(output)
    assert {target.platform for target in scenario.targets} == {"web", "ios"}
    assert all(step.target and step.target.web and step.target.ios for step in scenario.steps if step.action != "navigate")
