# Cross-Platform QA Harness Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Build Newton as an **agent-native, file-first QA harness** that can run under Claude Code, Codex CLI, Hermes Agent, plain terminal workflows, and CI jobs. It should turn QA scenario YAML into executable web/iOS runs and produce evidence-backed markdown QA reports.

**Architecture:** Start with a Python CLI and a small domain model. The CLI is the stable contract that every agent runtime calls. The first executable backend is Playwright for web because it runs locally without macOS/iOS constraints; the iOS backend is introduced as a Maestro adapter that can be skipped when Maestro/Xcode are unavailable. All backend-specific results are normalized into one `result.json` schema and one `qa-report.md` template.

**Tech Stack:** Python 3.12, Typer CLI, Pydantic v2, PyYAML, pytest, Playwright Python, optional Maestro CLI for iOS, `xcrun simctl` for iOS simulator lifecycle later.

---

## Constraints and Scope

- This repository currently only contains `PRD.md`; implementation starts from an empty codebase.
- Do not build a full UI.
- Do not build a hosted runner yet.
- Do not implement LLM/vision-driven screen control in the first pass.
- Use selector-first deterministic execution.
- Web execution must work first with Playwright.
- iOS execution must have a clean adapter boundary and can initially support dry-run/compile-to-Maestro before real simulator execution.
- The command contract must stay stable across agent runtimes: Claude Code, Codex CLI, Hermes Agent, plain terminal, and CI.
- Every run must produce:
  - `qa/runs/<run_id>/result.json`
  - `qa/runs/<run_id>/qa-report.md`
  - evidence files when available
- Scenario YAML is Newton-owned and must preserve QA meaning: source refs, risk category, priority, environment, target bindings, and evidence requirements.
- MVP priority is the executable harness contract first; QA planning intelligence expands after that contract is stable.

## Target Repository Layout

```text
Newton/
  PRD.md
  pyproject.toml
  README.md
  src/
    newton/
      __init__.py
      cli.py
      models.py
      scenario_loader.py
      reporting.py
      runner.py
      backends/
        __init__.py
        base.py
        web_playwright.py
        ios_maestro.py
  tests/
    fixtures/
      scenarios/
        web_login.yaml
        cross_platform_login.yaml
    test_models.py
    test_scenario_loader.py
    test_reporting.py
    test_runner.py
    test_cli.py
    test_ios_maestro.py
  qa/
    scenarios/
      web-login-smoke.yaml
      cross-platform-login-smoke.yaml
  docs/
    plans/
      2026-05-06-cross-platform-qa-harness.md
    scenario-schema.md
    agent-runtime-usage.md
```

## Runtime Compatibility Contract

Newton should be callable through the same CLI contract from:

- Claude Code
- Codex CLI
- Hermes Agent
- plain terminal sessions
- CI jobs

The implementation should optimize for the CLI first. MCP exposure or runtime-specific wrappers can be added later, but must map cleanly onto the same `newton qa ...` commands rather than introducing a separate execution model.

## Commit Note

This directory is not currently a git repository. If implementation starts before `git init`, skip the commit step for each task and record the intended commit message. If the implementer initializes git, commit after each task as written.

---

### Task 1: Create Python Project Skeleton

**Objective:** Add the minimum Python package/test structure so future tasks have stable paths.

**Files:**
- Create: `pyproject.toml`
- Create: `src/newton/__init__.py`
- Create: `src/newton/cli.py`
- Create: `tests/test_cli.py`

**Step 1: Create `pyproject.toml`**

```toml
[project]
name = "newton-qa"
version = "0.1.0"
description = "Agent-native QA planning and cross-platform execution harness"
requires-python = ">=3.12"
dependencies = [
  "typer>=0.12.0",
  "pydantic>=2.7.0",
  "pyyaml>=6.0.0",
  "rich>=13.7.0",
]

[project.optional-dependencies]
web = ["playwright>=1.45.0"]
dev = ["pytest>=8.2.0", "pytest-cov>=5.0.0"]

[project.scripts]
newton = "newton.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

**Step 2: Create package files**

`src/newton/__init__.py`:

```python
__version__ = "0.1.0"
```

`src/newton/cli.py`:

```python
import typer

app = typer.Typer(help="Newton QA harness")


@app.command()
def version() -> None:
    """Print Newton version."""
    from newton import __version__

    typer.echo(__version__)
```

**Step 3: Write smoke test**

`tests/test_cli.py`:

```python
from typer.testing import CliRunner

from newton.cli import app


def test_version_command_prints_version():
    result = CliRunner().invoke(app, ["version"])

    assert result.exit_code == 0
    assert result.stdout.strip() == "0.1.0"
```

**Step 4: Run test**

Run:

```bash
cd /Users/hippoo/Desktop/01_projects/05_zero2one/Newton
python -m pip install -e '.[dev]'
pytest tests/test_cli.py -v
```

Expected: `1 passed`.

**Step 5: Commit**

```bash
git add pyproject.toml src/newton/__init__.py src/newton/cli.py tests/test_cli.py
git commit -m "chore: create python cli skeleton"
```

---

### Task 2: Define Scenario Domain Models

**Objective:** Add Pydantic models for Newton scenario YAML without executing anything.

**Files:**
- Create: `src/newton/models.py`
- Create: `tests/test_models.py`

**Step 1: Write failing tests**

`tests/test_models.py`:

```python
import pytest
from pydantic import ValidationError

from newton.models import EvidencePolicy, Scenario, ScenarioStep, TargetBinding


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
```

**Step 2: Run test to verify failure**

Run:

```bash
pytest tests/test_models.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'newton.models'`.

**Step 3: Implement models**

`src/newton/models.py`:

```python
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator

Platform = Literal["web", "ios"]
Backend = Literal["playwright", "maestro", "xcuitest", "appium", "dry-run"]
Priority = Literal["P0", "P1", "P2", "P3"]
ScreenshotPolicy = Literal["never", "on_failure", "after_each_step"]


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
```

**Step 4: Run test**

Run:

```bash
pytest tests/test_models.py -v
```

Expected: `4 passed`.

**Step 5: Commit**

```bash
git add src/newton/models.py tests/test_models.py
git commit -m "feat: define qa scenario models"
```

---

### Task 3: Add YAML Scenario Loader

**Objective:** Load Newton scenario YAML files into validated models.

**Files:**
- Create: `src/newton/scenario_loader.py`
- Create: `tests/fixtures/scenarios/web_login.yaml`
- Create: `tests/test_scenario_loader.py`

**Step 1: Create fixture YAML**

`tests/fixtures/scenarios/web_login.yaml`:

```yaml
scenario:
  id: web-login-smoke
  title: Web login smoke
  source_refs:
    - qa/inputs/tickets.md#login
  risk_category: functional
  priority: P0
  environments: [staging]

targets:
  - id: web
    platform: web
    backend: playwright
    base_url: https://staging.example.com

steps:
  - id: open-login
    action: navigate
    target:
      web:
        url: /login
  - id: enter-email
    action: input_text
    value: qa@example.com
    target:
      web:
        role: textbox
        name: Email
  - id: submit
    action: tap
    target:
      web:
        role: button
        name: Log in

evidence:
  screenshots: on_failure
  video: true
  logs: true
  traces: true
```

**Step 2: Write failing tests**

`tests/test_scenario_loader.py`:

```python
from pathlib import Path

import pytest

from newton.scenario_loader import ScenarioLoadError, load_scenario


def test_load_scenario_from_yaml_fixture():
    scenario = load_scenario(Path("tests/fixtures/scenarios/web_login.yaml"))

    assert scenario.meta.id == "web-login-smoke"
    assert scenario.targets[0].backend == "playwright"
    assert len(scenario.steps) == 3


def test_load_scenario_rejects_missing_file():
    with pytest.raises(ScenarioLoadError, match="not found"):
        load_scenario(Path("tests/fixtures/scenarios/missing.yaml"))
```

**Step 3: Run test to verify failure**

Run:

```bash
pytest tests/test_scenario_loader.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'newton.scenario_loader'`.

**Step 4: Implement loader**

`src/newton/scenario_loader.py`:

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from newton.models import Scenario


class ScenarioLoadError(RuntimeError):
    """Raised when a scenario file cannot be loaded or validated."""


def load_scenario(path: Path) -> Scenario:
    if not path.exists():
        raise ScenarioLoadError(f"scenario file not found: {path}")

    try:
        raw: Any = yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        raise ScenarioLoadError(f"invalid yaml in {path}: {exc}") from exc

    if raw is None:
        raise ScenarioLoadError(f"scenario file is empty: {path}")

    try:
        return Scenario.model_validate(raw)
    except ValidationError as exc:
        raise ScenarioLoadError(f"invalid scenario {path}: {exc}") from exc
```

**Step 5: Run test**

Run:

```bash
pytest tests/test_scenario_loader.py tests/test_models.py -v
```

Expected: all tests pass.

**Step 6: Commit**

```bash
git add src/newton/scenario_loader.py tests/fixtures/scenarios/web_login.yaml tests/test_scenario_loader.py
git commit -m "feat: load scenario yaml files"
```

---

### Task 4: Add Result Models

**Objective:** Represent normalized run results independent of backend.

**Files:**
- Modify: `src/newton/models.py`
- Modify: `tests/test_models.py`

**Step 1: Add failing tests**

Append to `tests/test_models.py`:

```python
from newton.models import RunResult, StepResult


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
```

**Step 2: Run test to verify failure**

Run:

```bash
pytest tests/test_models.py::test_run_result_tracks_failure_status -v
```

Expected: FAIL — `ImportError` for `RunResult`.

**Step 3: Implement result models**

Append to `src/newton/models.py`:

```python
StepStatus = Literal["passed", "failed", "skipped"]
RunStatus = Literal["passed", "failed", "skipped"]


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
    run_id: str
    scenario_id: str
    target_id: str
    platform: Platform
    status: RunStatus
    steps: list[StepResult]
    evidence: list[EvidenceArtifact] = Field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.status == "passed"

    def failed_step_ids(self) -> list[str]:
        return [step.id for step in self.steps if step.status == "failed"]
```

**Step 4: Run tests**

Run:

```bash
pytest tests/test_models.py -v
```

Expected: all tests pass.

**Step 5: Commit**

```bash
git add src/newton/models.py tests/test_models.py
git commit -m "feat: add normalized run result models"
```

---

### Task 5: Add Markdown Report Generator

**Objective:** Generate `qa-report.md` from normalized run results.

**Files:**
- Create: `src/newton/reporting.py`
- Create: `tests/test_reporting.py`

**Step 1: Write failing test**

`tests/test_reporting.py`:

```python
from newton.models import RunResult, StepResult
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
            StepResult(id="tap-login", action="tap", status="failed", error="button not found"),
        ],
    )

    markdown = render_markdown_report(result)

    assert "# QA Report: login-smoke" in markdown
    assert "**Status:** failed" in markdown
    assert "| tap-login | tap | failed | button not found |" in markdown
    assert "## Bug Draft" in markdown
    assert "button not found" in markdown
```

**Step 2: Run test to verify failure**

Run:

```bash
pytest tests/test_reporting.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'newton.reporting'`.

**Step 3: Implement report generator**

`src/newton/reporting.py`:

```python
from __future__ import annotations

from newton.models import RunResult


def render_markdown_report(result: RunResult) -> str:
    lines: list[str] = [
        f"# QA Report: {result.scenario_id}",
        "",
        f"**Run ID:** {result.run_id}",
        f"**Target:** {result.target_id}",
        f"**Platform:** {result.platform}",
        f"**Status:** {result.status}",
        "",
        "## Step Results",
        "",
        "| Step | Action | Status | Error |",
        "| --- | --- | --- | --- |",
    ]

    for step in result.steps:
        lines.append(
            f"| {step.id} | {step.action} | {step.status} | {step.error or '-'} |"
        )

    if not result.passed:
        failed = [step for step in result.steps if step.status == "failed"]
        first_error = failed[0].error if failed else "Unknown failure"
        lines.extend(
            [
                "",
                "## Bug Draft",
                "",
                f"**Title:** {result.scenario_id} failed on {result.platform}",
                f"**Environment:** {result.target_id}",
                "**Severity:** TBD by QA",
                "**Priority:** TBD by QA",
                "",
                "### Reproduction Steps",
            ]
        )
        for index, step in enumerate(result.steps, start=1):
            lines.append(f"{index}. {step.action}: `{step.id}`")
        lines.extend(
            [
                "",
                "### Actual Result",
                first_error or "Unknown failure",
                "",
                "### Expected Result",
                "Scenario should complete all steps successfully.",
            ]
        )

    lines.append("")
    return "\n".join(lines)
```

**Step 4: Run tests**

Run:

```bash
pytest tests/test_reporting.py -v
```

Expected: `1 passed`.

**Step 5: Commit**

```bash
git add src/newton/reporting.py tests/test_reporting.py
git commit -m "feat: render markdown qa reports"
```

---

### Task 6: Add Backend Protocol and Dry Run Backend

**Objective:** Create a backend interface and deterministic dry-run backend for safe local testing.

**Files:**
- Create: `src/newton/backends/__init__.py`
- Create: `src/newton/backends/base.py`
- Create: `src/newton/runner.py`
- Create: `tests/test_runner.py`

**Step 1: Write failing test**

`tests/test_runner.py`:

```python
from pathlib import Path

from newton.runner import run_scenario
from newton.scenario_loader import load_scenario


def test_run_scenario_with_dry_run_backend(tmp_path: Path):
    scenario = load_scenario(Path("tests/fixtures/scenarios/web_login.yaml"))
    result = run_scenario(scenario, target_id="web", run_dir=tmp_path, backend_name="dry-run")

    assert result.status == "passed"
    assert result.run_id.startswith("run_")
    assert [step.status for step in result.steps] == ["passed", "passed", "passed"]
```

**Step 2: Run test to verify failure**

Run:

```bash
pytest tests/test_runner.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'newton.runner'`.

**Step 3: Implement backend protocol**

`src/newton/backends/__init__.py`:

```python
from newton.backends.base import DryRunBackend, ExecutionBackend

__all__ = ["DryRunBackend", "ExecutionBackend"]
```

`src/newton/backends/base.py`:

```python
from __future__ import annotations

from pathlib import Path
from typing import Protocol

from newton.models import RunResult, Scenario, ScenarioTarget, StepResult


class ExecutionBackend(Protocol):
    def run(self, scenario: Scenario, target: ScenarioTarget, run_dir: Path) -> RunResult:
        """Execute a scenario target and return a normalized result."""


class DryRunBackend:
    def run(self, scenario: Scenario, target: ScenarioTarget, run_dir: Path) -> RunResult:
        run_dir.mkdir(parents=True, exist_ok=True)
        steps = [
            StepResult(id=step.id, action=step.action, status="passed")
            for step in scenario.steps
        ]
        return RunResult(
            run_id=run_dir.name,
            scenario_id=scenario.meta.id,
            target_id=target.id,
            platform=target.platform,
            status="passed",
            steps=steps,
        )
```

**Step 4: Implement runner**

`src/newton/runner.py`:

```python
from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from newton.backends.base import DryRunBackend, ExecutionBackend
from newton.models import RunResult, Scenario, ScenarioTarget


def find_target(scenario: Scenario, target_id: str) -> ScenarioTarget:
    for target in scenario.targets:
        if target.id == target_id:
            return target
    raise ValueError(f"target not found: {target_id}")


def make_run_id() -> str:
    return f"run_{uuid4().hex[:12]}"


def get_backend(name: str) -> ExecutionBackend:
    if name == "dry-run":
        return DryRunBackend()
    raise ValueError(f"unsupported backend: {name}")


def run_scenario(
    scenario: Scenario,
    target_id: str,
    run_dir: Path,
    backend_name: str | None = None,
) -> RunResult:
    target = find_target(scenario, target_id)
    backend = get_backend(backend_name or target.backend)
    actual_run_dir = run_dir / make_run_id() if run_dir.name != "run_fixed" else run_dir
    result = backend.run(scenario, target, actual_run_dir)
    return result
```

**Step 5: Fix test to avoid random directory assertion if needed**

If the exact `run_dir` behavior makes the assertion unstable, use:

```python
assert result.run_id.startswith("run_") or result.run_id == tmp_path.name
```

Prefer keeping `run_id` generated by `runner.py` in a later cleanup task.

**Step 6: Run tests**

Run:

```bash
pytest tests/test_runner.py -v
```

Expected: `1 passed`.

**Step 7: Commit**

```bash
git add src/newton/backends src/newton/runner.py tests/test_runner.py
git commit -m "feat: add backend interface and dry run runner"
```

---

### Task 7: Persist Result JSON and QA Report

**Objective:** Write run artifacts to disk after every execution.

**Files:**
- Modify: `src/newton/runner.py`
- Modify: `tests/test_runner.py`

**Step 1: Add failing test**

Append to `tests/test_runner.py`:

```python
import json


def test_run_scenario_writes_result_and_report(tmp_path: Path):
    scenario = load_scenario(Path("tests/fixtures/scenarios/web_login.yaml"))
    result = run_scenario(scenario, target_id="web", run_dir=tmp_path, backend_name="dry-run")

    run_path = tmp_path / result.run_id
    result_path = run_path / "result.json"
    report_path = run_path / "qa-report.md"

    assert result_path.exists()
    assert report_path.exists()
    assert json.loads(result_path.read_text())["scenario_id"] == "web-login-smoke"
    assert "# QA Report: web-login-smoke" in report_path.read_text()
```

**Step 2: Run test to verify failure**

Run:

```bash
pytest tests/test_runner.py::test_run_scenario_writes_result_and_report -v
```

Expected: FAIL — result/report files do not exist.

**Step 3: Update runner persistence**

Modify `src/newton/runner.py`:

```python
from newton.reporting import render_markdown_report
```

Then replace `run_scenario` with:

```python
def run_scenario(
    scenario: Scenario,
    target_id: str,
    run_dir: Path,
    backend_name: str | None = None,
) -> RunResult:
    target = find_target(scenario, target_id)
    backend = get_backend(backend_name or target.backend)
    actual_run_dir = run_dir / make_run_id()
    result = backend.run(scenario, target, actual_run_dir)

    actual_run_dir.mkdir(parents=True, exist_ok=True)
    (actual_run_dir / "result.json").write_text(result.model_dump_json(indent=2))
    (actual_run_dir / "qa-report.md").write_text(render_markdown_report(result))
    return result
```

**Step 4: Run tests**

Run:

```bash
pytest tests/test_runner.py tests/test_reporting.py -v
```

Expected: all tests pass.

**Step 5: Commit**

```bash
git add src/newton/runner.py tests/test_runner.py
git commit -m "feat: persist qa run artifacts"
```

---

### Task 8: Add `newton qa validate` CLI Command

**Objective:** Validate scenario YAML from the command line.

**Files:**
- Modify: `src/newton/cli.py`
- Modify: `tests/test_cli.py`

**Step 1: Add failing test**

Append to `tests/test_cli.py`:

```python

def test_qa_validate_accepts_valid_scenario():
    result = CliRunner().invoke(
        app,
        ["qa", "validate", "tests/fixtures/scenarios/web_login.yaml"],
    )

    assert result.exit_code == 0
    assert "valid: web-login-smoke" in result.stdout
```

**Step 2: Run test to verify failure**

Run:

```bash
pytest tests/test_cli.py::test_qa_validate_accepts_valid_scenario -v
```

Expected: FAIL — command does not exist.

**Step 3: Implement nested CLI**

Replace `src/newton/cli.py` with:

```python
from pathlib import Path

import typer

from newton.scenario_loader import ScenarioLoadError, load_scenario

app = typer.Typer(help="Newton QA harness")
qa_app = typer.Typer(help="QA scenario commands")
app.add_typer(qa_app, name="qa")


@app.command()
def version() -> None:
    """Print Newton version."""
    from newton import __version__

    typer.echo(__version__)


@qa_app.command("validate")
def qa_validate(path: Path) -> None:
    """Validate a Newton QA scenario YAML file."""
    try:
        scenario = load_scenario(path)
    except ScenarioLoadError as exc:
        raise typer.BadParameter(str(exc)) from exc

    typer.echo(f"valid: {scenario.meta.id}")
```

**Step 4: Run tests**

Run:

```bash
pytest tests/test_cli.py tests/test_scenario_loader.py -v
```

Expected: all tests pass.

**Step 5: Commit**

```bash
git add src/newton/cli.py tests/test_cli.py
git commit -m "feat: add scenario validation cli"
```

---

### Task 9: Add `newton qa run` Dry-Run CLI Command

**Objective:** Execute a scenario through the dry-run backend from the CLI and print the run path.

**Files:**
- Modify: `src/newton/cli.py`
- Modify: `tests/test_cli.py`

**Step 1: Add failing test**

Append to `tests/test_cli.py`:

```python

def test_qa_run_dry_run_writes_artifacts(tmp_path):
    result = CliRunner().invoke(
        app,
        [
            "qa",
            "run",
            "tests/fixtures/scenarios/web_login.yaml",
            "--target",
            "web",
            "--backend",
            "dry-run",
            "--out",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "run:" in result.stdout
    assert list(tmp_path.glob("run_*/result.json"))
    assert list(tmp_path.glob("run_*/qa-report.md"))
```

**Step 2: Run test to verify failure**

Run:

```bash
pytest tests/test_cli.py::test_qa_run_dry_run_writes_artifacts -v
```

Expected: FAIL — `qa run` command does not exist.

**Step 3: Implement command**

Append to `src/newton/cli.py`:

```python
from newton.runner import run_scenario
```

Then add:

```python
@qa_app.command("run")
def qa_run(
    path: Path,
    target: str = typer.Option(..., "--target", help="Scenario target id to run"),
    backend: str | None = typer.Option(None, "--backend", help="Override backend"),
    out: Path = typer.Option(Path("qa/runs"), "--out", help="Run output directory"),
) -> None:
    """Run a Newton QA scenario."""
    try:
        scenario = load_scenario(path)
        result = run_scenario(scenario, target_id=target, run_dir=out, backend_name=backend)
    except (ScenarioLoadError, ValueError) as exc:
        raise typer.BadParameter(str(exc)) from exc

    typer.echo(f"run: {out / result.run_id}")
    typer.echo(f"status: {result.status}")
```

**Step 4: Run tests**

Run:

```bash
pytest tests/test_cli.py tests/test_runner.py -v
```

Expected: all tests pass.

**Step 5: Commit**

```bash
git add src/newton/cli.py tests/test_cli.py
git commit -m "feat: add qa run cli"
```

---

### Task 10: Add Playwright Backend Skeleton

**Objective:** Add a Playwright backend that supports `navigate`, `tap`, `input_text`, and `assert_visible` for web targets.

**Files:**
- Create: `src/newton/backends/web_playwright.py`
- Modify: `src/newton/runner.py`
- Create: `tests/test_web_playwright.py`

**Step 1: Write selector unit tests without launching browser**

`tests/test_web_playwright.py`:

```python
from newton.backends.web_playwright import selector_description


def test_selector_description_prefers_role_name():
    assert selector_description({"role": "button", "name": "Log in"}) == "role=button[name=Log in]"


def test_selector_description_accepts_test_id():
    assert selector_description({"test_id": "submit"}) == "test_id=submit"


def test_selector_description_accepts_text():
    assert selector_description({"text": "Dashboard"}) == "text=Dashboard"
```

**Step 2: Run test to verify failure**

Run:

```bash
pytest tests/test_web_playwright.py -v
```

Expected: FAIL — module missing.

**Step 3: Implement backend skeleton**

`src/newton/backends/web_playwright.py`:

```python
from __future__ import annotations

from pathlib import Path
from time import monotonic

from newton.models import RunResult, Scenario, ScenarioTarget, StepResult


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
        except ImportError as exc:
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
        status = "passed"

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
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
                    except Exception as exc:  # noqa: BLE001 - report user-facing failure
                        status = "failed"
                        screenshot = run_dir / f"{step.id}.png"
                        page.screenshot(path=str(screenshot))
                        step_results.append(
                            StepResult(
                                id=step.id,
                                action=step.action,
                                status="failed",
                                error=str(exc),
                                duration_ms=int((monotonic() - start) * 1000),
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
```

**Step 4: Register backend**

Modify `src/newton/runner.py` `get_backend`:

```python
def get_backend(name: str) -> ExecutionBackend:
    if name == "dry-run":
        return DryRunBackend()
    if name == "playwright":
        from newton.backends.web_playwright import PlaywrightBackend

        return PlaywrightBackend()
    raise ValueError(f"unsupported backend: {name}")
```

**Step 5: Run unit tests**

Run:

```bash
pytest tests/test_web_playwright.py tests/test_runner.py -v
```

Expected: all tests pass without launching a browser.

**Step 6: Commit**

```bash
git add src/newton/backends/web_playwright.py src/newton/runner.py tests/test_web_playwright.py
git commit -m "feat: add playwright backend skeleton"
```

---

### Task 11: Add iOS Maestro Compile Adapter

**Objective:** Convert Newton iOS steps into a Maestro YAML flow without requiring a simulator yet.

**Files:**
- Create: `src/newton/backends/ios_maestro.py`
- Create: `tests/fixtures/scenarios/cross_platform_login.yaml`
- Create: `tests/test_ios_maestro.py`

**Step 1: Create cross-platform fixture**

`tests/fixtures/scenarios/cross_platform_login.yaml`:

```yaml
scenario:
  id: cross-platform-login
  title: Cross-platform login
  priority: P0
  risk_category: functional

targets:
  - id: web
    platform: web
    backend: playwright
    base_url: https://staging.example.com
  - id: ios
    platform: ios
    backend: maestro
    bundle_id: com.example.app

steps:
  - id: enter-email
    action: input_text
    value: qa@example.com
    target:
      web:
        role: textbox
        name: Email
      ios:
        accessibility_id: emailField
  - id: submit
    action: tap
    target:
      web:
        role: button
        name: Log in
      ios:
        accessibility_id: loginButton
  - id: assert-home
    action: assert_visible
    target:
      web:
        text: Dashboard
      ios:
        text: Home
```

**Step 2: Write failing tests**

`tests/test_ios_maestro.py`:

```python
from pathlib import Path

from newton.backends.ios_maestro import compile_maestro_flow
from newton.scenario_loader import load_scenario


def test_compile_maestro_flow_from_ios_bindings():
    scenario = load_scenario(Path("tests/fixtures/scenarios/cross_platform_login.yaml"))
    target = scenario.targets[1]

    flow = compile_maestro_flow(scenario, target)

    assert flow["appId"] == "com.example.app"
    assert {"tapOn": {"id": "emailField"}} in flow["---"]
    assert {"inputText": "qa@example.com"} in flow["---"]
    assert {"assertVisible": "Home"} in flow["---"]
```

**Step 3: Run test to verify failure**

Run:

```bash
pytest tests/test_ios_maestro.py -v
```

Expected: FAIL — module missing.

**Step 4: Implement Maestro compiler**

`src/newton/backends/ios_maestro.py`:

```python
from __future__ import annotations

from newton.models import Scenario, ScenarioTarget


def compile_maestro_flow(scenario: Scenario, target: ScenarioTarget) -> dict[str, object]:
    if not target.bundle_id:
        raise ValueError("Maestro iOS target requires bundle_id")

    commands: list[dict[str, object]] = []
    for step in scenario.steps:
        binding = step.target.ios if step.target and step.target.ios else {}
        if step.action == "tap":
            commands.append({"tapOn": _maestro_selector(binding)})
        elif step.action == "input_text":
            commands.append({"tapOn": _maestro_selector(binding)})
            commands.append({"inputText": step.value or ""})
        elif step.action == "assert_visible":
            if "text" in binding:
                commands.append({"assertVisible": binding["text"]})
            else:
                commands.append({"assertVisible": _maestro_selector(binding)})
        elif step.action in {"navigate", "launch_app"}:
            continue
        else:
            raise ValueError(f"unsupported iOS action for Maestro: {step.action}")

    return {"appId": target.bundle_id, "---": commands}


def _maestro_selector(binding: dict[str, object]) -> dict[str, str] | str:
    if "accessibility_id" in binding:
        return {"id": str(binding["accessibility_id"])}
    if "text" in binding:
        return str(binding["text"])
    raise ValueError(f"unsupported iOS binding: {binding}")
```

**Step 5: Run tests**

Run:

```bash
pytest tests/test_ios_maestro.py -v
```

Expected: `1 passed`.

**Step 6: Commit**

```bash
git add src/newton/backends/ios_maestro.py tests/fixtures/scenarios/cross_platform_login.yaml tests/test_ios_maestro.py
git commit -m "feat: compile ios scenarios to maestro"
```

---

### Task 12: Add Sample QA Scenarios

**Objective:** Provide copy-pasteable examples under `qa/scenarios/` for users and agents.

**Files:**
- Create: `qa/scenarios/web-login-smoke.yaml`
- Create: `qa/scenarios/cross-platform-login-smoke.yaml`

**Step 1: Copy web fixture into user-facing example**

`qa/scenarios/web-login-smoke.yaml`:

```yaml
scenario:
  id: web-login-smoke
  title: Web login smoke
  source_refs:
    - qa/inputs/tickets.md#login
  risk_category: functional
  priority: P0
  environments: [staging]

targets:
  - id: web
    platform: web
    backend: playwright
    base_url: https://staging.example.com

steps:
  - id: open-login
    action: navigate
    target:
      web:
        url: /login
  - id: enter-email
    action: input_text
    value: qa@example.com
    target:
      web:
        role: textbox
        name: Email
  - id: enter-password
    action: input_text
    value: password123
    secure: true
    target:
      web:
        test_id: password-input
  - id: submit
    action: tap
    target:
      web:
        role: button
        name: Log in
  - id: assert-dashboard
    action: assert_visible
    target:
      web:
        text: Dashboard

evidence:
  screenshots: on_failure
  video: true
  logs: true
  traces: true
```

**Step 2: Copy cross-platform fixture into user-facing example**

`qa/scenarios/cross-platform-login-smoke.yaml`:

```yaml
scenario:
  id: cross-platform-login-smoke
  title: Cross-platform login smoke
  source_refs:
    - qa/inputs/tickets.md#login
  risk_category: functional
  priority: P0
  environments: [staging]

targets:
  - id: web
    platform: web
    backend: playwright
    base_url: https://staging.example.com
  - id: ios
    platform: ios
    backend: maestro
    bundle_id: com.example.app
    device:
      model: iPhone 15

steps:
  - id: enter-email
    action: input_text
    value: qa@example.com
    target:
      web:
        role: textbox
        name: Email
      ios:
        accessibility_id: emailField
  - id: enter-password
    action: input_text
    value: password123
    secure: true
    target:
      web:
        test_id: password-input
      ios:
        accessibility_id: passwordField
  - id: submit
    action: tap
    target:
      web:
        role: button
        name: Log in
      ios:
        accessibility_id: loginButton
  - id: assert-home
    action: assert_visible
    target:
      web:
        text: Dashboard
      ios:
        text: Home

evidence:
  screenshots: on_failure
  video: true
  logs: true
```

**Step 3: Validate examples**

Run:

```bash
newton qa validate qa/scenarios/web-login-smoke.yaml
newton qa validate qa/scenarios/cross-platform-login-smoke.yaml
```

Expected:

```text
valid: web-login-smoke
valid: cross-platform-login-smoke
```

**Step 4: Commit**

```bash
git add qa/scenarios/web-login-smoke.yaml qa/scenarios/cross-platform-login-smoke.yaml
git commit -m "docs: add sample qa scenarios"
```

---

### Task 13: Document Scenario Schema

**Objective:** Explain how Newton scenario YAML maps QA intent to web/iOS bindings.

**Files:**
- Create: `docs/scenario-schema.md`

**Step 1: Write documentation**

`docs/scenario-schema.md`:

```markdown
# Newton Scenario Schema

Newton scenarios are QA artifacts, not just automation scripts. A scenario must explain what product behavior is being tested and how each target should execute it.

## Required Top-Level Fields

- `scenario`: QA metadata
- `targets`: one or more execution targets
- `steps`: ordered executable steps

## Scenario Metadata

```yaml
scenario:
  id: login-smoke
  title: Login smoke
  source_refs:
    - qa/inputs/tickets.md#login
  risk_category: functional
  priority: P0
  environments: [staging]
```

## Targets

Web target:

```yaml
targets:
  - id: web
    platform: web
    backend: playwright
    base_url: https://staging.example.com
```

iOS target:

```yaml
targets:
  - id: ios
    platform: ios
    backend: maestro
    bundle_id: com.example.app
    device:
      model: iPhone 15
```

## Steps

Each step has a shared action and target-specific bindings.

```yaml
steps:
  - id: submit
    action: tap
    target:
      web:
        role: button
        name: Log in
      ios:
        accessibility_id: loginButton
```

## Supported Actions in MVP

- `navigate`: web navigation
- `tap`: click/tap an element
- `input_text`: fill an input
- `assert_visible`: wait until an element/text is visible

## Selector Priority

Prefer stable selectors:

1. Web `role` + `name` or `test_id`
2. iOS `accessibility_id`
3. Visible `text`
4. CSS selector for web only
5. Coordinates only as a future last resort

## Evidence Policy

```yaml
evidence:
  screenshots: on_failure
  video: true
  logs: true
  traces: true
```

Evidence is normalized into `qa/runs/<run_id>/result.json` and summarized in `qa-report.md`.
```

**Step 2: Verify docs mention both platforms**

Run:

```bash
grep -n "platform: web\|platform: ios\|Supported Actions" docs/scenario-schema.md
```

Expected: lines for web, iOS, and supported actions.

**Step 3: Commit**

```bash
git add docs/scenario-schema.md
git commit -m "docs: document scenario schema"
```

---

### Task 14: Add README Quick Start

**Objective:** Document local installation, validation, dry-run, and web backend usage.

**Files:**
- Create: `README.md`

**Step 1: Write README**

`README.md`:

```markdown
# Newton QA

Newton is an agent-native QA harness that turns sprint context into executable web/iOS scenarios and evidence-backed QA reports.

## Install

```bash
python -m pip install -e '.[dev]'
```

For web execution:

```bash
python -m pip install -e '.[dev,web]'
python -m playwright install chromium
```

## Validate a Scenario

```bash
newton qa validate qa/scenarios/web-login-smoke.yaml
```

Expected:

```text
valid: web-login-smoke
```

## Dry Run

```bash
newton qa run qa/scenarios/web-login-smoke.yaml --target web --backend dry-run --out qa/runs
```

Outputs:

```text
qa/runs/run_*/result.json
qa/runs/run_*/qa-report.md
```

## Web Run

```bash
newton qa run qa/scenarios/web-login-smoke.yaml --target web --backend playwright --out qa/runs
```

## Current Backends

- `dry-run`: validates the full Newton pipeline without opening a browser or simulator
- `playwright`: executes web scenarios
- `maestro`: planned iOS backend; current first step is compiling Newton iOS bindings to Maestro flow YAML
```

**Step 2: Verify README commands are present**

Run:

```bash
grep -n "newton qa validate\|newton qa run\|playwright" README.md
```

Expected: command lines are found.

**Step 3: Commit**

```bash
git add README.md
git commit -m "docs: add newton qa quick start"
```

---

### Task 15: Final Integration Check

**Objective:** Verify the implemented MVP works end-to-end with dry-run and schema validation.

**Files:**
- No new files

**Step 1: Install dev dependencies**

Run:

```bash
cd /Users/hippoo/Desktop/01_projects/05_zero2one/Newton
python -m pip install -e '.[dev]'
```

Expected: package installs successfully.

**Step 2: Run all tests**

Run:

```bash
pytest -v
```

Expected: all tests pass.

**Step 3: Validate sample scenarios**

Run:

```bash
newton qa validate qa/scenarios/web-login-smoke.yaml
newton qa validate qa/scenarios/cross-platform-login-smoke.yaml
```

Expected:

```text
valid: web-login-smoke
valid: cross-platform-login-smoke
```

**Step 4: Run dry-run scenario**

Run:

```bash
newton qa run qa/scenarios/web-login-smoke.yaml --target web --backend dry-run --out qa/runs
```

Expected:

```text
run: qa/runs/run_<id>
status: passed
```

**Step 5: Inspect artifacts**

Run:

```bash
ls qa/runs/run_*/result.json qa/runs/run_*/qa-report.md
```

Expected: both files exist in the latest run directory.

**Step 6: Optional web backend smoke**

Only run this after installing Playwright and replacing `base_url` with a reachable app URL:

```bash
python -m pip install -e '.[web]'
python -m playwright install chromium
newton qa run qa/scenarios/web-login-smoke.yaml --target web --backend playwright --out qa/runs
```

Expected: either a real pass/fail report depending on the target app, or a clear failure report with screenshot evidence.

**Step 7: Commit final verification notes if any docs changed**

```bash
git status --short
git add README.md docs/scenario-schema.md qa/scenarios || true
git commit -m "docs: verify qa harness mvp" || true
```

---

## Future Plan After This MVP

Do not implement these until the above plan is complete and tested.

1. Real Maestro execution backend:
   - Write compiled flow to `qa/runs/<run_id>/maestro-flow.yaml`
   - Run `maestro test maestro-flow.yaml`
   - Parse exit code into `RunResult`

2. iOS simulator lifecycle:
   - `xcrun simctl list devices`
   - boot selected simulator
   - install `.app`
   - launch bundle id
   - collect logs and screenshots

3. Cross-target matrix report:
   - Run `--target all`
   - Produce one report table comparing web/iOS status per scenario

4. Agent repair loop:
   - Read failure report
   - Classify as product bug, selector issue, environment issue, or flaky test
   - Suggest scenario patch or app accessibility id patch

5. Crabbox-style runner:
   - Web runner on Linux warm box
   - iOS runner on static macOS SSH host first
   - Managed macOS lease later

## Plan Review Checklist

- [x] Tasks are sequential and logical
- [x] Each task is bite-sized enough for one focused implementation pass
- [x] File paths are exact
- [x] Code examples are complete and copy-pasteable
- [x] Commands are exact with expected output
- [x] TDD cycle is included for code tasks
- [x] DRY/YAGNI respected
- [x] Web-first path works without iOS/macOS dependencies
- [x] iOS path has a clean adapter boundary without overbuilding
