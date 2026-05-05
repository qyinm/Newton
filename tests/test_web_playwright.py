from pathlib import Path

import importlib.util

import pytest

from newton.backends.web_playwright import PlaywrightBackend, selector_description

HAS_PLAYWRIGHT = importlib.util.find_spec("playwright") is not None
from newton.models import EvidenceArtifact, RunResult, StepResult
from newton.scenario_loader import load_scenario


def test_selector_description_prefers_role_name():
    assert selector_description({"role": "button", "name": "Log in"}) == "role=button[name=Log in]"


def test_selector_description_accepts_test_id():
    assert selector_description({"test_id": "submit"}) == "test_id=submit"


def test_selector_description_accepts_text():
    assert selector_description({"text": "Dashboard"}) == "text=Dashboard"


def test_playwright_backend_resolves_relative_url_with_base_url():
    scenario = load_scenario(Path("tests/fixtures/scenarios/web_login.yaml"))
    target = scenario.targets[0].model_copy(update={"base_url": "http://127.0.0.1:8000/app"})
    step = scenario.steps[0]

    assert PlaywrightBackend()._resolve_url(target, step) == "http://127.0.0.1:8000/app/login"


def test_playwright_backend_stores_relative_screenshot_and_trace_evidence(tmp_path: Path):
    result = RunResult(
        run_id=tmp_path.name,
        scenario_id="web-login-smoke",
        target_id="web",
        platform="web",
        status="failed",
        steps=[
            StepResult(
                id="assert-dashboard",
                action="assert_visible",
                status="failed",
                evidence=[
                    EvidenceArtifact(
                        kind="screenshot",
                        path="failure-step-005-assert-dashboard.png",
                        description="Failure screenshot for step assert-dashboard",
                    )
                ],
            )
        ],
        evidence=[
            EvidenceArtifact(
                kind="trace",
                path="playwright-trace.zip",
                description="Playwright trace for failed run",
            )
        ],
    )

    assert all(not Path(artifact.path).is_absolute() for artifact in result.evidence)
    assert all(not Path(artifact.path).is_absolute() for step in result.steps for artifact in step.evidence)
    assert result.evidence[0].path == "playwright-trace.zip"
    assert result.steps[0].evidence[0].path.startswith("failure-step-005-")


@pytest.mark.skipif(not HAS_PLAYWRIGHT, reason="Playwright package is required for browser integration")
def test_playwright_backend_runs_login_fixture(playwright_fixture_base_url: str, tmp_path: Path):
    scenario = load_scenario(Path("tests/fixtures/scenarios/web_login_playwright.yaml"))
    target = scenario.targets[0].model_copy(update={"base_url": playwright_fixture_base_url})

    result = PlaywrightBackend().run(scenario, target, tmp_path / "run_fixture")

    assert result.status == "passed"
    assert [step.status for step in result.steps] == ["passed"] * len(scenario.steps)


@pytest.mark.skipif(not HAS_PLAYWRIGHT, reason="Playwright package is required for browser integration")
def test_playwright_backend_captures_screenshot_and_trace_on_failure(playwright_fixture_base_url: str, tmp_path: Path):
    scenario = load_scenario(Path("tests/fixtures/scenarios/web_login_playwright_failure.yaml"))
    target = scenario.targets[0].model_copy(update={"base_url": playwright_fixture_base_url})
    run_dir = tmp_path / "run_failure"

    result = PlaywrightBackend().run(scenario, target, run_dir)

    assert result.status == "failed"
    assert any(artifact.kind == "trace" and artifact.path == "playwright-trace.zip" for artifact in result.evidence)
    failed_step = next(step for step in result.steps if step.status == "failed")
    screenshot = next(artifact for artifact in failed_step.evidence if artifact.kind == "screenshot")
    assert screenshot.path.startswith("failure-step-")
    assert (run_dir / screenshot.path).exists()
    assert (run_dir / "playwright-trace.zip").exists()
