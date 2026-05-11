import json
from pathlib import Path

import pytest

from newton.models import ARTIFACT_CONTRACT_VERSION, RunResult
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
    result_payload = json.loads(result_path.read_text())
    assert result_payload["contract_version"] == ARTIFACT_CONTRACT_VERSION
    assert result_payload["scenario_id"] == "web-login-smoke"
    assert result_payload["summary"] == {
        "total_steps": 3,
        "passed_steps": 3,
        "failed_steps": 0,
        "skipped_steps": 0,
        "artifact_count": 0,
        "total_duration_ms": None,
        "first_error": None,
    }
    assert "# QA Report: web-login-smoke" in report_path.read_text()


def test_run_result_artifact_validation_rejects_legacy_payload_without_contract_version():
    legacy_payload = {
        "run_id": "run_legacy",
        "scenario_id": "web-login-smoke",
        "target_id": "web",
        "platform": "web",
        "status": "passed",
        "steps": [],
    }

    with pytest.raises(ValueError, match="result.json missing contract_version; regenerate this artifact with Newton v0.1"):
        RunResult.validate_artifact_payload(legacy_payload)


def test_run_scenario_appends_local_run_index_entry(tmp_path: Path):
    scenario = load_scenario(Path("tests/fixtures/scenarios/web_login.yaml"))

    result = run_scenario(scenario, target_id="web", run_dir=tmp_path, backend_name="dry-run")

    index_path = tmp_path / "index.jsonl"
    entries = [json.loads(line) for line in index_path.read_text().splitlines()]
    assert entries == [
        {
            "run_id": result.run_id,
            "scenario_id": "web-login-smoke",
            "target_id": "web",
            "status": "passed",
            "result_path": str(tmp_path / result.run_id / "result.json"),
            "report_path": str(tmp_path / result.run_id / "qa-report.md"),
            "planning_provenance_path": None,
        }
    ]


def test_run_scenario_links_accepted_plan_provenance_in_result_and_report(tmp_path: Path):
    scenario_path = Path("tests/fixtures/scenarios/web_login.yaml")
    scenario = load_scenario(scenario_path)
    provenance_path = tmp_path / "login_ticket.codex.plan.json"
    provenance_path.write_text(
        json.dumps(
            {
                "agent": "codex",
                "input_path": "tests/fixtures/inputs/login_ticket.md",
                "target": "web",
                "base_url": "http://127.0.0.1:8000",
                "prompt_path": "out/login_ticket.codex.prompt.txt",
                "raw_output_path": "out/login_ticket.codex.raw.txt",
                "accepted_scenario_path": str(scenario_path),
                "validation_status": "accepted",
                "validation_error": None,
            }
        )
    )

    result = run_scenario(
        scenario,
        target_id="web",
        run_dir=tmp_path / "runs",
        backend_name="dry-run",
        plan_provenance_path=provenance_path,
        scenario_path=scenario_path,
    )

    run_path = tmp_path / "runs" / result.run_id
    result_payload = json.loads((run_path / "result.json").read_text())
    report = (run_path / "qa-report.md").read_text()

    assert result_payload["planning"] == {
        "provenance_path": str(provenance_path),
        "agent": "codex",
        "input_path": "tests/fixtures/inputs/login_ticket.md",
        "accepted_scenario_path": str(scenario_path),
        "validation_status": "accepted",
    }
    assert "## Planning Provenance" in report
    assert f"**Provenance:** `{provenance_path}`" in report
    assert "**Agent:** codex" in report


def test_run_scenario_rejects_plan_provenance_before_backend_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    scenario = load_scenario(Path("tests/fixtures/scenarios/web_login.yaml"))
    provenance_path = tmp_path / "login_ticket.codex.plan.json"
    provenance_path.write_text(
        json.dumps(
            {
                "agent": "codex",
                "input_path": "tests/fixtures/inputs/login_ticket.md",
                "target": "web",
                "base_url": "http://127.0.0.1:8000",
                "prompt_path": "out/login_ticket.codex.prompt.txt",
                "raw_output_path": "out/login_ticket.codex.raw.txt",
                "accepted_scenario_path": None,
                "validation_status": "rejected",
                "validation_error": "invalid scenario",
            }
        )
    )
    executed = False

    class RecordingBackend:
        def run(self, scenario, target, run_dir):
            nonlocal executed
            executed = True
            from newton.models import RunResult

            return RunResult(
                run_id=run_dir.name,
                scenario_id=scenario.meta.id,
                target_id=target.id,
                platform=target.platform,
                status="passed",
                steps=[],
            )

    monkeypatch.setattr("newton.runner.get_backend", lambda name: RecordingBackend())

    with pytest.raises(ValueError, match="plan provenance must be accepted"):
        run_scenario(
            scenario,
            target_id="web",
            run_dir=tmp_path / "runs",
            backend_name="dry-run",
            plan_provenance_path=provenance_path,
        )

    assert executed is False
    assert not (tmp_path / "runs").exists()


def test_run_scenario_rejects_unrelated_plan_provenance(tmp_path: Path):
    scenario_path = Path("tests/fixtures/scenarios/web_login.yaml")
    scenario = load_scenario(scenario_path)
    provenance_path = tmp_path / "login_ticket.codex.plan.json"
    provenance_path.write_text(
        json.dumps(
            {
                "agent": "codex",
                "input_path": "tests/fixtures/inputs/login_ticket.md",
                "target": "web",
                "base_url": "http://127.0.0.1:8000",
                "prompt_path": "out/login_ticket.codex.prompt.txt",
                "raw_output_path": "out/login_ticket.codex.raw.txt",
                "accepted_scenario_path": "tests/fixtures/scenarios/other.yaml",
                "validation_status": "accepted",
                "validation_error": None,
            }
        )
    )

    with pytest.raises(ValueError, match="does not match scenario path"):
        run_scenario(
            scenario,
            target_id="web",
            run_dir=tmp_path / "runs",
            backend_name="dry-run",
            plan_provenance_path=provenance_path,
            scenario_path=scenario_path,
        )


def test_run_scenario_rejects_accepted_plan_provenance_without_scenario_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    scenario = load_scenario(Path("tests/fixtures/scenarios/web_login.yaml"))
    provenance_path = tmp_path / "login_ticket.codex.plan.json"
    provenance_path.write_text(
        json.dumps(
            {
                "agent": "codex",
                "input_path": "tests/fixtures/inputs/login_ticket.md",
                "target": "web",
                "base_url": "http://127.0.0.1:8000",
                "prompt_path": "out/login_ticket.codex.prompt.txt",
                "raw_output_path": "out/login_ticket.codex.raw.txt",
                "accepted_scenario_path": None,
                "validation_status": "accepted",
                "validation_error": None,
            }
        )
    )
    executed = False

    class RecordingBackend:
        def run(self, scenario, target, run_dir):
            nonlocal executed
            executed = True
            raise AssertionError("backend should not execute")

    monkeypatch.setattr("newton.runner.get_backend", lambda name: RecordingBackend())

    with pytest.raises(ValueError, match="accepted plan provenance must include accepted_scenario_path"):
        run_scenario(
            scenario,
            target_id="web",
            run_dir=tmp_path / "runs",
            backend_name="dry-run",
            plan_provenance_path=provenance_path,
        )

    assert executed is False


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


def test_run_scenario_redacts_secure_step_values_from_artifacts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    scenario = load_scenario(Path("tests/fixtures/scenarios/web_login_playwright.yaml"))

    class RecordingBackend:
        def run(self, scenario, target, run_dir):
            from newton.models import EvidenceArtifact, RunResult, StepResult

            return RunResult(
                run_id=run_dir.name,
                scenario_id=scenario.meta.id,
                target_id=target.id,
                platform=target.platform,
                status="failed",
                steps=[
                    StepResult(
                        id="password",
                        action="fill",
                        status="failed",
                        error="browser error included password123",
                        evidence=[
                            EvidenceArtifact(
                                kind="screenshot",
                                path="failure.png",
                                description="failure after password123",
                            )
                        ],
                    )
                ],
            )

    monkeypatch.setattr("newton.runner.get_backend", lambda name: RecordingBackend())

    result = run_scenario(
        scenario,
        target_id="web",
        run_dir=tmp_path,
        backend_name="playwright",
    )

    run_path = tmp_path / result.run_id
    result_text = (run_path / "result.json").read_text()
    report_text = (run_path / "qa-report.md").read_text()

    assert "password123" not in result.model_dump_json()
    assert "password123" not in result_text
    assert "password123" not in report_text
    assert "[secure value redacted]" in result_text
    assert "[secure value redacted]" in report_text
