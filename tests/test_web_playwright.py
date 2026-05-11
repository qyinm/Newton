from __future__ import annotations

import contextlib
import functools
import http.server
import importlib.util
import socket
import socketserver
import threading
from pathlib import Path
from typing import Iterator

import pytest

from newton.backends.playwright_setup import (
    chromium_ready,
    setup_failure_result,
    setup_result_from_navigation_error,
)
from newton.backends.web_playwright import PlaywrightBackend, selector_description
from newton.models import (
    EvidenceArtifact,
    RunResult,
    Scenario,
    ScenarioStep,
    ScenarioTarget,
    StepResult,
    TargetBinding,
)
from newton.scenario_loader import load_scenario

HAS_PLAYWRIGHT = importlib.util.find_spec("playwright") is not None and chromium_ready()


def test_selector_description_prefers_role_name():
    assert selector_description({"role": "button", "name": "Log in"}) == "role=button[name=Log in]"


def test_selector_description_accepts_test_id():
    assert selector_description({"test_id": "submit"}) == "test_id=submit"


def test_selector_description_accepts_text():
    assert selector_description({"text": "Dashboard"}) == "text=Dashboard"


@pytest.mark.parametrize(
    ("selector", "expected"),
    [
        ({"css": "#submit"}, "css=#submit"),
        ({"label": "Email"}, "label=Email"),
        ({"placeholder": "Search"}, "placeholder=Search"),
        ({"alt_text": "Product preview"}, "alt_text=Product preview"),
        ({"title": "Continue"}, "title=Continue"),
        ({"url_pattern": "**/dashboard*"}, "url_pattern=**/dashboard*"),
    ],
)
def test_selector_description_accepts_extended_selector_families(selector: dict[str, str], expected: str):
    assert selector_description(selector) == expected


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


def test_playwright_backend_unsupported_selector_error_includes_step_id_and_payload():
    target = ScenarioTarget.model_validate(
        {
            "id": "web",
            "platform": "web",
            "backend": "playwright",
            "base_url": "http://127.0.0.1:8000",
        }
    )
    step = ScenarioStep(
        id="bad-selector",
        action="click",
        target=TargetBinding(web={"xpath": "//button[text()='Save']"}),
    )

    with pytest.raises(ValueError) as exc_info:
        PlaywrightBackend()._execute_step(object(), target, step)

    message = str(exc_info.value)
    assert "bad-selector" in message
    assert "{'xpath': \"//button[text()='Save']\"}" in message


@pytest.mark.skipif(not HAS_PLAYWRIGHT, reason="Playwright package is required for browser integration")
def test_playwright_backend_runs_login_fixture(playwright_fixture_base_url: str, tmp_path: Path):
    scenario = load_scenario(Path("tests/fixtures/scenarios/web_login_playwright.yaml"))
    target = scenario.targets[0].model_copy(update={"base_url": playwright_fixture_base_url})

    result = PlaywrightBackend().run(scenario, target, tmp_path / "run_fixture")

    assert result.status == "passed"
    assert [step.status for step in result.steps] == ["passed"] * len(scenario.steps)


@pytest.mark.skipif(not HAS_PLAYWRIGHT, reason="Playwright package is required for browser integration")
def test_playwright_backend_runs_extended_selector_and_action_fixture(
    extended_playwright_fixture: tuple[str, Path],
    tmp_path: Path,
):
    base_url, upload_path = extended_playwright_fixture
    scenario = Scenario.model_validate(
        {
            "scenario": {
                "id": "web-selector-action-coverage",
                "title": "Web selector and action coverage",
            },
            "targets": [
                {
                    "id": "web",
                    "platform": "web",
                    "backend": "playwright",
                    "base_url": base_url,
                }
            ],
            "steps": [
                {"id": "open", "action": "navigate", "target": {"web": {"url": "/index.html"}}},
                {"id": "explicit-wait", "action": "wait", "timeout_ms": 25},
                {
                    "id": "fill-email-by-label",
                    "action": "fill",
                    "value": "qa@example.com",
                    "target": {"web": {"label": "Email"}},
                },
                {
                    "id": "input-search-by-placeholder",
                    "action": "input_text",
                    "value": "release notes",
                    "target": {"web": {"placeholder": "Search docs"}},
                },
                {
                    "id": "press-enter-in-search",
                    "action": "press",
                    "value": "Enter",
                    "target": {"web": {"placeholder": "Search docs"}},
                },
                {
                    "id": "assert-keyboard-text",
                    "action": "assert_text",
                    "value": "Pressed Enter",
                    "target": {"web": {"css": "#keyboard-status"}},
                },
                {
                    "id": "check-terms",
                    "action": "checkbox",
                    "value": "true",
                    "target": {"web": {"label": "Accept terms"}},
                },
                {
                    "id": "select-plan",
                    "action": "select_option",
                    "value": "pro",
                    "target": {"web": {"title": "Plan selector"}},
                },
                {
                    "id": "upload-evidence",
                    "action": "upload_file",
                    "value": str(upload_path),
                    "target": {"web": {"label": "Evidence file"}},
                },
                {
                    "id": "assert-upload-text",
                    "action": "assert_text",
                    "value": upload_path.name,
                    "target": {"web": {"css": "#file-status"}},
                },
                {
                    "id": "tap-role-button",
                    "action": "tap",
                    "target": {"web": {"role": "button", "name": "Role tap"}},
                },
                {
                    "id": "assert-tap-text",
                    "action": "assert_text",
                    "value": "Role tapped",
                    "target": {"web": {"css": "#tap-status"}},
                },
                {"id": "click-save", "action": "click", "target": {"web": {"test_id": "save-btn"}}},
                {
                    "id": "assert-url-pattern",
                    "action": "assert_url_pattern",
                    "target": {"web": {"url_pattern": "**/done?plan=pro"}},
                },
                {"id": "assert-url", "action": "assert_url", "target": {"web": {"url": "/done?plan=pro"}}},
                {
                    "id": "assert-status-text",
                    "action": "assert_text",
                    "value": "Saved qa@example.com with pro",
                    "target": {"web": {"css": "#status"}},
                },
                {
                    "id": "assert-visible-by-text",
                    "action": "assert_visible",
                    "target": {"web": {"text": "Saved qa@example.com with pro"}},
                },
                {
                    "id": "assert-visible-by-alt-text",
                    "action": "assert_visible",
                    "target": {"web": {"alt_text": "Product preview"}},
                },
                {"id": "assert-hidden", "action": "assert_hidden", "target": {"web": {"css": "#hide-me"}}},
                {
                    "id": "assert-not-visible",
                    "action": "assert_not_visible",
                    "target": {"web": {"css": "#transient"}},
                },
                {
                    "id": "assert-enabled",
                    "action": "assert_enabled",
                    "target": {"web": {"role": "button", "name": "Enabled action"}},
                },
                {
                    "id": "assert-disabled",
                    "action": "assert_disabled",
                    "target": {"web": {"title": "Disabled action"}},
                },
                {
                    "id": "assert-value",
                    "action": "assert_value",
                    "value": "qa@example.com",
                    "target": {"web": {"label": "Email"}},
                },
            ],
        }
    )

    result = PlaywrightBackend().run(scenario, scenario.targets[0], tmp_path / "run_extended")

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


@pytest.fixture
def extended_playwright_fixture(tmp_path: Path) -> Iterator[tuple[str, Path]]:
    fixture_dir = tmp_path / "web"
    fixture_dir.mkdir()
    upload_path = tmp_path / "evidence.txt"
    upload_path.write_text("fixture evidence", encoding="utf-8")
    (fixture_dir / "index.html").write_text(
        """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Newton selector fixture</title>
  </head>
  <body>
    <main>
      <h1>Selector coverage</h1>
      <label for="email">Email</label>
      <input id="email" />
      <input id="search" placeholder="Search docs" />
      <label><input id="terms" type="checkbox" /> Accept terms</label>
      <label for="plan">Plan</label>
      <select id="plan" title="Plan selector">
        <option value="">Choose</option>
        <option value="basic">Basic</option>
        <option value="pro">Pro</option>
      </select>
      <label for="evidence">Evidence file</label>
      <input id="evidence" type="file" />
      <button type="button" aria-label="Role tap" id="role-tap">Tap</button>
      <button type="button" data-testid="save-btn" id="save">Save</button>
      <button type="button" id="enabled">Enabled action</button>
      <button type="button" title="Disabled action" disabled>Archive</button>
      <img alt="Product preview" src="data:image/gif;base64,R0lGODlhAQABAAAAACw=" />
      <p id="keyboard-status"></p>
      <p id="file-status"></p>
      <p id="tap-status"></p>
      <p id="status"></p>
      <p id="hide-me">Hide me</p>
      <p id="transient">Transient</p>
    </main>
    <script>
      const email = document.getElementById('email');
      const plan = document.getElementById('plan');
      document.getElementById('search').addEventListener('keydown', (event) => {
        if (event.key === 'Enter') {
          document.getElementById('keyboard-status').textContent = 'Pressed Enter';
        }
      });
      document.getElementById('evidence').addEventListener('change', (event) => {
        document.getElementById('file-status').textContent = event.target.files[0].name;
      });
      document.getElementById('role-tap').addEventListener('click', () => {
        document.getElementById('tap-status').textContent = 'Role tapped';
      });
      document.getElementById('save').addEventListener('click', () => {
        document.getElementById('status').textContent = `Saved ${email.value} with ${plan.value}`;
        document.getElementById('hide-me').hidden = true;
        document.getElementById('transient').style.display = 'none';
        history.pushState({}, '', `/done?plan=${plan.value}`);
      });
    </script>
  </body>
</html>
""",
        encoding="utf-8",
    )

    port = _free_port()
    handler = functools.partial(QuietSimpleHTTPRequestHandler, directory=str(fixture_dir))
    server = socketserver.ThreadingTCPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}", upload_path
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


class QuietSimpleHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        return


def _free_port() -> int:
    with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])
