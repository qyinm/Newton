from __future__ import annotations

import re
import shlex
import subprocess
from pathlib import Path
from typing import Callable, Sequence

from newton.plan_provenance import write_plan_provenance
from newton.scenario_loader import ScenarioLoadError, load_scenario

AgentRun = Callable[..., subprocess.CompletedProcess[str]]


class AgentPlanningError(RuntimeError):
    """Raised when an external planning agent cannot produce a valid scenario."""


def plan_scenario_with_agent(
    input_path: Path,
    *,
    agent: str,
    target: str,
    out_dir: Path,
    base_url: str = "http://127.0.0.1:8000",
    command: Sequence[str] | str | None = None,
    run: AgentRun = subprocess.run,
) -> Path:
    if not input_path.exists():
        raise AgentPlanningError(f"input markdown not found: {input_path}")

    agent = agent.lower().strip()
    if agent not in {"codex", "claude"}:
        raise AgentPlanningError(f"unsupported planning agent: {agent}")

    prompt = build_agent_prompt(
        input_path=input_path,
        markdown=input_path.read_text(),
        agent=agent,
        target=target,
        base_url=base_url,
    )
    argv, prompt_via_stdin = _agent_command(agent, prompt, command)

    out_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = out_dir / f"{input_path.stem}.{agent}.prompt.txt"
    raw_output_path = out_dir / f"{input_path.stem}.{agent}.raw.txt"
    prompt_path.write_text(prompt)

    try:
        completed = run(
            argv,
            input=prompt if prompt_via_stdin else None,
            text=True,
            capture_output=True,
            check=True,
        )
    except FileNotFoundError as exc:
        error = f"{agent} planner command not found: {argv[0]}. Install/authenticate it or use --agent template."
        write_plan_provenance(
            input_path=input_path,
            agent=agent,
            target=target,
            out_dir=out_dir,
            base_url=base_url,
            prompt_path=prompt_path,
            raw_output_path=None,
            accepted_scenario_path=None,
            validation_status="rejected",
            validation_error=error,
        )
        raise AgentPlanningError(error) from exc
    except subprocess.CalledProcessError as exc:
        raw = (exc.stdout or "") + (exc.stderr or "")
        raw_output_path.write_text(raw)
        error = f"{agent} planner command failed; raw output saved to {raw_output_path}"
        write_plan_provenance(
            input_path=input_path,
            agent=agent,
            target=target,
            out_dir=out_dir,
            base_url=base_url,
            prompt_path=prompt_path,
            raw_output_path=raw_output_path,
            accepted_scenario_path=None,
            validation_status="rejected",
            validation_error=error,
        )
        raise AgentPlanningError(error) from exc

    raw_output_path.write_text(completed.stdout)
    yaml_text = _extract_yaml(completed.stdout)
    candidate_path = out_dir / f"{input_path.stem}.{agent}.candidate.yaml"
    candidate_path.write_text(yaml_text)

    try:
        scenario = load_scenario(candidate_path)
    except ScenarioLoadError as exc:
        error = f"agent output did not validate; raw output saved to {raw_output_path}"
        write_plan_provenance(
            input_path=input_path,
            agent=agent,
            target=target,
            out_dir=out_dir,
            base_url=base_url,
            prompt_path=prompt_path,
            raw_output_path=raw_output_path,
            accepted_scenario_path=None,
            validation_status="rejected",
            validation_error=error,
        )
        raise AgentPlanningError(error) from exc

    output_path = out_dir / f"{scenario.meta.id}.generated.yaml"
    output_path.write_text(yaml_text)
    write_plan_provenance(
        input_path=input_path,
        agent=agent,
        target=target,
        out_dir=out_dir,
        base_url=base_url,
        prompt_path=prompt_path,
        raw_output_path=raw_output_path,
        accepted_scenario_path=output_path,
        validation_status="accepted",
        validation_error=None,
    )
    candidate_path.unlink(missing_ok=True)
    return output_path


def build_agent_prompt(*, input_path: Path, markdown: str, agent: str, target: str, base_url: str) -> str:
    return f"""You are generating a Newton QA scenario YAML.

Agent: {agent}
Input file: {input_path}
Target: {target}
Base URL: {base_url}

Output only valid Newton scenario YAML. Do not include explanations.

Required YAML shape:
scenario:
  id: <kebab-case-id>
  title: <human title>
  source_refs:
    - {input_path}
  risk_category: functional
  priority: P0
  environments:
    - local
targets:
  - id: web
    platform: web
    backend: playwright
    base_url: {base_url}
steps:
  - id: <step-id>
    action: <navigate|tap|input_text|assert_visible|assert_text|assert_url>
    target:
      web: {{...}}
evidence:
  screenshots: on_failure
  video: false
  logs: true
  traces: true

Rules:
- The YAML must validate with Newton's scenario schema.
- Generate one scenario only.
- Use target bindings for every non-navigation step.
- For web targets, use Playwright-friendly selectors such as url, text, test_id, role/name.
- Do not wrap the output unless your CLI requires fenced output; Newton will extract a yaml fence if present.

Markdown context:
---
{markdown}
---
"""


def _agent_command(agent: str, prompt: str, command: Sequence[str] | str | None) -> tuple[list[str], bool]:
    if command is not None:
        if isinstance(command, str):
            return shlex.split(command), True
        return list(command), True

    if agent == "codex":
        return ["codex", "exec", "-"], True
    if agent == "claude":
        return ["claude", "-p"], True
    raise AgentPlanningError(f"unsupported planning agent: {agent}")


def _extract_yaml(output: str) -> str:
    fenced = re.search(r"```(?:yaml|yml)?\s*(.*?)```", output, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip() + "\n"
    return output.strip() + "\n"
