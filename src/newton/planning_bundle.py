from __future__ import annotations

import json
import re
from pathlib import Path


class PlanningBundleError(ValueError):
    """Raised when markdown context cannot produce a planning bundle."""


def generate_planning_bundle(input_path: Path, out_dir: Path) -> Path:
    if not input_path.exists():
        raise PlanningBundleError(f"input markdown not found: {input_path}")

    markdown = input_path.read_text()
    title = _extract_title(markdown)
    plan_id = _slugify(title)
    summary = _extract_summary(markdown)
    checklist_items = _extract_acceptance_criteria(markdown) or [summary]

    bundle_dir = out_dir / plan_id
    bundle_dir.mkdir(parents=True, exist_ok=True)

    qa_scope_path = bundle_dir / "qa-scope.md"
    checklist_path = bundle_dir / "checklist.md"
    risk_map_path = bundle_dir / "risk-map.md"
    qa_estimate_path = bundle_dir / "qa-estimate.md"
    automation_candidates_path = bundle_dir / "automation-candidates.md"
    qa_run_tracker_path = bundle_dir / "qa-run-tracker.md"
    manifest_path = bundle_dir / "manifest.json"

    qa_scope_path.write_text(_render_scope(title, summary, input_path))
    checklist_path.write_text(_render_checklist(title, checklist_items))
    risk_map_path.write_text(_render_risk_map(title))
    qa_estimate_path.write_text(_render_estimate(title, checklist_items, input_path))
    automation_candidates_path.write_text(_render_automation_candidates(title, checklist_items))
    qa_run_tracker_path.write_text(_render_run_tracker(title, checklist_items))
    manifest_path.write_text(
        json.dumps(
            {
                "plan_id": plan_id,
                "input_path": str(input_path),
                "artifacts": {
                    "qa_scope": str(qa_scope_path),
                    "checklist": str(checklist_path),
                    "risk_map": str(risk_map_path),
                    "qa_estimate": str(qa_estimate_path),
                    "automation_candidates": str(automation_candidates_path),
                    "qa_run_tracker": str(qa_run_tracker_path),
                },
            },
            indent=2,
        )
        + "\n"
    )
    return bundle_dir


def _extract_title(markdown: str) -> str:
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            title = stripped.lstrip("#").strip()
            if title:
                return title
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:80]
    raise PlanningBundleError("input markdown is empty")


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "qa-plan"


def _extract_summary(markdown: str) -> str:
    for line in markdown.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("-"):
            continue
        if stripped.lower().rstrip(":") == "acceptance criteria":
            continue
        return stripped
    return "Review the provided markdown context and verify the intended user outcome."


def _extract_acceptance_criteria(markdown: str) -> list[str]:
    items: list[str] = []
    in_acceptance_criteria = False
    for line in markdown.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.lower().rstrip(":") == "acceptance criteria":
            in_acceptance_criteria = True
            continue
        if in_acceptance_criteria and stripped.startswith("#"):
            break
        if in_acceptance_criteria and stripped.startswith("-"):
            item = stripped.lstrip("-").strip()
            if item:
                items.append(item)
    return items


def _render_scope(title: str, summary: str, input_path: Path) -> str:
    return f"""# QA Scope: {title}

## Source

- `{input_path}`

## Goal

{summary}

## In Scope

- Validate the primary user flow described in the source context.
- Cover the listed acceptance criteria as manual checklist items.

## Out of Scope

- Cross-browser matrix expansion.
- Performance, security, and accessibility deep dives unless explicitly listed in the source context.
"""


def _render_checklist(title: str, items: list[str]) -> str:
    checklist = "\n".join(f"- [ ] {item}" for item in items)
    return f"""# QA Checklist: {title}

{checklist}
"""


def _render_risk_map(title: str) -> str:
    return f"""# Risk Map: {title}

| Area | Priority | Rationale |
| --- | --- | --- |
| functional | P0 | {title} flow blocks core user access |
"""


def _render_estimate(title: str, checklist_items: list[str], input_path: Path) -> str:
    return f"""# QA Estimate: {title}

## Summary

Estimated QA effort: S

## Basis

- Checklist items: {len(checklist_items)}
- Risk level: P0 functional
- Source input: `{input_path}`

## Suggested Manual QA Time

- Happy path smoke: 15 min
- Negative/error cases: 15 min
- Evidence/report review: 10 min

## Assumptions

- Local or staging environment is available.
- No cross-platform mobile validation included.
"""


def _render_automation_candidates(title: str, checklist_items: list[str]) -> str:
    recommended = checklist_items[0]
    manual_items = checklist_items[1:]
    manual_section = "\n".join(
        f"- {item}\n  - Source: checklist item {index}\n  - Reason: keep manual until the flow and copy are stable."
        for index, item in enumerate(manual_items, start=2)
    )
    if not manual_section:
        manual_section = "- No additional checklist items."

    return f"""# Automation Candidates: {title}

## Recommended

- {recommended}
  - Source: checklist item 1
  - Suggested automation: web scenario smoke test
  - Priority: P0
  - Reason: stable happy path with clear pass/fail signal.

## Manual For Now

{manual_section}
"""


def _render_run_tracker(title: str, checklist_items: list[str]) -> str:
    checklist_status = "\n".join(
        f"- [ ] {item}\n  - env: dev\n  - status: not run\n  - notes:" for item in checklist_items
    )
    return f"""# QA Run Tracker: {title}

## Environment Status

- dev: not run
- stg: not run
- prod: not run

## Checklist Status

{checklist_status}
"""
