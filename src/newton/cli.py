from __future__ import annotations

from pathlib import Path

import typer

from newton import __version__
from newton.agent_planner import AgentPlanningError, plan_scenario_with_agent
from newton.plan_provenance import PlanProvenanceError, write_plan_provenance
from newton.planner import PlanningError, plan_scenario_from_markdown
from newton.runner import run_scenario
from newton.scenario_loader import ScenarioLoadError, load_scenario

app = typer.Typer(help="Newton QA harness")
qa_app = typer.Typer(help="QA scenario commands")
app.add_typer(qa_app, name="qa")


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


@qa_app.command("report")
def qa_report(run_path: Path) -> None:
    """Print the path to an existing QA report."""
    report_path = run_path / "qa-report.md"
    if not report_path.exists():
        raise typer.BadParameter(f"qa report not found: {report_path}")
    typer.echo(str(report_path))
