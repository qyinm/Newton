import pytest
from pydantic import ValidationError

from newton.models import (
    EvidenceArtifact,
    EvidencePolicy,
    RunResult,
    Scenario,
    StepResult,
    TargetBinding,
)


def test_scenario_accepts_minimal_web_case():
    scenario = Scenario.model_validate(
        {
            "scenario": {
                "id": "login-smoke",
                "title": "Login smoke",
                "priority": "P0",
                "risk_category": "functional",
            },
            "targets": [
                {
                    "id": "web",
                    "platform": "web",
                    "backend": "playwright",
                    "base_url": "https://staging.example.com",
                }
            ],
            "steps": [
                {
                    "id": "open-login",
                    "action": "navigate",
                    "target": {"web": {"url": "/login"}},
                }
            ],
        }
    )

    assert scenario.meta.id == "login-smoke"
    assert scenario.targets[0].platform == "web"
    assert scenario.steps[0].action == "navigate"


def test_scenario_rejects_unknown_platform():
    with pytest.raises(ValidationError):
        Scenario.model_validate(
            {
                "scenario": {"id": "bad", "title": "Bad"},
                "targets": [{"id": "desktop", "platform": "desktop", "backend": "none"}],
                "steps": [],
            }
        )


def test_evidence_defaults_are_safe():
    policy = EvidencePolicy()

    assert policy.screenshots == "on_failure"
    assert policy.video is False
    assert policy.logs is True


def test_target_binding_keeps_platform_specific_selectors():
    binding = TargetBinding.model_validate(
        {
            "web": {"role": "button", "name": "Log in"},
            "ios": {"accessibility_id": "loginButton"},
        }
    )

    assert binding.web["role"] == "button"
    assert binding.ios["accessibility_id"] == "loginButton"


def test_run_result_tracks_failure_status():
    result = RunResult(
        run_id="run_001",
        scenario_id="login",
        target_id="web",
        platform="web",
        status="failed",
        steps=[
            StepResult(id="open", action="navigate", status="passed"),
            StepResult(id="submit", action="tap", status="failed", error="button missing"),
        ],
    )

    assert result.failed_step_ids() == ["submit"]
    assert result.passed is False


def test_run_result_tracks_success_status():
    result = RunResult(
        run_id="run_002",
        scenario_id="login",
        target_id="web",
        platform="web",
        status="passed",
        steps=[StepResult(id="open", action="navigate", status="passed")],
    )

    assert result.failed_step_ids() == []
    assert result.passed is True


def test_scenario_rejects_empty_steps():
    with pytest.raises(ValidationError, match="at least one step"):
        Scenario.model_validate(
            {
                "scenario": {"id": "empty-steps", "title": "Empty steps"},
                "targets": [
                    {
                        "id": "web",
                        "platform": "web",
                        "backend": "playwright",
                        "base_url": "https://staging.example.com",
                    }
                ],
                "steps": [],
            }
        )


def test_scenario_rejects_missing_platform_binding():
    with pytest.raises(ValidationError, match="missing an ios target binding"):
        Scenario.model_validate(
            {
                "scenario": {"id": "cross-platform", "title": "Cross-platform"},
                "targets": [
                    {
                        "id": "web",
                        "platform": "web",
                        "backend": "playwright",
                        "base_url": "https://staging.example.com",
                    },
                    {
                        "id": "ios",
                        "platform": "ios",
                        "backend": "maestro",
                        "bundle_id": "com.example.app",
                    },
                ],
                "steps": [
                    {
                        "id": "submit",
                        "action": "tap",
                        "target": {"web": {"role": "button", "name": "Log in"}},
                    }
                ],
            }
        )
