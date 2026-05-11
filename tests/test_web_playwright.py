from pathlib import Path

import importlib.util

import pytest

from newton.backends.playwright_setup import (
    chromium_ready,
    setup_failure_result,
    setup_result_from_navigation_error,
)
from newton.backends.web_playwright import PlaywrightBackend, selector_description

HAS_PLAYWRIGHT = importlib.util.find_spec("playwright") is not None and chromium_ready()
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


def test_playwright_setup_result_for_missing_playwright_includes_install_command():
    result = setup_failure_result("missing_playwright", "No module named 'playwright'")

    assert result.status == "failed"
    assert result.failure_kind == "missing_playwright"
    assert "python -m pip install -e '.[web]'" in result.remediation
    assert "python -m playwright install chromium" in result.remediation
    assert "missing_playwright" in result.format_error()


def test_playwright_setup_result_for_missing_os_dependencies_includes_with_deps_command():
    result = setup_failure_result("missing_os_dependencies", "Host system is missing dependencies.")

    assert result.status == "failed"
    assert result.failure_kind == "missing_os_dependencies"
    assert "python -m playwright install --with-deps chromium" in result.remediation


def test_playwright_navigation_error_becomes_unreachable_base_url_preflight():
    result = setup_result_from_navigation_error(
        RuntimeError("Page.goto: net::ERR_CONNECTION_REFUSED at http://127.0.0.1:65535/login"),
        "http://127.0.0.1:65535/login",
    )

    assert result is not None
    assert result.failure_kind == "unreachable_base_url"
    assert "http://127.0.0.1:65535/login" in result.message
    assert "newton qa run" in result.remediation[0]


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
