from __future__ import annotations

from pathlib import Path

import typer

from newton import __version__
from newton.agent_planning_bundle import AgentPlanningBundleError, generate_planning_bundle_with_agent
from newton.agent_planner import AgentPlanningError, plan_scenario_with_agent
from newton.backends import playwright_setup
from newton.bug_draft import BugDraftError, write_bug_ticket_draft
from newton.bundle_review import DEFAULT_GATE_THRESHOLD, BundleReviewError, review_planning_bundle
from newton.plan_provenance import PlanProvenanceError, write_plan_provenance
from newton.planner import PlanningError, plan_scenario_from_markdown
from newton.planning_bundle import PlanningBundleError, generate_planning_bundle
from newton.planning_bundle_validation import PlanningBundleValidationError, validate_planning_bundle
from newton.run_index import read_run_index
from newton.runner import run_scenario
from newton.scenario_loader import ScenarioLoadError, load_scenario
from newton.tracker_update import TrackerUpdateError, update_tracker_item, update_tracker_item_from_run

app = typer.Typer(help="Newton QA harness")
qa_app = typer.Typer(help="QA scenario commands")
qa_doctor_app = typer.Typer(help="QA setup diagnostics")
app.add_typer(qa_app, name="qa")
qa_app.add_typer(qa_doctor_app, name="doctor")


@app.command()
def version() -> None:
    """Print Newton version."""
    typer.echo(__version__)


@qa_app.command("validate")
def qa_validate(path: Path) -> None:
    """Validate a Newton QA scenario YAML file."""
    try:
        scenario = load_scenario(path)
    except ScenarioLoadError as exc:
        raise typer.BadParameter(str(exc)) from exc

    typer.echo(f"valid: {scenario.meta.id}")


@qa_app.command("plan")
def qa_plan(
    path: Path,
    target: str = typer.Option("web", "--target", help="Comma-separated planning targets: web or web,ios"),
    out: Path = typer.Option(Path("qa/scenarios"), "--out", help="Scenario output directory"),
    base_url: str = typer.Option("http://127.0.0.1:8000", "--base-url", help="Default web target base URL"),
    agent: str = typer.Option("template", "--agent", help="Planning agent: template, codex, or claude"),
    agent_command: str | None = typer.Option(
        None,
        "--agent-command",
        help="Override agent command; prompt is sent on stdin",
        hidden=True,
    ),
) -> None:
    """Generate a validated Newton scenario YAML draft from markdown context."""
    try:
        if agent == "template":
            output_path = plan_scenario_from_markdown(path, target=target, out_dir=out, base_url=base_url)
            write_plan_provenance(
                input_path=path,
                agent="template",
                target=target,
                out_dir=out,
                base_url=base_url,
                prompt_path=None,
                raw_output_path=None,
                accepted_scenario_path=output_path,
                validation_status="accepted",
                validation_error=None,
            )
        else:
            output_path = plan_scenario_with_agent(
                path,
                agent=agent,
                target=target,
                out_dir=out,
                base_url=base_url,
                command=agent_command,
            )
        scenario = load_scenario(output_path)
    except (PlanningError, AgentPlanningError, ScenarioLoadError) as exc:
        raise typer.BadParameter(str(exc)) from exc

    typer.echo(f"planned: {output_path}")
    typer.echo(f"valid: {scenario.meta.id}")


@qa_app.command("plan-bundle")
def qa_plan_bundle(
    path: Path,
    source: list[Path] = typer.Option([], "--source", help="Additional markdown source file to merge into the bundle"),
    agent: str = typer.Option("template", "--agent", help="Planning bundle agent: template, codex, or claude"),
    agent_command: str | None = typer.Option(
        None,
        "--agent-command",
        help="Override agent command; prompt is sent on stdin",
        hidden=True,
    ),
    out: Path = typer.Option(Path("qa/plans"), "--out", help="Planning bundle output directory"),
    bundle_dir_name: str | None = typer.Option(
        None,
        "--bundle-dir-name",
        help="Override generated bundle directory name while preserving manifest plan_id",
    ),
) -> None:
    """Generate a minimal QA planning bundle from markdown context."""
    try:
        if agent == "template":
            bundle_dir = generate_planning_bundle(
                path,
                out_dir=out,
                source_paths=source,
                bundle_dir_name=bundle_dir_name,
            )
        else:
            if bundle_dir_name is not None:
                raise AgentPlanningBundleError("--bundle-dir-name is only supported with --agent template")
            bundle_dir = generate_planning_bundle_with_agent(
                path,
                out_dir=out,
                source_paths=source,
                agent=agent,
                command=agent_command,
            )
    except (PlanningBundleError, AgentPlanningBundleError) as exc:
        raise typer.BadParameter(str(exc)) from exc

    typer.echo(f"bundle: {bundle_dir}")
    typer.echo(f"scope: {bundle_dir / 'qa-scope.md'}")
    typer.echo(f"checklist: {bundle_dir / 'checklist.md'}")
    typer.echo(f"test_cases: {bundle_dir / 'test-cases.csv'}")
    typer.echo(f"risk_map: {bundle_dir / 'risk-map.md'}")
    typer.echo(f"estimate: {bundle_dir / 'qa-estimate.md'}")
    typer.echo(f"automation_candidates: {bundle_dir / 'automation-candidates.md'}")
    typer.echo(f"qa_run_tracker: {bundle_dir / 'qa-run-tracker.md'}")


@qa_app.command("bundle-validate")
def qa_bundle_validate(bundle_dir: Path) -> None:
    """Validate a QA planning bundle artifact contract."""
    try:
        result = validate_planning_bundle(bundle_dir)
    except PlanningBundleValidationError as exc:
        raise typer.BadParameter(str(exc)) from exc

    typer.echo(f"valid_bundle: {result.plan_id}")
    typer.echo(f"artifacts: {result.artifact_count}")
    typer.echo(f"checklist_items: {result.checklist_items}")
    typer.echo(f"test_cases: {result.test_cases}")
    typer.echo(f"tracker_items: {result.tracker_items}")


@qa_app.command("bundle-review")
def qa_bundle_review(
    bundle_dir: Path,
    agent: str = typer.Option("template", "--agent", help="Review agent: template, codex, or claude"),
    agent_command: str | None = typer.Option(
        None,
        "--agent-command",
        help="Override agent command; prompt is sent on stdin",
        hidden=True,
    ),
    gate: bool = typer.Option(False, "--gate", help="Exit non-zero when the review score is below the threshold"),
    gate_threshold: int = typer.Option(
        DEFAULT_GATE_THRESHOLD,
        "--gate-threshold",
        min=0,
        max=100,
        help="Minimum bundle-review score required when --gate is enabled",
    ),
) -> None:
    """Write an advisory QA planning bundle review."""
    try:
        result = review_planning_bundle(
            bundle_dir,
            agent=agent,
            command=agent_command,
            gate=gate,
            gate_threshold=gate_threshold,
        )
    except BundleReviewError as exc:
        raise typer.BadParameter(str(exc)) from exc

    typer.echo(f"review_json: {result.review_json_path}")
    typer.echo(f"review_markdown: {result.review_markdown_path}")
    typer.echo(f"score: {result.score}")
    typer.echo(f"verdict: {result.verdict}")
    if result.gate:
        typer.echo(f"gate_threshold: {result.gate_threshold}")
        typer.echo(f"gate: {'passed' if result.gate_passed else 'failed'}")
        if not result.gate_passed:
            raise typer.Exit(code=1)


@qa_doctor_app.command("web")
def qa_doctor_web() -> None:
    """Check local Playwright web execution setup."""
    result = playwright_setup.check_playwright_setup()
    typer.echo(f"status: {result.status}")
    if result.failure_kind:
        typer.echo(f"failure: {result.failure_kind}")
    for check in result.checks:
        typer.echo(f"{check.name}: {check.status} - {check.message}")
    if result.remediation:
        typer.echo("remediation:")
        for command in result.remediation:
            typer.echo(f"  {command}")
    if not result.ok:
        raise typer.Exit(code=1)


@qa_app.command("bug-draft")
def qa_bug_draft(
    tracker_path: Path,
    out: Path | None = typer.Option(None, "--out", help="Bug ticket draft output path"),
    output_format: str = typer.Option("markdown", "--format", help="Draft format: markdown, linear, or jira"),
) -> None:
    """Generate a bug ticket draft from the first failed tracker item."""
    try:
        output_path = write_bug_ticket_draft(tracker_path, output_path=out, output_format=output_format)
    except BugDraftError as exc:
        raise typer.BadParameter(str(exc)) from exc

    typer.echo(f"bug_ticket_draft: {output_path}")


@qa_app.command("tracker-update")
def qa_tracker_update(
    tracker_path: Path,
    item: int = typer.Option(..., "--item", help="1-based checklist item number to update"),
    env: str = typer.Option(..., "--env", help="Environment: dev, stg, or prod"),
    status: str = typer.Option(..., "--status", help="Status: not run, passed, failed, blocked, or needs retest"),
    notes: str = typer.Option("", "--notes", help="Status notes for the checklist item"),
) -> None:
    """Update one generated QA run tracker checklist item."""
    try:
        updated_path = update_tracker_item(
            tracker_path,
            item_number=item,
            env=env,
            status=status,
            notes=notes,
        )
    except TrackerUpdateError as exc:
        raise typer.BadParameter(str(exc)) from exc

    typer.echo(f"updated_tracker: {updated_path}")


@qa_app.command("tracker-update-from-run")
def qa_tracker_update_from_run(
    tracker_path: Path,
    item: int = typer.Option(..., "--item", help="1-based checklist item number to update"),
    env: str = typer.Option(..., "--env", help="Environment: dev, stg, or prod"),
    run: Path = typer.Option(..., "--run", help="QA run directory containing result.json"),
) -> None:
    """Update one generated QA run tracker checklist item from a run result."""
    try:
        updated_path = update_tracker_item_from_run(
            tracker_path,
            item_number=item,
            env=env,
            run_path=run,
        )
    except TrackerUpdateError as exc:
        raise typer.BadParameter(str(exc)) from exc

    typer.echo(f"updated_tracker: {updated_path}")


@qa_app.command("run")
def qa_run(
    path: Path,
    target: str = typer.Option(..., "--target", help="Scenario target id to run"),
    backend: str | None = typer.Option(None, "--backend", help="Override backend"),
    base_url: str | None = typer.Option(None, "--base-url", help="Override web target base URL"),
    plan_provenance: Path | None = typer.Option(
        None,
        "--plan-provenance",
        help="Accepted qa plan provenance JSON to link into the run report",
    ),
    allow_failure: bool = typer.Option(
        False,
        "--allow-failure",
        help="Exit 0 even when the scenario run does not pass; intended for dogfood and diagnostics",
    ),
    out: Path = typer.Option(Path("qa/runs"), "--out", help="Run output directory"),
) -> None:
    """Run a Newton QA scenario."""
    try:
        scenario = load_scenario(path)
        result = run_scenario(
            scenario,
            target_id=target,
            run_dir=out,
            backend_name=backend,
            base_url=base_url,
            plan_provenance_path=plan_provenance,
            scenario_path=path,
        )
    except (ScenarioLoadError, PlanProvenanceError, ValueError) as exc:
        raise typer.BadParameter(str(exc)) from exc

    typer.echo(f"run: {out / result.run_id}")
    typer.echo(f"status: {result.status}")
    if not result.passed and not allow_failure:
        raise typer.Exit(code=1)


@qa_app.command("report")
def qa_report(run_path: Path) -> None:
    """Print the path to an existing QA report."""
    report_path = run_path / "qa-report.md"
    if not report_path.exists():
        raise typer.BadParameter(f"qa report not found: {report_path}")
    typer.echo(str(report_path))


@qa_app.command("runs")
def qa_runs(out: Path = typer.Option(Path("qa/runs"), "--out", help="Run output directory")) -> None:
    """List locally indexed QA runs."""
    for entry in read_run_index(out):
        typer.echo(
            f"{entry['run_id']}  {entry['status']}  {entry['scenario_id']}  {entry['target_id']}"
        )
