# Agent Runtime Usage

Newton exposes a stable CLI contract for agent runtimes and humans alike.

## Supported Callers

- Claude Code
- Codex CLI
- Hermes Agent
- plain terminal sessions
- CI jobs

## Core Commands

```bash
newton qa plan-bundle <context.md> [--source <extra.md>]... [--out <dir>]
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
- `qa plan-bundle` turns one or more markdown context files into a deterministic minimal planning bundle: scope, checklist, structured test cases CSV, risk map, QA estimate, automation candidates, QA run tracker, and manifest.
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
