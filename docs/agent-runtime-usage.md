# Agent Runtime Usage

Newton exposes a stable CLI contract for agent runtimes and humans alike.

## v0.1 Release Contract

Newton v0.1 is web-first: generate a source-backed QA plan, draft a web smoke scenario, run it with evidence, and return normalized artifacts another agent can inspect.

The release-quality execution backend is Playwright for web scenarios. Cross-platform targets such as `web,ios` remain an experimental roadmap surface where the CLI supports draft or adapter artifacts; they are not the v0.1 execution promise.

## Supported Callers

- Claude Code
- Codex CLI
- Hermes Agent
- plain terminal sessions
- CI jobs

## Core Commands

```bash
newton qa plan-bundle <context.md> [--source <extra.md>]... [--out <dir>]
newton qa bundle-validate <bundle-dir>
newton qa bundle-review <bundle-dir> [--agent <template|codex|claude>]
newton qa tracker-update <qa-run-tracker.md> --item <n> --env <dev|stg|prod> --status <status> [--notes <text>]
newton qa tracker-update-from-run <qa-run-tracker.md> --item <n> --env <dev|stg|prod> --run <run-dir>
newton qa bug-draft <qa-run-tracker.md> [--out <bug-ticket-draft.md>]
newton qa plan <context.md> [--agent <template|codex|claude>] --target <web|web,ios> [--base-url <url>] [--out <dir>]
newton qa validate <scenario.yaml>
newton qa run <scenario.yaml> --target <target-id> [--backend <backend>] [--base-url <url>] [--plan-provenance <plan.json>] [--out <dir>]
newton qa runs [--out <dir>]
newton qa report <run-dir>
```

## Contract Principles

- Inputs are file-first and replayable.
- Agents should call the CLI rather than invent ad-hoc workflows.
- `qa plan-bundle` turns one or more markdown context files into a deterministic minimal planning bundle: scope, checklist, structured test cases CSV, PRD baseline risk map, QA estimate, automation candidates, QA run tracker, and manifest.
- `qa bundle-validate` deterministically checks a planning bundle's required files, manifest paths, item counts, and baseline risks before agent/CI handoff.
- `qa bundle-review` optionally asks `template`, Codex, or Claude for advisory QA quality feedback and writes validated review JSON/Markdown artifacts. Default external review commands are constrained to read-only/no-tool mode; custom agent commands are an explicit escape hatch.
- `qa tracker-update` updates one generated QA run tracker checklist item plus the selected environment status.
- `qa tracker-update-from-run` maps a completed `qa run` result onto one tracker item and records the run report path in notes.
- `qa bug-draft` reads the first failed checklist item from a QA run tracker and writes `bug-ticket-draft.md`.
- `qa plan` turns markdown context into a validated scenario YAML draft.
- In agent mode, Codex or Claude Code proposes YAML; Newton accepts it only after schema validation.
- `qa plan` writes `<input-stem>.<agent>.plan.json` as planning provenance, including selected agent, input, prompt/raw output paths, accepted scenario path, and validation status.
- Planning provenance is audit/replay metadata, not an execution contract.
- `qa run --plan-provenance <plan.json>` links an accepted planning artifact to execution output without re-running the agent.
- Linked runs copy only minimal planning metadata into `result.json` and `qa-report.md`: provenance path, agent, source input, accepted scenario path, and validation status.
- Rejected planning provenance cannot be linked to a run, and a linked provenance file must point at the scenario being run.
- Outputs are normalized under `qa/runs/<run_id>/`.
- `qa run` also appends one JSON object per run to `qa/runs/index.jsonl`.
- `qa runs --out qa/runs` prints a minimal local history from the index: run id, status, scenario id, and target id.
- `result.json` is the machine-readable contract.
- `qa-report.md` is the human-readable summary.
- Web runs can override scenario target URLs with `--base-url` for local fixtures, preview deployments, or staging environments.
- Failure evidence is stored in the run directory and referenced from both output files.

## v0.1 Artifact Fields

Every v0.1 planning bundle and run result must include `"contract_version": "v0.1"`. Agents and CI readers should reject artifacts that omit `contract_version`; regenerate those artifacts with a v0.1 Newton build before treating them as release-contract outputs.

Planning bundle directories must contain:

- `manifest.json`
- `qa-scope.md`
- `checklist.md`
- `test-cases.csv`
- `risk-map.md`
- `qa-estimate.md`
- `automation-candidates.md`
- `qa-run-tracker.md`

`manifest.json` requires:

- `contract_version`: `"v0.1"`
- `plan_id`: non-empty plan identifier
- `input_path`: primary markdown context path
- `source_paths`: ordered source path list including the primary input
- `artifacts`: object with paths for `qa_scope`, `checklist`, `test_cases`, `risk_map`, `qa_estimate`, `automation_candidates`, and `qa_run_tracker`

Agent-generated planning bundles may also include `agent` and `generation` metadata. Deterministic validation still requires the same v0.1 `manifest.json` fields and artifacts.

Run `result.json` requires:

- `contract_version`: `"v0.1"`
- `run_id`: run directory identifier
- `scenario_id`: scenario id from the accepted scenario YAML
- `target_id`: executed target id
- `platform`: `web` or `ios`
- `status`: `passed`, `failed`, or `skipped`
- `steps`: ordered step result objects with `id`, `action`, `status`, optional `error`, optional `duration_ms`, and step-level `evidence`
- `evidence`: run-level evidence artifact list

Linked runs may also include `planning` metadata with the provenance path, agent, input path, accepted scenario path, and validation status.
