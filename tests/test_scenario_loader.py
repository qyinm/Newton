from pathlib import Path

import pytest

from newton.scenario_loader import ScenarioLoadError, load_scenario


def test_load_scenario_from_yaml_fixture():
    scenario = load_scenario(Path("tests/fixtures/scenarios/web_login.yaml"))

    assert scenario.meta.id == "web-login-smoke"
    assert scenario.targets[0].backend == "playwright"
    assert len(scenario.steps) == 3


def test_load_scenario_rejects_missing_file():
    with pytest.raises(ScenarioLoadError, match="not found"):
        load_scenario(Path("tests/fixtures/scenarios/missing.yaml"))
