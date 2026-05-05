from __future__ import annotations

from pathlib import Path
from time import monotonic

from newton.models import EvidenceArtifact, RunResult, Scenario, ScenarioTarget, StepResult


def selector_description(selector: dict[str, object]) -> str:
    if "role" in selector:
        name = selector.get("name")
        return f"role={selector['role']}[name={name}]" if name else f"role={selector['role']}"
    if "test_id" in selector:
        return f"test_id={selector['test_id']}"
    if "text" in selector:
        return f"text={selector['text']}"
    if "css" in selector:
        return f"css={selector['css']}"
    if "url" in selector:
        return f"url={selector['url']}"
    return str(selector)


class PlaywrightBackend:
    def run(self, scenario: Scenario, target: ScenarioTarget, run_dir: Path) -> RunResult:
        try:
            return self._run_with_playwright(scenario, target, run_dir)
        except ImportError:
            steps = [
                StepResult(
                    id="setup",
                    action="import_playwright",
                    status="failed",
                    error="Playwright is not installed. Run: python -m pip install -e '.[web]' && python -m playwright install chromium",
                )
            ]
            return RunResult(
                run_id=run_dir.name,
                scenario_id=scenario.meta.id,
                target_id=target.id,
                platform=target.platform,
                status="failed",
                steps=steps,
            )

    def _run_with_playwright(self, scenario: Scenario, target: ScenarioTarget, run_dir: Path) -> RunResult:
        from playwright.sync_api import sync_playwright

        run_dir.mkdir(parents=True, exist_ok=True)
        step_results: list[StepResult] = []
        run_evidence: list[EvidenceArtifact] = []
        status = "passed"

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(record_video_dir=str(run_dir) if scenario.evidence.video else None)
            try:
                for step in scenario.steps:
                    start = monotonic()
                    try:
                        self._execute_step(page, target, step)
                        step_results.append(
                            StepResult(
                                id=step.id,
                                action=step.action,
                                status="passed",
                                duration_ms=int((monotonic() - start) * 1000),
                            )
                        )
                    except Exception as exc:  # noqa: BLE001
                        status = "failed"
                        screenshot = run_dir / f"{step.id}.png"
                        page.screenshot(path=str(screenshot))
                        screenshot_artifact = EvidenceArtifact(
                            kind="screenshot",
                            path=str(screenshot),
                            description=f"Failure screenshot for step {step.id}",
                        )
                        run_evidence.append(screenshot_artifact)
                        step_results.append(
                            StepResult(
                                id=step.id,
                                action=step.action,
                                status="failed",
                                error=str(exc),
                                duration_ms=int((monotonic() - start) * 1000),
                                evidence=[screenshot_artifact],
                            )
                        )
                        for remaining_step in scenario.steps[len(step_results) :]:
                            step_results.append(
                                StepResult(
                                    id=remaining_step.id,
                                    action=remaining_step.action,
                                    status="skipped",
                                    error="Not executed because a previous step failed",
                                )
                            )
                        break
            finally:
                browser.close()

        return RunResult(
            run_id=run_dir.name,
            scenario_id=scenario.meta.id,
            target_id=target.id,
            platform="web",
            status=status,
            steps=step_results,
            evidence=run_evidence,
        )

    def _execute_step(self, page, target: ScenarioTarget, step) -> None:
        selector = step.target.web if step.target and step.target.web else {}
        if step.action == "navigate":
            url = selector.get("url", "/")
            if str(url).startswith("http"):
                page.goto(str(url))
            elif target.base_url:
                page.goto(str(target.base_url).rstrip("/") + str(url))
            else:
                raise ValueError("navigate step requires target.base_url or absolute url")
            return
        if step.action == "tap":
            self._locator(page, selector).click(timeout=step.timeout_ms)
            return
        if step.action == "input_text":
            self._locator(page, selector).fill(step.value or "", timeout=step.timeout_ms)
            return
        if step.action == "assert_visible":
            self._locator(page, selector).wait_for(state="visible", timeout=step.timeout_ms)
            return
        raise ValueError(f"unsupported web action: {step.action}")

    def _locator(self, page, selector: dict[str, object]):
        if "role" in selector:
            return page.get_by_role(str(selector["role"]), name=selector.get("name"))
        if "test_id" in selector:
            return page.get_by_test_id(str(selector["test_id"]))
        if "text" in selector:
            return page.get_by_text(str(selector["text"]))
        if "css" in selector:
            return page.locator(str(selector["css"]))
        raise ValueError(f"unsupported selector: {selector_description(selector)}")
