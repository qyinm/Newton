from __future__ import annotations

from pathlib import Path
from time import monotonic
from urllib.parse import urljoin

from newton.models import EvidenceArtifact, RunResult, Scenario, ScenarioStep, ScenarioTarget, StepResult


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
        traces_enabled = scenario.evidence.traces
        trace_path = run_dir / "playwright-trace.zip"

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(record_video_dir=str(run_dir) if scenario.evidence.video else None)
            if traces_enabled:
                context.tracing.start(screenshots=True, snapshots=True, sources=True)
            page = context.new_page()
            try:
                for index, step in enumerate(scenario.steps, start=1):
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
                        step_evidence: list[EvidenceArtifact] = []
                        if scenario.evidence.screenshots in {"on_failure", "after_each_step"}:
                            screenshot_name = f"failure-step-{index:03d}-{step.id}.png"
                            screenshot = run_dir / screenshot_name
                            page.screenshot(path=str(screenshot), full_page=True)
                            screenshot_artifact = EvidenceArtifact(
                                kind="screenshot",
                                path=screenshot_name,
                                description=f"Failure screenshot for step {step.id}",
                            )
                            run_evidence.append(screenshot_artifact)
                            step_evidence.append(screenshot_artifact)
                        step_results.append(
                            StepResult(
                                id=step.id,
                                action=step.action,
                                status="failed",
                                error=str(exc),
                                duration_ms=int((monotonic() - start) * 1000),
                                evidence=step_evidence,
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
                if traces_enabled:
                    context.tracing.stop(path=str(trace_path))
                    if status == "failed":
                        run_evidence.append(
                            EvidenceArtifact(
                                kind="trace",
                                path=trace_path.name,
                                description="Playwright trace for failed run",
                            )
                        )
                context.close()
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

    def _execute_step(self, page, target: ScenarioTarget, step: ScenarioStep) -> None:
        selector = step.target.web if step.target and step.target.web else {}
        if step.action in {"navigate", "goto"}:
            page.goto(self._resolve_url(target, step), wait_until="domcontentloaded", timeout=step.timeout_ms)
            return
        if step.action in {"tap", "click"}:
            self._locator(page, selector).click(timeout=step.timeout_ms)
            return
        if step.action in {"input_text", "fill"}:
            self._locator(page, selector).fill(step.value or "", timeout=step.timeout_ms)
            return
        if step.action in {"assert_visible", "wait_for_selector", "expect_visible"}:
            self._locator(page, selector).wait_for(state="visible", timeout=step.timeout_ms)
            return
        if step.action == "assert_text":
            text = step.value or str(selector.get("text", ""))
            if not text:
                raise ValueError("assert_text requires step.value or target.web.text")
            page.get_by_text(text).wait_for(state="visible", timeout=step.timeout_ms)
            return
        if step.action == "assert_url":
            expected_url = self._resolve_url(target, step)
            page.wait_for_url(expected_url, timeout=step.timeout_ms)
            return
        raise ValueError(f"unsupported web action: {step.action}")

    def _resolve_url(self, target: ScenarioTarget, step: ScenarioStep) -> str:
        selector = step.target.web if step.target and step.target.web else {}
        raw_url = str(selector.get("url", step.value or "/"))
        if raw_url.startswith(("http://", "https://")):
            return raw_url
        if target.base_url is None:
            raise ValueError("navigate/assert_url step requires target.base_url or absolute url")
        return urljoin(str(target.base_url).rstrip("/") + "/", raw_url.lstrip("/"))

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
