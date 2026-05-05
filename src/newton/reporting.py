from __future__ import annotations

from newton.models import EvidenceArtifact, RunResult


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
        lines.append(f"| {step.id} | {step.action} | {step.status} | {step.error or '-'} |")

    evidence_lines = _render_evidence_sections(result)
    if evidence_lines:
        lines.extend(["", *evidence_lines])

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


def _render_evidence_sections(result: RunResult) -> list[str]:
    lines: list[str] = []
    if result.evidence:
        lines.extend(["## Evidence", ""])
        lines.extend(_render_evidence_list(result.evidence))

    step_lines: list[str] = []
    for step in result.steps:
        if step.evidence:
            if not step_lines:
                step_lines.extend(["## Step Evidence", ""])
            step_lines.append(f"### {step.id}")
            step_lines.extend(_render_evidence_list(step.evidence))
            step_lines.append("")

    if step_lines:
        if step_lines[-1] == "":
            step_lines.pop()
        if lines:
            lines.append("")
        lines.extend(step_lines)

    return lines


def _render_evidence_list(evidence: list[EvidenceArtifact]) -> list[str]:
    rendered: list[str] = []
    for artifact in evidence:
        detail = f" — {artifact.description}" if artifact.description else ""
        rendered.append(f"- `{artifact.kind}`: `{artifact.path}`{detail}")
    return rendered
