from newton.models import EvidenceArtifact, RunResult, StepResult
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
                        path="qa/runs/run_001/tap-login.png",
                        description="Failure screenshot for step tap-login",
                    )
                ],
            ),
        ],
        evidence=[
            EvidenceArtifact(
                kind="video",
                path="qa/runs/run_001/session.webm",
                description="Playwright session recording",
            )
        ],
    )

    markdown = render_markdown_report(result)

    assert "# QA Report: login-smoke" in markdown
    assert "**Status:** failed" in markdown
    assert "| tap-login | tap | failed | button not found |" in markdown
    assert "## Evidence" in markdown
    assert "qa/runs/run_001/session.webm" in markdown
    assert "## Step Evidence" in markdown
    assert "qa/runs/run_001/tap-login.png" in markdown
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
