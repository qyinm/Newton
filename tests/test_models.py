import pytest
from pydantic import ValidationError

from newton.models import (
    ARTIFACT_CONTRACT_VERSION,
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
    assert scenario.contract_version == ARTIFACT_CONTRACT_VERSION
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


def test_scenario_rejects_web_target_without_base_url():
    with pytest.raises(ValidationError, match="web target 'web' must define base_url"):
        Scenario.model_validate(
            {
                "scenario": {"id": "missing-base-url", "title": "Missing base URL"},
                "targets": [
                    {
                        "id": "web",
                        "platform": "web",
                        "backend": "playwright",
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


def test_scenario_rejects_web_target_with_incompatible_backend():
    with pytest.raises(ValidationError, match="backend 'maestro' does not support platform 'web'"):
        Scenario.model_validate(
            {
                "scenario": {"id": "bad-backend", "title": "Bad backend"},
                "targets": [
                    {
                        "id": "web",
                        "platform": "web",
                        "backend": "maestro",
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


def test_scenario_rejects_invalid_timeout():
    with pytest.raises(ValidationError, match="timeout_ms must be greater than 0"):
        Scenario.model_validate(
            {
                "scenario": {"id": "bad-timeout", "title": "Bad timeout"},
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
                        "timeout_ms": 0,
                        "target": {"web": {"url": "/login"}},
                    }
                ],
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


@pytest.mark.parametrize(
    "selector",
    [
        {"role": "button", "name": "Log in"},
        {"test_id": "submit"},
        {"text": "Dashboard"},
        {"css": "#submit"},
        {"label": "Email"},
        {"placeholder": "Search"},
        {"alt_text": "Product preview"},
        {"title": "Continue"},
    ],
)
def test_scenario_accepts_supported_web_selector_families(selector: dict[str, str]):
    scenario = _scenario_with_step({"id": "exercise-selector", "action": "click", "target": {"web": selector}})

    assert scenario.steps[0].target is not None
    assert scenario.steps[0].target.web == selector


@pytest.mark.parametrize(
    "step",
    [
        {"id": "open", "action": "navigate", "target": {"web": {"url": "/login"}}},
        {"id": "goto", "action": "goto", "target": {"web": {"url": "/login"}}},
        {"id": "click", "action": "click", "target": {"web": {"role": "button", "name": "Save"}}},
        {"id": "tap", "action": "tap", "target": {"web": {"role": "button", "name": "Save"}}},
        {"id": "fill", "action": "fill", "value": "qa@example.com", "target": {"web": {"label": "Email"}}},
        {
            "id": "input-text",
            "action": "input_text",
            "value": "Search",
            "target": {"web": {"placeholder": "Search"}},
        },
        {"id": "checkbox", "action": "checkbox", "value": "true", "target": {"web": {"label": "Terms"}}},
        {"id": "select-option", "action": "select_option", "value": "pro", "target": {"web": {"label": "Plan"}}},
        {"id": "press", "action": "press", "value": "Enter", "target": {"web": {"placeholder": "Search"}}},
        {"id": "upload", "action": "upload_file", "value": "/tmp/evidence.txt", "target": {"web": {"label": "Evidence"}}},
        {"id": "wait", "action": "wait", "timeout_ms": 25},
        {"id": "assert-url", "action": "assert_url", "target": {"web": {"url": "/dashboard"}}},
        {
            "id": "assert-url-pattern",
            "action": "assert_url_pattern",
            "target": {"web": {"url_pattern": "**/dashboard*"}},
        },
        {"id": "assert-text", "action": "assert_text", "value": "Saved", "target": {"web": {"css": "#status"}}},
        {"id": "assert-visible", "action": "assert_visible", "target": {"web": {"text": "Dashboard"}}},
        {"id": "assert-hidden", "action": "assert_hidden", "target": {"web": {"css": "#spinner"}}},
        {"id": "assert-not-visible", "action": "assert_not_visible", "target": {"web": {"css": "#modal"}}},
        {"id": "assert-enabled", "action": "assert_enabled", "target": {"web": {"role": "button", "name": "Save"}}},
        {
            "id": "assert-disabled",
            "action": "assert_disabled",
            "target": {"web": {"role": "button", "name": "Archive"}},
        },
        {"id": "assert-value", "action": "assert_value", "value": "qa@example.com", "target": {"web": {"label": "Email"}}},
        {"id": "wait-for-selector", "action": "wait_for_selector", "target": {"web": {"css": "#ready"}}},
        {"id": "expect-visible", "action": "expect_visible", "target": {"web": {"text": "Ready"}}},
    ],
)
def test_scenario_accepts_supported_web_actions_and_assertions(step: dict[str, object]):
    scenario = _scenario_with_step(step)

    assert scenario.steps[0].id == step["id"]
    assert scenario.steps[0].action == step["action"]


def test_scenario_rejects_unsupported_web_selector_with_step_id_and_payload():
    with pytest.raises(ValidationError) as exc_info:
        _scenario_with_step(
            {
                "id": "bad-selector",
                "action": "click",
                "target": {"web": {"xpath": "//button[text()='Save']"}},
            }
        )

    message = str(exc_info.value)
    assert "bad-selector" in message
    assert "{'xpath': \"//button[text()='Save']\"}" in message


def _scenario_with_step(step: dict[str, object]) -> Scenario:
    return Scenario.model_validate(
        {
            "scenario": {"id": "web-contract", "title": "Web contract"},
            "targets": [
                {
                    "id": "web",
                    "platform": "web",
                    "backend": "playwright",
                    "base_url": "https://staging.example.com",
                }
            ],
            "steps": [step],
        }
    )
