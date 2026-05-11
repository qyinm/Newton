from __future__ import annotations

from pathlib import Path
from time import monotonic
from urllib.parse import urljoin

from newton.backends import playwright_setup
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
    if "label" in selector:
        return f"label={selector['label']}"
    if "placeholder" in selector:
        return f"placeholder={selector['placeholder']}"
    if "alt_text" in selector:
        return f"alt_text={selector['alt_text']}"
    if "title" in selector:
        return f"title={selector['title']}"
    if "url" in selector:
        return f"url={selector['url']}"
    if "url_pattern" in selector:
        return f"url_pattern={selector['url_pattern']}"
    return str(selector)


class PlaywrightBackend:
    def run(self, scenario: Scenario, target: ScenarioTarget, run_dir: Path) -> RunResult:
        setup_result = playwright_setup.check_playwright_setup()
        if not setup_result.ok:
            return playwright_setup.run_result_from_setup_failure(setup_result, scenario, target, run_dir)
        return self._run_with_playwright(scenario, target, run_dir)

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
                        navigation_failure = self._navigation_preflight_failure(target, step, exc)
                        if navigation_failure is not None:
                            status = "failed"
                            step_results.append(
                                playwright_setup.step_result_from_setup_failure(
                                    navigation_failure,
                                    step_id="preflight-base-url",
                                    action="reach_base_url",
                                )
                            )
                            for remaining_step in scenario.steps[index - 1 :]:
                                step_results.append(
                                    StepResult(
                                        id=remaining_step.id,
                                        action=remaining_step.action,
                                        status="skipped",
                                        error="Not executed because web preflight failed",
                                    )
                                )
                            break
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
            self._locator(page, selector, step_id=step.id).click(timeout=step.timeout_ms)
            return
        if step.action in {"input_text", "fill"}:
            self._locator(page, selector, step_id=step.id).fill(step.value or "", timeout=step.timeout_ms)
            return
        if step.action == "checkbox":
            self._locator(page, selector, step_id=step.id).set_checked(
                self._checkbox_state(step),
                timeout=step.timeout_ms,
            )
            return
        if step.action == "select_option":
            if step.value is None:
                raise ValueError(f"step '{step.id}' action '{step.action}' requires step.value")
            self._locator(page, selector, step_id=step.id).select_option(step.value, timeout=step.timeout_ms)
            return
        if step.action == "press":
            if not step.value:
                raise ValueError(f"step '{step.id}' action '{step.action}' requires step.value")
            if selector:
                self._locator(page, selector, step_id=step.id).press(step.value, timeout=step.timeout_ms)
            else:
                page.keyboard.press(step.value)
            return
        if step.action == "upload_file":
            if step.value is None:
                raise ValueError(f"step '{step.id}' action '{step.action}' requires step.value")
            self._locator(page, selector, step_id=step.id).set_input_files(step.value, timeout=step.timeout_ms)
            return
        if step.action == "wait":
            page.wait_for_timeout(step.timeout_ms)
            return
        if step.action in {"assert_visible", "wait_for_selector", "expect_visible"}:
            self._locator(page, selector, step_id=step.id).wait_for(state="visible", timeout=step.timeout_ms)
            return
        if step.action in {"assert_hidden", "assert_not_visible"}:
            self._locator(page, selector, step_id=step.id).wait_for(state="hidden", timeout=step.timeout_ms)
            return
        if step.action == "assert_text":
            text = step.value or str(selector.get("text", ""))
            if not text:
                raise ValueError(f"step '{step.id}' action 'assert_text' requires step.value or target.web.text")
            if selector and "text" not in selector:
                from playwright.sync_api import expect

                expect(self._locator(page, selector, step_id=step.id)).to_contain_text(
                    text,
                    timeout=step.timeout_ms,
                )
            else:
                page.get_by_text(text).wait_for(state="visible", timeout=step.timeout_ms)
            return
        if step.action == "assert_url":
            expected_url = self._resolve_url(target, step)
            page.wait_for_url(expected_url, timeout=step.timeout_ms)
            return
        if step.action == "assert_url_pattern":
            expected_pattern = self._resolve_url_pattern(target, step)
            page.wait_for_url(expected_pattern, timeout=step.timeout_ms)
            return
        if step.action == "assert_enabled":
            from playwright.sync_api import expect

            expect(self._locator(page, selector, step_id=step.id)).to_be_enabled(timeout=step.timeout_ms)
            return
        if step.action == "assert_disabled":
            from playwright.sync_api import expect

            expect(self._locator(page, selector, step_id=step.id)).to_be_disabled(timeout=step.timeout_ms)
            return
        if step.action == "assert_value":
            if step.value is None:
                raise ValueError(f"step '{step.id}' action 'assert_value' requires step.value")
            from playwright.sync_api import expect

            expect(self._locator(page, selector, step_id=step.id)).to_have_value(
                step.value,
                timeout=step.timeout_ms,
            )
            return
        raise ValueError(f"unsupported web action: {step.action}")

    def _navigation_preflight_failure(
        self,
        target: ScenarioTarget,
        step: ScenarioStep,
        exc: BaseException,
    ):
        if step.action not in {"navigate", "goto"}:
            return None
        try:
            url = self._resolve_url(target, step)
        except ValueError:
            url = str(target.base_url or step.value or "target URL")
        return playwright_setup.setup_result_from_navigation_error(exc, url)

    def _resolve_url(self, target: ScenarioTarget, step: ScenarioStep) -> str:
        selector = step.target.web if step.target and step.target.web else {}
        raw_url = str(selector.get("url", step.value or "/"))
        if raw_url.startswith(("http://", "https://")):
            return raw_url
        if target.base_url is None:
            raise ValueError("navigate/assert_url step requires target.base_url or absolute url")
        return urljoin(str(target.base_url).rstrip("/") + "/", raw_url.lstrip("/"))

    def _resolve_url_pattern(self, target: ScenarioTarget, step: ScenarioStep) -> str:
        selector = step.target.web if step.target and step.target.web else {}
        raw_pattern = str(selector.get("url_pattern", step.value or ""))
        if not raw_pattern:
            raise ValueError("assert_url_pattern step requires target.web.url_pattern or step.value")
        if raw_pattern.startswith(("http://", "https://")) or "*" in raw_pattern:
            return raw_pattern
        if target.base_url is None:
            raise ValueError("assert_url_pattern step requires target.base_url, absolute url, or glob pattern")
        return urljoin(str(target.base_url).rstrip("/") + "/", raw_pattern.lstrip("/"))

    def _locator(self, page, selector: dict[str, object], *, step_id: str | None = None):
        if "role" in selector:
            return page.get_by_role(str(selector["role"]), name=selector.get("name"))
        if "test_id" in selector:
            return page.get_by_test_id(str(selector["test_id"]))
        if "text" in selector:
            return page.get_by_text(str(selector["text"]))
        if "css" in selector:
            return page.locator(str(selector["css"]))
        if "label" in selector:
            return page.get_by_label(str(selector["label"]))
        if "placeholder" in selector:
            return page.get_by_placeholder(str(selector["placeholder"]))
        if "alt_text" in selector:
            return page.get_by_alt_text(str(selector["alt_text"]))
        if "title" in selector:
            return page.get_by_title(str(selector["title"]))
        raise ValueError(self._unsupported_selector_error(selector, step_id=step_id))

    def _checkbox_state(self, step: ScenarioStep) -> bool:
        if step.value is None:
            return True
        value = step.value.strip().lower()
        if value in {"1", "true", "yes", "on", "checked"}:
            return True
        if value in {"0", "false", "no", "off", "unchecked"}:
            return False
        raise ValueError(
            f"step '{step.id}' action '{step.action}' value {step.value!r}: "
            "checkbox value must be true or false"
        )

    def _unsupported_selector_error(self, selector: dict[str, object], *, step_id: str | None = None) -> str:
        step_prefix = f"step '{step_id}' " if step_id else ""
        return f"{step_prefix}unsupported selector: {selector_description(selector)} payload={selector!r}"
