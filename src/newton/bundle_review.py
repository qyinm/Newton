from __future__ import annotations

import json
import re
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from newton.planning_bundle_validation import PlanningBundleValidationError, validate_planning_bundle

AgentRun = Callable[..., subprocess.CompletedProcess[str]]


class BundleReviewError(RuntimeError):
    """Raised when a QA bundle advisory review cannot be produced."""


@dataclass(frozen=True)
class BundleReviewResult:
    agent: str
    score: int
    verdict: str
    review_json_path: Path
    review_markdown_path: Path
    prompt_path: Path | None = None
    raw_output_path: Path | None = None


def review_planning_bundle(
    bundle_dir: Path,
    *,
    agent: str = "template",
    command: Sequence[str] | str | None = None,
    run: AgentRun = subprocess.run,
) -> BundleReviewResult:
    normalized_agent = agent.strip().lower()
    if normalized_agent not in {"template", "codex", "claude"}:
        raise BundleReviewError(f"unsupported bundle review agent: {agent}")

    try:
        validation = validate_planning_bundle(bundle_dir)
    except PlanningBundleValidationError as exc:
        raise BundleReviewError(f"bundle validation failed: {exc}") from exc

    if normalized_agent == "template":
        payload = _template_review_payload(bundle_dir)
        return _write_review_artifacts(
            bundle_dir,
            agent=normalized_agent,
            plan_id=validation.plan_id,
            payload=payload,
        )

    prompt = build_bundle_review_prompt(bundle_dir)
    prompt_path = bundle_dir / f"bundle-review.{normalized_agent}.prompt.txt"
    raw_output_path = bundle_dir / f"bundle-review.{normalized_agent}.raw.txt"
    prompt_path.write_text(prompt)
    argv, prompt_via_stdin = _agent_command(normalized_agent, command)

    try:
        completed = run(
            argv,
            input=prompt if prompt_via_stdin else None,
            text=True,
            capture_output=True,
            check=True,
        )
    except FileNotFoundError as exc:
        raise BundleReviewError(
            f"{normalized_agent} review command not found: {argv[0]}. Install/authenticate it or use --agent template."
        ) from exc
    except subprocess.CalledProcessError as exc:
        raw = (exc.stdout or "") + (exc.stderr or "")
        raw_output_path.write_text(raw)
        raise BundleReviewError(f"{normalized_agent} review command failed; raw output saved to {raw_output_path}") from exc

    raw_output_path.write_text(completed.stdout)
    try:
        payload = _validate_agent_review_payload(_extract_json(completed.stdout), agent=normalized_agent, bundle_dir=bundle_dir)
    except BundleReviewError as exc:
        raise BundleReviewError(f"agent review output did not validate; raw output saved to {raw_output_path}") from exc

    return _write_review_artifacts(
        bundle_dir,
        agent=normalized_agent,
        plan_id=validation.plan_id,
        payload=payload,
        prompt_path=prompt_path,
        raw_output_path=raw_output_path,
    )


def build_bundle_review_prompt(bundle_dir: Path) -> str:
    artifact_sections = []
    for filename in [
        "qa-scope.md",
        "checklist.md",
        "test-cases.csv",
        "risk-map.md",
        "qa-estimate.md",
        "automation-candidates.md",
        "qa-run-tracker.md",
        "manifest.json",
    ]:
        path = bundle_dir / filename
        artifact_sections.append(f"## {filename}\n\n```\n{path.read_text()}\n```")

    artifacts = "\n\n".join(artifact_sections)
    return f"""Review this Newton QA planning bundle as a senior QA reviewer.

Bundle path: {bundle_dir}

This is advisory only. Do not rewrite artifacts. Identify coverage, risk, test-case, and tracker quality gaps.

Output only JSON with this exact shape:
{{
  "score": <integer 0-100>,
  "verdict": "advisory_pass" | "needs_improvement",
  "findings": [
    {{
      "severity": "low" | "medium" | "high",
      "artifact": "<artifact filename>",
      "finding": "<concise issue>",
      "suggestion": "<actionable suggestion>"
    }}
  ]
}}

Artifacts:

{artifacts}
"""


def _template_review_payload(bundle_dir: Path) -> dict[str, object]:
    return {
        "agent": "template",
        "bundle_path": str(bundle_dir),
        "score": 80,
        "verdict": "advisory_pass",
        "findings": [
            {
                "severity": "low",
                "artifact": "checklist.md",
                "finding": "Deterministic review only checks that baseline planning artifacts are present and internally consistent.",
                "suggestion": "Use --agent codex or --agent claude for semantic QA coverage feedback.",
            }
        ],
    }


def _write_review_artifacts(
    bundle_dir: Path,
    *,
    agent: str,
    plan_id: str,
    payload: dict[str, object],
    prompt_path: Path | None = None,
    raw_output_path: Path | None = None,
) -> BundleReviewResult:
    normalized_payload = _validate_agent_review_payload(payload, agent=agent, bundle_dir=bundle_dir)
    json_path = bundle_dir / f"bundle-review.{agent}.json"
    markdown_path = bundle_dir / f"bundle-review.{agent}.md"
    json_path.write_text(json.dumps(normalized_payload, indent=2) + "\n")
    markdown_path.write_text(_render_review_markdown(plan_id, normalized_payload))
    return BundleReviewResult(
        agent=agent,
        score=int(normalized_payload["score"]),
        verdict=str(normalized_payload["verdict"]),
        review_json_path=json_path,
        review_markdown_path=markdown_path,
        prompt_path=prompt_path,
        raw_output_path=raw_output_path,
    )


def _validate_agent_review_payload(payload: object, *, agent: str, bundle_dir: Path) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise BundleReviewError("review output must be a JSON object")
    score = payload.get("score")
    verdict = payload.get("verdict")
    findings = payload.get("findings")
    if not isinstance(score, int) or score < 0 or score > 100:
        raise BundleReviewError("review score must be an integer from 0 to 100")
    if verdict not in {"advisory_pass", "needs_improvement"}:
        raise BundleReviewError("review verdict must be advisory_pass or needs_improvement")
    if not isinstance(findings, list):
        raise BundleReviewError("review findings must be a list")

    normalized_findings: list[dict[str, str]] = []
    for finding in findings:
        if not isinstance(finding, dict):
            raise BundleReviewError("review finding must be an object")
        severity = finding.get("severity")
        artifact = finding.get("artifact")
        finding_text = finding.get("finding")
        suggestion = finding.get("suggestion")
        if severity not in {"low", "medium", "high"}:
            raise BundleReviewError("review finding severity must be low, medium, or high")
        if not all(isinstance(value, str) and value for value in [artifact, finding_text, suggestion]):
            raise BundleReviewError("review finding fields must be non-empty strings")
        normalized_findings.append(
            {
                "severity": severity,
                "artifact": artifact,
                "finding": finding_text,
                "suggestion": suggestion,
            }
        )

    return {
        "agent": agent,
        "bundle_path": str(bundle_dir),
        "score": score,
        "verdict": verdict,
        "findings": normalized_findings,
    }


def _render_review_markdown(plan_id: str, payload: dict[str, object]) -> str:
    findings = payload["findings"]
    finding_lines = []
    for index, finding in enumerate(findings, start=1):
        assert isinstance(finding, dict)
        finding_lines.append(
            f"{index}. **{finding['severity']}** — `{finding['artifact']}`\n"
            f"   - Finding: {finding['finding']}\n"
            f"   - Suggestion: {finding['suggestion']}"
        )
    rendered_findings = "\n".join(finding_lines) if finding_lines else "No findings."
    return f"""# QA Bundle Review: {plan_id}

This is an advisory review. Deterministic `bundle-validate` remains the required structural gate.

- Agent: {payload['agent']}
- Bundle: `{payload['bundle_path']}`
- Score: {payload['score']}
- Verdict: {payload['verdict']}

## Findings

{rendered_findings}
"""


def _agent_command(agent: str, command: Sequence[str] | str | None) -> tuple[list[str], bool]:
    if command is not None:
        if isinstance(command, str):
            return shlex.split(command), True
        return list(command), True
    if agent == "codex":
        return ["codex", "exec", "--sandbox", "read-only", "-"], True
    if agent == "claude":
        return ["claude", "-p", "--tools", ""], True
    raise BundleReviewError(f"unsupported bundle review agent: {agent}")


def _extract_json(output: str) -> object:
    fenced = re.search(r"```(?:json)?\s*(.*?)```", output, flags=re.DOTALL | re.IGNORECASE)
    raw_json = fenced.group(1).strip() if fenced else output.strip()
    try:
        return json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise BundleReviewError(f"invalid review JSON: {exc.msg}") from exc
