from __future__ import annotations

from typing import Any, Literal, Mapping

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator

ARTIFACT_CONTRACT_VERSION = "v0.1"

Platform = Literal["web", "ios"]
Backend = Literal["playwright", "maestro", "xcuitest", "appium", "dry-run"]
Priority = Literal["P0", "P1", "P2", "P3"]
ScreenshotPolicy = Literal["never", "on_failure", "after_each_step"]
StepStatus = Literal["passed", "failed", "skipped"]
RunStatus = Literal["passed", "failed", "skipped"]

WEB_ACTIONS = frozenset(
    {
        "navigate",
        "goto",
        "tap",
        "click",
        "input_text",
        "fill",
        "checkbox",
        "select_option",
        "press",
        "upload_file",
        "wait",
        "assert_visible",
        "wait_for_selector",
        "expect_visible",
        "assert_hidden",
        "assert_not_visible",
        "assert_text",
        "assert_url",
        "assert_url_pattern",
        "assert_enabled",
        "assert_disabled",
        "assert_value",
    }
)
WEB_CLICK_ACTIONS = frozenset({"tap", "click"})
WEB_TEXT_ENTRY_ACTIONS = frozenset({"input_text", "fill"})
WEB_CHECKBOX_ACTIONS = frozenset({"checkbox"})
WEB_SELECT_ACTIONS = frozenset({"select_option"})
WEB_KEYBOARD_ACTIONS = frozenset({"press"})
WEB_FILE_UPLOAD_ACTIONS = frozenset({"upload_file"})
WEB_WAIT_ACTIONS = frozenset({"wait"})
WEB_VISIBLE_ASSERTION_ACTIONS = frozenset({"assert_visible", "wait_for_selector", "expect_visible"})
WEB_HIDDEN_ASSERTION_ACTIONS = frozenset({"assert_hidden", "assert_not_visible"})
WEB_STATE_ASSERTION_ACTIONS = frozenset({"assert_enabled", "assert_disabled"})
WEB_VALUE_ASSERTION_ACTIONS = frozenset({"assert_value"})
WEB_LOCATOR_REQUIRED_ACTIONS = frozenset().union(
    WEB_CLICK_ACTIONS,
    WEB_TEXT_ENTRY_ACTIONS,
    WEB_CHECKBOX_ACTIONS,
    WEB_SELECT_ACTIONS,
    WEB_FILE_UPLOAD_ACTIONS,
    WEB_VISIBLE_ASSERTION_ACTIONS,
    WEB_HIDDEN_ASSERTION_ACTIONS,
    WEB_STATE_ASSERTION_ACTIONS,
    WEB_VALUE_ASSERTION_ACTIONS,
)
WEB_URL_ACTIONS = frozenset({"navigate", "goto", "assert_url"})
WEB_URL_PATTERN_ACTIONS = frozenset({"assert_url_pattern"})
WEB_TARGET_OPTIONAL_ACTIONS = frozenset().union(
    WEB_URL_ACTIONS, WEB_URL_PATTERN_ACTIONS, WEB_WAIT_ACTIONS, WEB_KEYBOARD_ACTIONS
)
WEB_SELECTOR_FAMILIES = (
    "role",
    "test_id",
    "text",
    "css",
    "label",
    "placeholder",
    "alt_text",
    "title",
    "url",
    "url_pattern",
)
WEB_LOCATOR_SELECTOR_FAMILIES = (
    "role",
    "test_id",
    "text",
    "css",
    "label",
    "placeholder",
    "alt_text",
    "title",
)
WEB_SELECTOR_ALLOWED_KEYS = {
    "role": frozenset({"role", "name"}),
    "test_id": frozenset({"test_id"}),
    "text": frozenset({"text"}),
    "css": frozenset({"css"}),
    "label": frozenset({"label"}),
    "placeholder": frozenset({"placeholder"}),
    "alt_text": frozenset({"alt_text"}),
    "title": frozenset({"title"}),
    "url": frozenset({"url"}),
    "url_pattern": frozenset({"url_pattern"}),
}


class ArtifactContractVersionError(ValueError):
    """Raised when a Newton artifact is missing or using an unsupported contract version."""


def require_artifact_contract_version(payload: Mapping[str, Any], *, artifact_name: str) -> None:
    version = payload.get("contract_version")
    if not isinstance(version, str) or not version:
        raise ArtifactContractVersionError(
            f"{artifact_name} missing contract_version; regenerate this artifact with Newton "
            f"{ARTIFACT_CONTRACT_VERSION}"
        )
    if version != ARTIFACT_CONTRACT_VERSION:
        raise ArtifactContractVersionError(
            f"{artifact_name} uses unsupported contract_version {version!r}; expected "
            f"{ARTIFACT_CONTRACT_VERSION!r}"
        )


class ScenarioMeta(BaseModel):
    id: str
    title: str
    source_refs: list[str] = Field(default_factory=list)
    risk_category: str = "functional"
    priority: Priority = "P1"
    environments: list[str] = Field(default_factory=lambda: ["local"])

    @field_validator("id")
    @classmethod
    def id_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("scenario id must not be blank")
        return value


class ScenarioTarget(BaseModel):
    id: str
    platform: Platform
    backend: Backend
    base_url: HttpUrl | None = None
    bundle_id: str | None = None
    build: str | None = None
    device: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_backend_contract(self) -> "ScenarioTarget":
        compatibility: dict[Backend, set[Platform]] = {
            "dry-run": {"web", "ios"},
            "playwright": {"web"},
            "maestro": {"ios"},
            "xcuitest": {"ios"},
            "appium": {"ios"},
        }
        supported_platforms = compatibility[self.backend]
        if self.platform not in supported_platforms:
            raise ValueError(
                f"backend '{self.backend}' does not support platform '{self.platform}'"
            )
        if self.platform == "web" and self.base_url is None:
            raise ValueError(f"web target '{self.id}' must define base_url")
        return self


class TargetBinding(BaseModel):
    web: dict[str, Any] | None = None
    ios: dict[str, Any] | None = None


class ScenarioStep(BaseModel):
    id: str
    action: str
    target: TargetBinding | None = None
    value: str | None = None
    timeout_ms: int = 10_000
    secure: bool = False

    @field_validator("timeout_ms")
    @classmethod
    def timeout_must_be_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("timeout_ms must be greater than 0")
        return value


class EvidencePolicy(BaseModel):
    screenshots: ScreenshotPolicy = "on_failure"
    video: bool = False
    logs: bool = True
    traces: bool = False


class ReportPolicy(BaseModel):
    output: str | None = None
    include: list[str] = Field(
        default_factory=lambda: ["summary", "step_results", "evidence", "bug_draft_on_failure"]
    )


class Scenario(BaseModel):
    contract_version: Literal["v0.1"] = ARTIFACT_CONTRACT_VERSION
    meta: ScenarioMeta = Field(alias="scenario")
    targets: list[ScenarioTarget]
    steps: list[ScenarioStep]
    evidence: EvidencePolicy = Field(default_factory=EvidencePolicy)
    report: ReportPolicy = Field(default_factory=ReportPolicy)

    @field_validator("targets")
    @classmethod
    def must_have_target(cls, value: list[ScenarioTarget]) -> list[ScenarioTarget]:
        if not value:
            raise ValueError("scenario must define at least one target")
        return value

    @field_validator("steps")
    @classmethod
    def must_have_step(cls, value: list[ScenarioStep]) -> list[ScenarioStep]:
        if not value:
            raise ValueError("scenario must define at least one step")
        return value

    @model_validator(mode="after")
    def validate_step_bindings(self) -> "Scenario":
        platforms = {target.platform for target in self.targets}
        for step in self.steps:
            if "web" in platforms:
                validate_web_step(step)
            if step.target is None:
                if platforms == {"web"} and step.action in WEB_TARGET_OPTIONAL_ACTIONS:
                    continue
                if step.action in {"navigate", "launch_app"}:
                    continue
                raise ValueError(f"step '{step.id}' must define a target binding")
            if (
                "web" in platforms
                and step.target.web is None
                and step.action not in WEB_TARGET_OPTIONAL_ACTIONS
            ):
                raise ValueError(f"step '{step.id}' is missing a web target binding")
            if "ios" in platforms and step.target.ios is None:
                raise ValueError(f"step '{step.id}' is missing an ios target binding")
        return self


def validate_web_step(step: ScenarioStep) -> None:
    selector = step.target.web if step.target and step.target.web is not None else {}
    if step.action not in WEB_ACTIONS:
        supported = ", ".join(sorted(WEB_ACTIONS))
        raise ValueError(
            _web_step_validation_error(
                step,
                selector,
                f"unsupported web action; supported actions: {supported}",
            )
        )

    if step.action in WEB_LOCATOR_REQUIRED_ACTIONS:
        _validate_web_selector(
            step,
            selector,
            allowed_families=WEB_LOCATOR_SELECTOR_FAMILIES,
            required=True,
        )
        if step.action in WEB_SELECT_ACTIONS | WEB_FILE_UPLOAD_ACTIONS | WEB_VALUE_ASSERTION_ACTIONS:
            _validate_step_value(step, selector, f"{step.action} requires step.value")
        return

    if step.action in WEB_URL_ACTIONS:
        if selector:
            _validate_web_selector(step, selector, allowed_families=("url",), required=False)
        return

    if step.action in WEB_URL_PATTERN_ACTIONS:
        if selector:
            _validate_web_selector(
                step,
                selector,
                allowed_families=("url_pattern",),
                required=False,
            )
        if not _non_blank_string(step.value) and "url_pattern" not in selector:
            raise ValueError(
                _web_step_validation_error(
                    step,
                    selector,
                    "assert_url_pattern requires step.value or target.web.url_pattern",
                )
            )
        return

    if step.action in WEB_WAIT_ACTIONS:
        return

    if step.action in WEB_KEYBOARD_ACTIONS:
        if selector:
            _validate_web_selector(
                step,
                selector,
                allowed_families=WEB_LOCATOR_SELECTOR_FAMILIES,
                required=False,
            )
        _validate_step_value(step, selector, f"{step.action} requires step.value")
        return

    if step.action == "assert_text":
        if selector:
            _validate_web_selector(
                step,
                selector,
                allowed_families=WEB_LOCATOR_SELECTOR_FAMILIES,
                required=False,
            )
        if not _non_blank_string(step.value) and "text" not in selector:
            raise ValueError(
                _web_step_validation_error(
                    step,
                    selector,
                    "assert_text requires step.value or target.web.text",
                )
            )


def _validate_step_value(step: ScenarioStep, selector: dict[str, Any], detail: str) -> None:
    if not _non_blank_string(step.value):
        raise ValueError(_web_step_validation_error(step, selector, detail))


def _validate_web_selector(
    step: ScenarioStep,
    selector: dict[str, Any],
    *,
    allowed_families: tuple[str, ...],
    required: bool,
) -> None:
    families = [family for family in WEB_SELECTOR_FAMILIES if family in selector]
    if not families:
        if required:
            expected = ", ".join(allowed_families)
            raise ValueError(
                _web_step_validation_error(
                    step,
                    selector,
                    f"requires target.web selector using one of: {expected}",
                )
            )
        raise ValueError(
            _web_step_validation_error(
                step,
                selector,
                "uses unsupported web selector family",
            )
        )
    if len(families) > 1:
        raise ValueError(
            _web_step_validation_error(
                step,
                selector,
                f"uses multiple web selector families: {', '.join(families)}",
            )
        )

    family = families[0]
    if family not in allowed_families:
        expected = ", ".join(allowed_families)
        raise ValueError(
            _web_step_validation_error(
                step,
                selector,
                f"selector family '{family}' is not supported for this action; expected one of: {expected}",
            )
        )

    extra_keys = set(selector) - WEB_SELECTOR_ALLOWED_KEYS[family]
    if extra_keys:
        raise ValueError(
            _web_step_validation_error(
                step,
                selector,
                f"unsupported selector field(s): {', '.join(sorted(extra_keys))}",
            )
        )

    if not _non_blank_string(selector[family]):
        raise ValueError(
            _web_step_validation_error(
                step,
                selector,
                f"selector field '{family}' must be a non-blank string",
            )
        )
    if family == "role" and "name" in selector and not _non_blank_string(selector["name"]):
        raise ValueError(
            _web_step_validation_error(
                step,
                selector,
                "selector field 'name' must be a non-blank string when provided",
            )
        )


def _non_blank_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _web_step_validation_error(step: ScenarioStep, selector: dict[str, Any], detail: str) -> str:
    return f"step '{step.id}' action '{step.action}' target.web {selector!r}: {detail}"


class EvidenceArtifact(BaseModel):
    kind: str
    path: str
    description: str | None = None


class StepResult(BaseModel):
    id: str
    action: str
    status: StepStatus
    error: str | None = None
    duration_ms: int | None = None
    evidence: list[EvidenceArtifact] = Field(default_factory=list)


class RunResult(BaseModel):
    contract_version: Literal["v0.1"] = ARTIFACT_CONTRACT_VERSION
    run_id: str
    scenario_id: str
    target_id: str
    platform: Platform
    status: RunStatus
    steps: list[StepResult]
    evidence: list[EvidenceArtifact] = Field(default_factory=list)
    planning: dict[str, str] | None = None

    @property
    def passed(self) -> bool:
        return self.status == "passed"

    def failed_step_ids(self) -> list[str]:
        return [step.id for step in self.steps if step.status == "failed"]

    @classmethod
    def validate_artifact_payload(cls, payload: Mapping[str, Any]) -> "RunResult":
        require_artifact_contract_version(payload, artifact_name="result.json")
        return cls.model_validate(payload)
