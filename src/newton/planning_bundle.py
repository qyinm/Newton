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
    manifest_path = bundle_dir / "manifest.json"

    qa_scope_path.write_text(_render_scope(title, summary, input_path))
    checklist_path.write_text(_render_checklist(title, checklist_items))
    risk_map_path.write_text(_render_risk_map(title))
    manifest_path.write_text(
        json.dumps(
            {
                "plan_id": plan_id,
                "input_path": str(input_path),
                "artifacts": {
                    "qa_scope": str(qa_scope_path),
                    "checklist": str(checklist_path),
                    "risk_map": str(risk_map_path),
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
