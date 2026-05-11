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
            if step.action in {"navigate", "launch_app"}:
                continue
            if step.target is None:
                raise ValueError(f"step '{step.id}' must define a target binding")
            if "web" in platforms and step.target.web is None:
                raise ValueError(f"step '{step.id}' is missing a web target binding")
            if "ios" in platforms and step.target.ios is None:
                raise ValueError(f"step '{step.id}' is missing an ios target binding")
        return self


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
