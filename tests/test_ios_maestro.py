from pathlib import Path

from newton.backends.ios_maestro import compile_maestro_flow
from newton.scenario_loader import load_scenario


def test_compile_maestro_flow_from_ios_bindings():
    scenario = load_scenario(Path("tests/fixtures/scenarios/cross_platform_login.yaml"))
    target = scenario.targets[1]

    flow = compile_maestro_flow(scenario, target)

    assert flow["appId"] == "com.example.app"
    assert flow["---"][0] == {"launchApp": {}}
    assert {"tapOn": {"id": "emailField"}} in flow["---"]
    assert {"inputText": "qa@example.com"} in flow["---"]
    assert {"assertVisible": "Home"} in flow["---"]
