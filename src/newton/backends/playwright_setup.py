from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from newton.models import RunResult, Scenario, ScenarioTarget, StepResult

SetupStatus = Literal["passed", "failed"]

INSTALL_WEB_COMMAND = "python -m pip install -e '.[web]'"
INSTALL_CHROMIUM_COMMAND = "python -m playwright install chromium"
INSTALL_CHROMIUM_WITH_DEPS_COMMAND = "python -m playwright install --with-deps chromium"

_REMEDIATION_BY_KIND = {
    "missing_playwright": [INSTALL_WEB_COMMAND, INSTALL_CHROMIUM_COMMAND],
    "missing_chromium": [INSTALL_CHROMIUM_COMMAND, INSTALL_CHROMIUM_WITH_DEPS_COMMAND],
    "missing_os_dependencies": [INSTALL_CHROMIUM_WITH_DEPS_COMMAND],
    "launch_failed": [INSTALL_CHROMIUM_COMMAND, INSTALL_CHROMIUM_WITH_DEPS_COMMAND],
    "unreachable_base_url": [
        "Start the target web app, then rerun: newton qa run <scenario.yaml> --target web --backend playwright --base-url <reachable-url>"
    ],
}


@dataclass(frozen=True)
class PlaywrightSetupCheck:
    name: str
    status: SetupStatus
    message: str
    remediation: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PlaywrightSetupResult:
    status: SetupStatus
    checks: list[PlaywrightSetupCheck]
    failure_kind: str | None = None
    message: str = ""
    remediation: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.status == "passed"

    def format_error(self) -> str:
        if self.ok:
            return "Playwright setup passed."
        headline = self.failure_kind or "playwright_setup_failed"
        lines = [f"{headline}: {self.message or 'Playwright setup failed.'}"]
        if self.remediation:
            lines.append("Remediation:")
            lines.extend(f"- {command}" for command in self.remediation)
        return "\n".join(lines)


def check_playwright_setup() -> PlaywrightSetupResult:
    checks: list[PlaywrightSetupCheck] = []
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        return setup_failure_result(
            "missing_playwright",
            str(exc),
            checks=[
                PlaywrightSetupCheck(
                    name="playwright_import",
                    status="failed",
                    message="Playwright import is not available.",
                    remediation=_REMEDIATION_BY_KIND["missing_playwright"],
                )
            ],
        )

    checks.append(
        PlaywrightSetupCheck(
            name="playwright_import",
            status="passed",
            message="Playwright import is available.",
        )
    )

    try:
        with sync_playwright() as playwright:
            checks.append(
                PlaywrightSetupCheck(
                    name="chromium_browser",
                    status="passed",
                    message="Chromium browser type is available.",
                )
            )
            browser = playwright.chromium.launch(headless=True)
            browser.close()
    except Exception as exc:  # noqa: BLE001
        failure_kind = classify_playwright_setup_error(exc)
        return setup_failure_result(
            failure_kind,
            _summarize_exception(exc),
            checks=[
                *checks,
                PlaywrightSetupCheck(
                    name="chromium_launch",
                    status="failed",
                    message=_summarize_exception(exc),
                    remediation=_REMEDIATION_BY_KIND[failure_kind],
                ),
            ],
        )

    checks.append(
        PlaywrightSetupCheck(
            name="chromium_launch",
            status="passed",
            message="Chromium launched headlessly.",
        )
    )
    return PlaywrightSetupResult(status="passed", checks=checks)


def chromium_ready() -> bool:
    try:
        return check_playwright_setup().ok
    except Exception:  # noqa: BLE001
        return False


def setup_failure_result(
    failure_kind: str,
    message: str,
    *,
    checks: list[PlaywrightSetupCheck] | None = None,
) -> PlaywrightSetupResult:
    remediation = _REMEDIATION_BY_KIND.get(failure_kind, _REMEDIATION_BY_KIND["launch_failed"])
    return PlaywrightSetupResult(
        status="failed",
        checks=checks
        or [
            PlaywrightSetupCheck(
                name=failure_kind,
                status="failed",
                message=message,
                remediation=remediation,
            )
        ],
        failure_kind=failure_kind,
        message=message,
        remediation=remediation,
    )


def classify_playwright_setup_error(exc: BaseException) -> str:
    message = str(exc).lower()
    if "host system is missing dependencies" in message or "missing dependencies" in message:
        return "missing_os_dependencies"
    if "missing libraries" in message or "playwright install-deps" in message:
        return "missing_os_dependencies"
    if "executable doesn't exist" in message or "executable does not exist" in message:
        return "missing_chromium"
    if "please run" in message and "playwright install" in message:
        return "missing_chromium"
    if "browser executable" in message and "not found" in message:
        return "missing_chromium"
    return "launch_failed"


def setup_result_from_navigation_error(exc: BaseException, url: str) -> PlaywrightSetupResult | None:
    message = str(exc).lower()
    unreachable_markers = [
        "err_connection_refused",
        "err_name_not_resolved",
        "err_connection_timed_out",
        "err_address_unreachable",
        "err_internet_disconnected",
        "net::err_failed",
    ]
    if not any(marker in message for marker in unreachable_markers):
        return None
    return setup_failure_result(
        "unreachable_base_url",
        f"Base URL is unreachable: {url}. Playwright reported: {_summarize_exception(exc)}",
    )


def step_result_from_setup_failure(
    setup_result: PlaywrightSetupResult,
    *,
    step_id: str = "setup",
    action: str = "playwright_setup",
) -> StepResult:
    return StepResult(
        id=step_id,
        action=action,
        status="failed",
        error=setup_result.format_error(),
    )


def run_result_from_setup_failure(
    setup_result: PlaywrightSetupResult,
    scenario: Scenario,
    target: ScenarioTarget,
    run_dir: Path,
    *,
    step_id: str = "setup",
    action: str = "playwright_setup",
) -> RunResult:
    return RunResult(
        run_id=run_dir.name,
        scenario_id=scenario.meta.id,
        target_id=target.id,
        platform=target.platform,
        status="failed",
        steps=[
            step_result_from_setup_failure(
                setup_result,
                step_id=step_id,
                action=action,
            )
        ],
    )


def _summarize_exception(exc: BaseException) -> str:
    message = str(exc).strip()
    if not message:
        return exc.__class__.__name__
    return message.splitlines()[0].strip()
