from newton import reporting
from newton.models import EvidenceArtifact, RunResult, Scenario, StepResult
from newton.reporting import render_markdown_report


def test_render_markdown_report_for_failed_run():
    result = RunResult(
        run_id="run_001",
        scenario_id="login-smoke",
        target_id="web",
        platform="web",
        status="failed",
        steps=[
            StepResult(id="open-login", action="navigate", status="passed"),
            StepResult(
                id="tap-login",
                action="tap",
                status="failed",
                error="button not found",
                evidence=[
                    EvidenceArtifact(
                        kind="screenshot",
                        path="tap-login.png",
                        description="Failure screenshot for step tap-login",
                    )
                ],
            ),
        ],
        evidence=[
            EvidenceArtifact(
                kind="video",
                path="session.webm",
                description="Playwright session recording",
            ),
            EvidenceArtifact(
                kind="console",
                path="console-errors.jsonl",
                description="1 browser console error(s)",
            )
        ],
    )

    markdown = render_markdown_report(result)

    assert "# QA Report: login-smoke" in markdown
    assert "**Status:** failed" in markdown
    assert "## Run Summary" in markdown
    assert "| 2 | 1 | 1 | 0 | 3 | - |" in markdown
    assert "| tap-login | tap | failed | button not found |" in markdown
    assert "## Evidence" in markdown
    assert "session.webm" in markdown
    assert "console-errors.jsonl" in markdown
    assert "## Step Evidence" in markdown
    assert "tap-login.png" in markdown
    assert "## Failure Diagnosis" in markdown
    assert "**First failed step:** `tap-login`" in markdown
    assert "### Diagnostic Artifacts" in markdown
    assert "## Bug Draft" in markdown
    assert "button not found" in markdown


def test_render_markdown_report_includes_optional_planning_provenance():
    result = RunResult(
        run_id="run_001",
        scenario_id="login-smoke",
        target_id="web",
        platform="web",
        status="passed",
        steps=[StepResult(id="open-login", action="navigate", status="passed")],
        planning={
            "provenance_path": "qa/generated/login_ticket.codex.plan.json",
            "agent": "codex",
            "input_path": "tests/fixtures/inputs/login_ticket.md",
            "accepted_scenario_path": "qa/generated/login-smoke.generated.yaml",
            "validation_status": "accepted",
        },
    )

    markdown = render_markdown_report(result)

    assert "## Planning Provenance" in markdown
    assert "**Provenance:** `qa/generated/login_ticket.codex.plan.json`" in markdown
    assert "**Agent:** codex" in markdown
    assert "**Input:** `tests/fixtures/inputs/login_ticket.md`" in markdown
    assert "**Accepted Scenario:** `qa/generated/login-smoke.generated.yaml`" in markdown


def test_redact_run_result_removes_secure_step_values_from_reportable_fields():
    scenario = Scenario.model_validate(
        {
            "scenario": {"id": "secure-login", "title": "Secure login"},
            "targets": [
                {
                    "id": "web",
                    "platform": "web",
                    "backend": "playwright",
                    "base_url": "https://example.com",
                }
            ],
            "steps": [
                {
                    "id": "password",
                    "action": "fill",
                    "secure": True,
                    "value": "super-secret-password",
                    "target": {"web": {"label": "Password"}},
                }
            ],
        }
    )
    result = RunResult(
        run_id="run_001",
        scenario_id="secure-login",
        target_id="web",
        platform="web",
        status="failed",
        steps=[
            StepResult(
                id="password",
                action="fill",
                status="failed",
                error="Playwright echoed super-secret-password in an error",
                evidence=[
                    EvidenceArtifact(
                        kind="screenshot",
                        path="failure.png",
                        description="Failure after super-secret-password",
                    )
                ],
            )
        ],
    )

    assert hasattr(reporting, "redact_run_result")

    redacted = reporting.redact_run_result(result, scenario)
    markdown = render_markdown_report(redacted)

    assert "super-secret-password" not in redacted.model_dump_json()
    assert "super-secret-password" not in markdown
    assert "[secure value redacted]" in markdown


def test_redact_run_result_removes_secure_step_values_from_summary_and_diagnosis():
    scenario = Scenario.model_validate(
        {
            "scenario": {"id": "secure-login", "title": "Secure login"},
            "targets": [
                {
                    "id": "web",
                    "platform": "web",
                    "backend": "playwright",
                    "base_url": "https://example.com",
                }
            ],
            "steps": [
                {
                    "id": "password",
                    "action": "fill",
                    "secure": True,
                    "value": "super-secret-password",
                    "target": {"web": {"label": "Password"}},
                }
            ],
        }
    )
    result = RunResult(
        run_id="run_001",
        scenario_id="secure-login",
        target_id="web",
        platform="web",
        status="failed",
        steps=[
            StepResult(
                id="password",
                action="fill",
                status="failed",
                error="browser error included super-secret-password",
            )
        ],
    )

    redacted = reporting.redact_run_result(result, scenario)
    markdown = render_markdown_report(redacted)

    assert redacted.summary is not None
    assert redacted.summary.first_error == "browser error included [secure value redacted]"
    assert "super-secret-password" not in markdown
    assert "**Error:** browser error included [secure value redacted]" in markdown
