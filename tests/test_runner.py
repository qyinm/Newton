import json
from pathlib import Path

import pytest

from newton.runner import run_scenario
from newton.scenario_loader import load_scenario


def test_run_scenario_with_dry_run_backend(tmp_path: Path):
    scenario = load_scenario(Path("tests/fixtures/scenarios/web_login.yaml"))
    result = run_scenario(scenario, target_id="web", run_dir=tmp_path, backend_name="dry-run")

    assert result.status == "passed"
    assert result.run_id.startswith("run_")
    assert [step.status for step in result.steps] == ["passed", "passed", "passed"]


def test_run_scenario_writes_result_and_report(tmp_path: Path):
    scenario = load_scenario(Path("tests/fixtures/scenarios/web_login.yaml"))
    result = run_scenario(scenario, target_id="web", run_dir=tmp_path, backend_name="dry-run")

    run_path = tmp_path / result.run_id
    result_path = run_path / "result.json"
    report_path = run_path / "qa-report.md"

    assert result_path.exists()
    assert report_path.exists()
    assert json.loads(result_path.read_text())["scenario_id"] == "web-login-smoke"
    assert "# QA Report: web-login-smoke" in report_path.read_text()


def test_run_scenario_rejects_backend_platform_mismatch(tmp_path: Path):
    scenario = load_scenario(Path("tests/fixtures/scenarios/cross_platform_login.yaml"))

    with pytest.raises(ValueError, match="does not support"):
        run_scenario(scenario, target_id="ios", run_dir=tmp_path, backend_name="playwright")


def test_run_scenario_applies_base_url_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    scenario = load_scenario(Path("tests/fixtures/scenarios/web_login.yaml"))
    seen = {}

    class RecordingBackend:
        def run(self, scenario, target, run_dir):
            seen["base_url"] = str(target.base_url)
            from newton.models import RunResult, StepResult

            return RunResult(
                run_id=run_dir.name,
                scenario_id=scenario.meta.id,
                target_id=target.id,
                platform=target.platform,
                status="passed",
                steps=[StepResult(id="setup", action="record", status="passed")],
            )

    monkeypatch.setattr("newton.runner.get_backend", lambda name: RecordingBackend())

    run_scenario(
        scenario,
        target_id="web",
        run_dir=tmp_path,
        backend_name="playwright",
        base_url="http://127.0.0.1:9000",
    )

    assert seen["base_url"] == "http://127.0.0.1:9000/"
