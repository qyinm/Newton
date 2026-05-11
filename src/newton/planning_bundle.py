from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass
from pathlib import Path

from newton.models import ARTIFACT_CONTRACT_VERSION


class PlanningBundleError(ValueError):
    """Raised when markdown context cannot produce a planning bundle."""


@dataclass(frozen=True)
class SourceReference:
    path: Path
    section: str

    def display(self) -> str:
        if self.section:
            return f"{self.path.name}#{self.section}"
        return self.path.name


@dataclass(frozen=True)
class SourceFact:
    kind: str
    text: str
    source_reference: SourceReference


@dataclass(frozen=True)
class SourceFacts:
    feature_goal: list[SourceFact]
    screens: list[SourceFact]
    user_roles: list[SourceFact]
    states: list[SourceFact]
    policies: list[SourceFact]
    environments: list[SourceFact]
    dependencies: list[SourceFact]
    regression_areas: list[SourceFact]
    unknowns: list[SourceFact]
    out_of_scope: list[SourceFact]


@dataclass(frozen=True)
class MarkdownItem:
    text: str
    source_reference: SourceReference


@dataclass(frozen=True)
class RiskEvidence:
    text: str
    source_reference: SourceReference


@dataclass(frozen=True)
class RiskMapRow:
    area: str
    priority: str
    rationale: str
    source: str


@dataclass(frozen=True)
class EstimateFactor:
    factor: str
    value: str
    evidence: str
    source: str
    score: int
    rule: str


@dataclass(frozen=True)
class EstimateBand:
    size: str
    time_range: str
    score_band: str
    manual_qa_time: list[str]


REQUIRED_ESTIMATE_FACTORS = (
    "screens",
    "roles",
    "states",
    "policy_rules",
    "integrations",
    "environments",
    "regression",
    "data_setup",
    "retest_count",
)

ESTIMATE_FACTOR_ALIASES = {
    "screens": {"screens", "screen"},
    "roles": {"roles", "role", "user_roles", "user_role", "personas", "persona"},
    "states": {"states", "state"},
    "policy_rules": {"policy_rules", "policy_rule", "policies", "policy"},
    "integrations": {
        "integrations",
        "integration",
        "dependencies",
        "dependency",
        "integrations_dependencies",
        "dependencies_integrations",
    },
    "environments": {"environments", "environment", "test_environments", "test_environment"},
    "regression": {"regression", "regressions", "regression_risk", "regression_areas", "regression_area"},
    "data_setup": {"data_setup", "data", "test_data", "fixtures", "fixture"},
    "retest_count": {"retest_count", "retest", "retests", "re_test_count"},
}

_COUNT_SCORE_RULES = {
    "screens": [
        (1, 0, "0-1 screens => +0"),
        (3, 1, "2-3 screens => +1"),
        (6, 2, "4-6 screens => +2"),
        (None, 3, "7+ screens => +3"),
    ],
    "roles": [
        (1, 0, "0-1 roles => +0"),
        (3, 1, "2-3 roles => +1"),
        (None, 2, "4+ roles => +2"),
    ],
    "states": [
        (5, 0, "0-5 states => +0"),
        (8, 1, "6-8 states => +1"),
        (None, 2, "9+ states => +2"),
    ],
    "policy_rules": [
        (0, 0, "0 policy rules => +0"),
        (2, 1, "1-2 policy rules => +1"),
        (None, 2, "3+ policy rules => +2"),
    ],
    "integrations": [
        (0, 0, "0 integrations/dependencies => +0"),
        (1, 1, "1 integration/dependency => +1"),
        (3, 2, "2-3 integrations/dependencies => +2"),
        (None, 3, "4+ integrations/dependencies => +3"),
    ],
    "environments": [
        (1, 0, "0-1 environments => +0"),
        (2, 1, "2 environments => +1"),
        (None, 2, "3+ environments => +2"),
    ],
    "regression": [
        (0, 0, "0 regression risks => +0"),
        (2, 1, "1-2 regression risks => +1"),
        (None, 2, "3+ regression risks => +2"),
    ],
    "data_setup": [
        (0, 0, "0 data setup signals => +0"),
        (2, 1, "1-2 data setup signals => +1"),
        (None, 2, "3+ data setup signals => +2"),
    ],
    "retest_count": [
        (1, 0, "1 retest pass => +0"),
        (3, 1, "2-3 retest passes => +1"),
        (5, 2, "4-5 retest passes => +2"),
        (None, 3, "6+ retest passes => +3"),
    ],
}

_DATA_SETUP_PATTERN = re.compile(
    r"\b(seed|fixture|test account|test user|sample data|test data|migration|backfill|import|export|paid invoice)\b",
    re.IGNORECASE,
)
_DATA_STATE_RISK_PATTERN = re.compile(
    r"\b(state|status|record|records|locked|expired|missing|declined|suspended|active|inactive|valid|invalid|"
    r"seed|fixture|test account|test user|sample data|test data|migration|backfill|import|export|paid invoice)\b",
    re.IGNORECASE,
)
_ANALYTICS_LOGGING_RISK_PATTERN = re.compile(
    r"\b(analytics?|events?|metrics?|logs|logging|telemetry|audit trail|tracking|instrumentation|"
    r"log entry|log line|log file)\b",
    re.IGNORECASE,
)
_LOCALIZATION_COPY_RISK_PATTERN = re.compile(
    r"\b(copy|message|text|label|wording|locale|locales|localized|localization|translation|language|guidance)\b",
    re.IGNORECASE,
)
_ACCESSIBILITY_RISK_PATTERN = re.compile(
    r"\b(accessibility|a11y|screen reader|keyboard|aria|focus|contrast|alt text|tab order|voiceover)\b",
    re.IGNORECASE,
)
_ENVIRONMENT_CONFIG_RISK_PATTERN = re.compile(
    r"\b(config|configuration|feature flag|flag|secret|env var|environment variable|region)\b",
    re.IGNORECASE,
)


def generate_planning_bundle(
    input_path: Path,
    out_dir: Path,
    source_paths: list[Path] | None = None,
    bundle_dir_name: str | None = None,
) -> Path:
    all_source_paths = [input_path, *(source_paths or [])]
    markdown_by_path = _read_markdown_sources(all_source_paths)

    markdown = markdown_by_path[0]
    title = _extract_title(markdown)
    plan_id = _slugify(title)
    markdown_sources = list(zip(all_source_paths, markdown_by_path, strict=True))
    source_facts = _extract_source_facts(markdown_sources)
    summary = source_facts.feature_goal[0].text if source_facts.feature_goal else _extract_summary(markdown)
    checklist_items = _extract_all_acceptance_criteria(markdown_by_path) or _facts_to_checklist(source_facts) or [summary]

    bundle_dir = out_dir / (bundle_dir_name or plan_id)
    bundle_dir.mkdir(parents=True, exist_ok=True)

    qa_scope_path = bundle_dir / "qa-scope.md"
    checklist_path = bundle_dir / "checklist.md"
    test_cases_path = bundle_dir / "test-cases.csv"
    risk_map_path = bundle_dir / "risk-map.md"
    qa_estimate_path = bundle_dir / "qa-estimate.md"
    automation_candidates_path = bundle_dir / "automation-candidates.md"
    qa_run_tracker_path = bundle_dir / "qa-run-tracker.md"
    manifest_path = bundle_dir / "manifest.json"

    qa_scope_path.write_text(_render_scope(title, summary, all_source_paths, source_facts))
    checklist_path.write_text(_render_checklist(title, checklist_items))
    test_cases_path.write_text(_render_test_cases_csv(checklist_items))
    risk_map_path.write_text(_render_risk_map(title, source_facts, markdown_sources))
    qa_estimate_path.write_text(
        _render_estimate(title, checklist_items, all_source_paths, source_facts, markdown_sources)
    )
    automation_candidates_path.write_text(_render_automation_candidates(title, checklist_items))
    qa_run_tracker_path.write_text(_render_run_tracker(title, checklist_items))
    manifest: dict[str, object] = {
        "contract_version": ARTIFACT_CONTRACT_VERSION,
        "plan_id": plan_id,
        "input_path": str(input_path),
        "source_paths": [str(source_path) for source_path in all_source_paths],
        "artifacts": {
            "qa_scope": str(qa_scope_path),
            "checklist": str(checklist_path),
            "test_cases": str(test_cases_path),
            "risk_map": str(risk_map_path),
            "qa_estimate": str(qa_estimate_path),
            "automation_candidates": str(automation_candidates_path),
            "qa_run_tracker": str(qa_run_tracker_path),
        },
    }
    if bundle_dir_name is not None:
        manifest["bundle_dir_name"] = bundle_dir.name

    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return bundle_dir


def _read_markdown_sources(paths: list[Path]) -> list[str]:
    markdown_sources: list[str] = []
    for path in paths:
        if not path.exists():
            raise PlanningBundleError(f"input markdown not found: {path}")
        markdown_sources.append(path.read_text())
    return markdown_sources


def _extract_source_facts(markdown_sources: list[tuple[Path, str]]) -> SourceFacts:
    facts: dict[str, list[SourceFact]] = {
        "feature_goal": [],
        "screens": [],
        "user_roles": [],
        "states": [],
        "policies": [],
        "environments": [],
        "dependencies": [],
        "regression_areas": [],
        "unknowns": [],
        "out_of_scope": [],
    }
    seen: set[tuple[str, str, str]] = set()
    for path, markdown in markdown_sources:
        for item in _iter_markdown_items(path, markdown):
            for fact in _facts_from_markdown_item(item):
                dedupe_key = (fact.kind, fact.text.casefold(), fact.source_reference.display())
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)
                facts[fact.kind].append(fact)
    return SourceFacts(**facts)


def _iter_markdown_items(path: Path, markdown: str) -> list[MarkdownItem]:
    items: list[MarkdownItem] = []
    section = "Summary"
    saw_document_title = False
    for line in markdown.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        heading = re.match(r"^(#{1,6})\s+(.+?)\s*$", stripped)
        if heading:
            level = len(heading.group(1))
            heading_title = heading.group(2).strip()
            if level == 1 and not saw_document_title:
                saw_document_title = True
                section = "Summary"
                continue
            section = heading_title
            continue

        if _is_plain_section_label(stripped):
            section = stripped.rstrip(":").strip()
            continue

        text = _strip_markdown_list_marker(stripped)
        if text:
            items.append(MarkdownItem(text=text, source_reference=SourceReference(path=path, section=section)))
    return items


def _is_plain_section_label(value: str) -> bool:
    return bool(re.match(r"^[A-Za-z][A-Za-z0-9 /&()_-]{1,80}:$", value))


def _strip_markdown_list_marker(value: str) -> str:
    stripped = re.sub(r"^[-*+]\s+", "", value)
    stripped = re.sub(r"^\d+[.)]\s+", "", stripped)
    return stripped.strip()


def _facts_from_markdown_item(item: MarkdownItem) -> list[SourceFact]:
    section_key = _section_key(item.source_reference.section)
    text = _clean_fact_text(item.text)
    if not text:
        return []

    screen_text = _inline_label_value(text, ["screens", "screen"])
    if screen_text:
        return [_source_fact("screens", screen_text, item.source_reference)]

    if section_key in {"scope", "goal", "objective", "summary", "overview"}:
        return [_source_fact("feature_goal", text, item.source_reference)]
    if section_key in {"user_stories", "user_story", "roles", "user_roles", "personas"}:
        role = _extract_user_role(text)
        return [_source_fact("user_roles", role or text, item.source_reference)]
    if section_key in {"requirements", "requirement", "acceptance_criteria", "acceptance", "states", "state"}:
        return [_source_fact("states", text, item.source_reference)]
    if section_key in {"policy", "policies", "policy_references", "policy_notes"}:
        return [_source_fact("policies", text, item.source_reference)]
    if section_key in {"environments", "environment", "test_environments", "test_matrix"}:
        return [_source_fact("environments", text, item.source_reference)]
    if section_key in {"dependencies", "dependency", "integrations", "integration"}:
        return [_source_fact("dependencies", text, item.source_reference)]
    if section_key in {"risks", "risk", "regression", "regressions", "regression_notes", "regression_areas"}:
        return [_source_fact("regression_areas", text, item.source_reference)]
    if section_key in {"unknowns", "unknown", "open_questions", "questions", "todos", "todo"}:
        return [_source_fact("unknowns", text, item.source_reference)]
    if section_key in {"out_of_scope", "out_of_scopes", "non_goals", "non_goal"}:
        return [_source_fact("out_of_scope", text, item.source_reference)]
    if section_key in {"design_notes", "design_note", "design_references", "design"}:
        return _facts_from_design_note(text, item.source_reference)

    if "?" in text or re.search(r"\b(tbd|unknown|confirm|not confirmed)\b", text, re.IGNORECASE):
        return [_source_fact("unknowns", text, item.source_reference)]
    return []


def _facts_from_design_note(text: str, source_reference: SourceReference) -> list[SourceFact]:
    lowered = text.lower()
    if "state" in lowered or re.search(r"\b(success|failure|error|locked|expired|timeout)\b", lowered):
        return [_source_fact("states", text, source_reference)]
    if re.search(r"\b(screen|page|route)\b", lowered):
        return [_source_fact("screens", text, source_reference)]
    if re.search(r"\b(api|service|depends|dependency|requires|required)\b", lowered):
        return [_source_fact("dependencies", text, source_reference)]
    return []


def _source_fact(kind: str, text: str, source_reference: SourceReference) -> SourceFact:
    return SourceFact(kind=kind, text=_clean_fact_text(text), source_reference=source_reference)


def _clean_fact_text(text: str) -> str:
    return text.strip().rstrip(";")


def _inline_label_value(text: str, labels: list[str]) -> str | None:
    for label in labels:
        match = re.match(rf"^{re.escape(label)}\s*:\s*(.+)$", text, re.IGNORECASE)
        if match:
            return _clean_fact_text(match.group(1))
    return None


def _extract_user_role(text: str) -> str | None:
    match = re.match(r"as an?\s+([^,]+),", text, re.IGNORECASE)
    if not match:
        return None
    return match.group(1).strip()


def _section_key(section: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", section.casefold()).strip("_")


def normalize_estimate_factor_name(factor: str) -> str | None:
    normalized = _section_key(factor)
    for canonical, aliases in ESTIMATE_FACTOR_ALIASES.items():
        if normalized == canonical or normalized in aliases:
            return canonical
    return None


def _facts_to_checklist(facts: SourceFacts) -> list[str]:
    checklist_facts = [
        *facts.states,
        *facts.policies,
        *facts.screens,
        *facts.dependencies,
        *facts.regression_areas,
        *facts.unknowns,
    ]
    return [fact.text for fact in checklist_facts]


def _extract_all_acceptance_criteria(markdown_sources: list[str]) -> list[str]:
    items: list[str] = []
    for markdown in markdown_sources:
        items.extend(_extract_acceptance_criteria(markdown))
    return items


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


def _render_scope(title: str, summary: str, source_paths: list[Path], source_facts: SourceFacts) -> str:
    sources = "\n".join(f"- `{source_path}`" for source_path in source_paths)
    fact_table = _render_source_fact_table(source_facts)
    out_of_scope = _render_out_of_scope(source_facts)
    return f"""# QA Scope: {title}

## Sources

{sources}

## Goal

{summary}

## Extracted Source Facts

{fact_table}

## In Scope

- Validate the primary user flow described in the source context.
- Cover the listed acceptance criteria as manual checklist items.

## Out of Scope

{out_of_scope}
"""


def _render_source_fact_table(source_facts: SourceFacts) -> str:
    rows: list[str] = []
    for label, facts in _source_fact_groups(source_facts):
        for fact in facts:
            rows.append(
                "| "
                f"{label} | "
                f"{_markdown_table_cell(fact.text)} | "
                f"`{_markdown_table_cell(fact.source_reference.display())}` |"
            )
    if not rows:
        return "No structured source facts were extracted."
    return "\n".join(["| Fact Type | Fact | Source |", "| --- | --- | --- |", *rows])


def _render_out_of_scope(source_facts: SourceFacts) -> str:
    if not source_facts.out_of_scope:
        return "\n".join(
            [
                "- Cross-browser matrix expansion.",
                "- Performance, security, and accessibility deep dives unless explicitly listed in the source context.",
            ]
        )
    return "\n".join(
        f"- {fact.text}\n  - Source: `{fact.source_reference.display()}`" for fact in source_facts.out_of_scope
    )


def _source_fact_groups(source_facts: SourceFacts) -> list[tuple[str, list[SourceFact]]]:
    return [
        ("Feature Goal", source_facts.feature_goal),
        ("Screens", source_facts.screens),
        ("User Roles", source_facts.user_roles),
        ("States", source_facts.states),
        ("Policies", source_facts.policies),
        ("Environments", source_facts.environments),
        ("Dependencies", source_facts.dependencies),
        ("Regression Areas", source_facts.regression_areas),
        ("Unknowns", source_facts.unknowns),
        ("Out Of Scope", source_facts.out_of_scope),
    ]


def _render_checklist(title: str, items: list[str]) -> str:
    checklist = "\n".join(f"- [ ] {item}" for item in items)
    return f"""# QA Checklist: {title}

{checklist}
"""


def _render_test_cases_csv(items: list[str]) -> str:
    output = io.StringIO()
    fieldnames = [
        "ID",
        "title",
        "priority",
        "precondition",
        "steps",
        "expected_result",
        "environment",
        "risk_category",
        "source_reference",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for index, item in enumerate(items, start=1):
        writer.writerow(
            {
                "ID": f"TC-{index:03d}",
                "title": item,
                "priority": "P0" if index == 1 else "P1",
                "precondition": "Feature context is available and the target environment is reachable.",
                "steps": f"Execute checklist item {index}: {item}",
                "expected_result": item,
                "environment": "dev/stg/prod",
                "risk_category": "functional",
                "source_reference": f"Acceptance criteria item {index}",
            }
        )
    return output.getvalue()


def _render_risk_map(
    title: str,
    source_facts: SourceFacts,
    markdown_sources: list[tuple[Path, str]],
) -> str:
    rows = [*_baseline_risk_rows(title), *_optional_risk_rows(source_facts, markdown_sources)]
    rendered_rows = "\n".join(_render_risk_map_row(row) for row in rows)
    return f"""# Risk Map: {title}

| Area | Priority | Rationale | Source |
| --- | --- | --- | --- |
{rendered_rows}

Source: generated PRD baseline risks
"""


def _baseline_risk_rows(title: str) -> list[RiskMapRow]:
    baseline_source = "generated PRD baseline risks"
    return [
        RiskMapRow("functional", "P0", f"{title} flow blocks core user access", baseline_source),
        RiskMapRow(
            "edge case",
            "P1",
            "Boundary, empty, duplicate, and invalid inputs can break the flow outside the happy path",
            baseline_source,
        ),
        RiskMapRow(
            "network failure",
            "P1",
            "Slow, offline, timeout, and retry states can hide incomplete error handling",
            baseline_source,
        ),
        RiskMapRow(
            "permission/role",
            "P1",
            "Role or session differences can expose unauthorized access or blocked valid users",
            baseline_source,
        ),
        RiskMapRow(
            "policy conflict",
            "P1",
            "Source policy or copy requirements may conflict with visible product behavior",
            baseline_source,
        ),
        RiskMapRow(
            "regression",
            "P1",
            "Existing login and navigation paths can regress when this feature changes",
            baseline_source,
        ),
    ]


def _optional_risk_rows(
    source_facts: SourceFacts,
    markdown_sources: list[tuple[Path, str]],
) -> list[RiskMapRow]:
    data_setup_items = [
        RiskEvidence(item.text, item.source_reference)
        for item in _extract_data_setup_items(markdown_sources)
    ]
    source_evidence = _dedupe_risk_evidence(
        [
            *_source_facts_to_risk_evidence(source_facts),
            *_markdown_sources_to_risk_evidence(markdown_sources),
        ]
    )
    optional_risks: list[tuple[str, str, list[RiskEvidence]]] = [
        (
            "data state",
            "Data setup and state-specific records require coverage",
            [
                *data_setup_items,
                *_matching_risk_evidence(
                    source_evidence,
                    _DATA_STATE_RISK_PATTERN,
                    section_keys={"data", "data_setup", "test_data", "fixtures"},
                ),
            ],
        ),
        (
            "analytics/logging",
            "Instrumentation or logs can silently break",
            _matching_risk_evidence(
                source_evidence,
                _ANALYTICS_LOGGING_RISK_PATTERN,
                section_keys={"analytics", "logging", "logs", "observability", "telemetry"},
            ),
        ),
        (
            "localization/copy",
            "Visible copy or localization rules can drift from source expectations",
            _matching_risk_evidence(
                source_evidence,
                _LOCALIZATION_COPY_RISK_PATTERN,
                section_keys={"copy", "localization", "locale", "locales", "translations"},
            ),
        ),
        (
            "accessibility",
            "Accessibility behavior needs explicit manual coverage",
            _matching_risk_evidence(
                source_evidence,
                _ACCESSIBILITY_RISK_PATTERN,
                section_keys={"accessibility", "a11y"},
            ),
        ),
        (
            "environment config",
            "Environment-specific configuration can diverge",
            [
                *[
                    RiskEvidence(fact.text, fact.source_reference)
                    for fact in source_facts.environments
                ],
                *_matching_risk_evidence(
                    source_evidence,
                    _ENVIRONMENT_CONFIG_RISK_PATTERN,
                    section_keys={
                        "environment",
                        "environments",
                        "environment_config",
                        "test_environments",
                        "test_matrix",
                    },
                ),
            ],
        ),
    ]

    rows: list[RiskMapRow] = []
    for area, rationale_prefix, evidence_items in optional_risks:
        evidence_items = _dedupe_risk_evidence(evidence_items)
        if not evidence_items:
            continue
        evidence_text = _join_risk_evidence_texts(evidence_items)
        rows.append(
            RiskMapRow(
                area=area,
                priority="P1",
                rationale=f"{rationale_prefix}: {evidence_text}",
                source=_join_risk_evidence_sources(evidence_items),
            )
        )
    return rows


def _source_facts_to_risk_evidence(source_facts: SourceFacts) -> list[RiskEvidence]:
    evidence: list[RiskEvidence] = []
    for _, facts in _source_fact_groups(source_facts):
        evidence.extend(RiskEvidence(fact.text, fact.source_reference) for fact in facts)
    return evidence


def _markdown_sources_to_risk_evidence(markdown_sources: list[tuple[Path, str]]) -> list[RiskEvidence]:
    evidence: list[RiskEvidence] = []
    for path, markdown in markdown_sources:
        evidence.extend(
            RiskEvidence(item.text, item.source_reference)
            for item in _iter_markdown_items(path, markdown)
        )
    return evidence


def _matching_risk_evidence(
    evidence_items: list[RiskEvidence],
    text_pattern: re.Pattern[str],
    *,
    section_keys: set[str],
) -> list[RiskEvidence]:
    return [
        evidence
        for evidence in evidence_items
        if text_pattern.search(evidence.text)
        or _section_key(evidence.source_reference.section) in section_keys
    ]


def _dedupe_risk_evidence(evidence_items: list[RiskEvidence]) -> list[RiskEvidence]:
    deduped: list[RiskEvidence] = []
    seen: set[tuple[str, str]] = set()
    for evidence in evidence_items:
        dedupe_key = (evidence.text.casefold(), evidence.source_reference.display())
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        deduped.append(evidence)
    return deduped


def _join_risk_evidence_texts(evidence_items: list[RiskEvidence]) -> str:
    values = [evidence.text for evidence in evidence_items[:3]]
    if len(evidence_items) > 3:
        values.append(f"+{len(evidence_items) - 3} more")
    return "; ".join(values)


def _join_risk_evidence_sources(evidence_items: list[RiskEvidence]) -> str:
    unique_sources: list[str] = []
    for evidence in evidence_items:
        source = evidence.source_reference.display()
        if source not in unique_sources:
            unique_sources.append(source)
    return ", ".join(f"`{_markdown_table_cell(source)}`" for source in unique_sources)


def _render_risk_map_row(row: RiskMapRow) -> str:
    return (
        "| "
        f"{_markdown_table_cell(row.area)} | "
        f"{_markdown_table_cell(row.priority)} | "
        f"{_markdown_table_cell(row.rationale)} | "
        f"{_markdown_table_cell(row.source)} |"
    )


def _estimate_factors(
    *,
    source_facts: SourceFacts,
    source_paths: list[Path],
    markdown_sources: list[tuple[Path, str]],
) -> list[EstimateFactor]:
    source_input = source_paths[0]
    data_setup_items = _extract_data_setup_items(markdown_sources)
    retest_count = max(1, len(source_facts.environments)) + min(len(source_facts.regression_areas), 2)
    retest_sources = [*source_facts.environments, *source_facts.regression_areas]
    return [
        _count_estimate_factor(
            "screens",
            source_facts.screens,
            source_input=source_input,
            missing_evidence="No screens called out in source context.",
        ),
        _count_estimate_factor(
            "roles",
            source_facts.user_roles,
            source_input=source_input,
            missing_evidence="No distinct user roles called out in source context.",
        ),
        _count_estimate_factor(
            "states",
            source_facts.states,
            source_input=source_input,
            missing_evidence="No explicit UI or flow states called out in source context.",
        ),
        _count_estimate_factor(
            "policy_rules",
            source_facts.policies,
            source_input=source_input,
            missing_evidence="No policy rules called out in source context.",
        ),
        _count_estimate_factor(
            "integrations",
            source_facts.dependencies,
            source_input=source_input,
            missing_evidence="No integrations or dependencies called out in source context.",
        ),
        _count_estimate_factor(
            "environments",
            source_facts.environments,
            source_input=source_input,
            missing_evidence="No explicit environment matrix called out in source context.",
        ),
        _count_estimate_factor(
            "regression",
            source_facts.regression_areas,
            source_input=source_input,
            missing_evidence="No regression risks called out in source context.",
        ),
        _data_setup_estimate_factor(data_setup_items, source_input=source_input),
        _scalar_estimate_factor(
            "retest_count",
            value=f"{retest_count} passes",
            evidence=(
                f"{max(1, len(source_facts.environments))} environment pass(es) plus "
                f"{min(len(source_facts.regression_areas), 2)} regression retest pass(es)."
            ),
            source=_join_fact_sources(retest_sources) if retest_sources else f"`{_markdown_table_cell(str(source_input))}`",
            measure=retest_count,
        ),
    ]


def _count_estimate_factor(
    factor: str,
    facts: list[SourceFact],
    *,
    source_input: Path,
    missing_evidence: str,
) -> EstimateFactor:
    count = len(facts)
    evidence = _join_fact_texts(facts) if facts else missing_evidence
    source = _join_fact_sources(facts) if facts else f"`{_markdown_table_cell(str(source_input))}`"
    return _scalar_estimate_factor(
        factor,
        value=f"{count} extracted",
        evidence=evidence,
        source=source,
        measure=count,
    )


def _data_setup_estimate_factor(items: list[MarkdownItem], *, source_input: Path) -> EstimateFactor:
    count = len(items)
    evidence = _join_markdown_item_texts(items) if items else "No explicit data setup called out in source context."
    source = _join_markdown_item_sources(items) if items else f"`{_markdown_table_cell(str(source_input))}`"
    return _scalar_estimate_factor(
        "data_setup",
        value=f"{count} signals",
        evidence=evidence,
        source=source,
        measure=count,
    )


def _scalar_estimate_factor(
    factor: str,
    *,
    value: str,
    evidence: str,
    source: str,
    measure: int,
) -> EstimateFactor:
    score, rule = _score_measure(factor, measure)
    return EstimateFactor(
        factor=factor,
        value=value,
        evidence=_markdown_table_cell(evidence),
        source=source,
        score=score,
        rule=rule,
    )


def _score_measure(factor: str, measure: int) -> tuple[int, str]:
    for max_value, score, rule in _COUNT_SCORE_RULES[factor]:
        if max_value is None or measure <= max_value:
            return score, rule
    raise AssertionError(f"unreachable score rule for {factor}")


def _estimate_band(total_score: int) -> EstimateBand:
    if total_score <= 4:
        return EstimateBand(
            size="S",
            time_range="40-90 min",
            score_band="0-4 points",
            manual_qa_time=[
                "Focused smoke and negative pass: 40-90 min",
                "Evidence/report review: 10-20 min",
            ],
        )
    if total_score <= 9:
        return EstimateBand(
            size="M",
            time_range="2-4 hours",
            score_band="5-9 points",
            manual_qa_time=[
                "Primary flow, role/state, and dependency pass: 2-3 hours",
                "Regression and evidence review: 30-60 min",
            ],
        )
    return EstimateBand(
        size="L",
        time_range="1-2 days",
        score_band="10+ points",
        manual_qa_time=[
            "Full matrix pass across roles, states, environments, and dependencies: 1-1.5 days",
            "Regression retest, data setup verification, and reporting: 0.5 day",
        ],
    )


def _render_estimate_factor_rows(factors: list[EstimateFactor]) -> str:
    return "\n".join(
        "| "
        f"{factor.factor} | "
        f"{factor.value} | "
        f"{factor.evidence} | "
        f"{factor.source} | "
        f"{factor.score} | "
        f"{factor.rule} |"
        for factor in factors
    )


def _extract_data_setup_items(markdown_sources: list[tuple[Path, str]]) -> list[MarkdownItem]:
    items: list[MarkdownItem] = []
    seen: set[tuple[str, str]] = set()
    for path, markdown in markdown_sources:
        for item in _iter_markdown_items(path, markdown):
            if not _DATA_SETUP_PATTERN.search(item.text):
                continue
            dedupe_key = (item.text.casefold(), item.source_reference.display())
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            items.append(item)
    return items


def _join_fact_texts(facts: list[SourceFact]) -> str:
    values = [fact.text for fact in facts[:3]]
    if len(facts) > 3:
        values.append(f"+{len(facts) - 3} more")
    return "; ".join(values)


def _join_markdown_item_texts(items: list[MarkdownItem]) -> str:
    values = [item.text for item in items[:3]]
    if len(items) > 3:
        values.append(f"+{len(items) - 3} more")
    return "; ".join(values)


def _join_fact_sources(facts: list[SourceFact]) -> str:
    unique_sources: list[str] = []
    for fact in facts:
        source = fact.source_reference.display()
        if source not in unique_sources:
            unique_sources.append(source)
    return ", ".join(f"`{_markdown_table_cell(source)}`" for source in unique_sources)


def _join_markdown_item_sources(items: list[MarkdownItem]) -> str:
    unique_sources: list[str] = []
    for item in items:
        source = item.source_reference.display()
        if source not in unique_sources:
            unique_sources.append(source)
    return ", ".join(f"`{_markdown_table_cell(source)}`" for source in unique_sources)


def _markdown_table_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


def _render_estimate(
    title: str,
    checklist_items: list[str],
    source_paths: list[Path],
    source_facts: SourceFacts,
    markdown_sources: list[tuple[Path, str]],
) -> str:
    source_input = source_paths[0]
    factors = _estimate_factors(source_facts=source_facts, source_paths=source_paths, markdown_sources=markdown_sources)
    total_score = sum(factor.score for factor in factors)
    band = _estimate_band(total_score)
    factor_rows = _render_estimate_factor_rows(factors)
    manual_qa_time = "\n".join(f"- {item}" for item in band.manual_qa_time)
    return f"""# QA Estimate: {title}

## Summary

Estimated QA effort: {band.size} ({band.time_range})

## Basis

- Checklist items: {len(checklist_items)}
- Risk level: P0 functional
- Source input: `{source_input}`
- Total score: {total_score}
- Score band: {band.score_band}

## Evidence Factors

| Factor | Value | Evidence | Source | Score | Rule |
| --- | --- | --- | --- | ---: | --- |
{factor_rows}

## Suggested Manual QA Time

{manual_qa_time}

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
