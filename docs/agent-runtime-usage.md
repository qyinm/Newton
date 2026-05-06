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
newton qa plan <context.md> [--agent <template|codex|claude>] --target <web|web,ios> [--base-url <url>] [--out <dir>]
newton qa validate <scenario.yaml>
newton qa run <scenario.yaml> --target <target-id> [--backend <backend>] [--base-url <url>] [--out <dir>]
newton qa report <run-dir>
```

## Contract Principles

- Inputs are file-first and replayable.
- Agents should call the CLI rather than invent ad-hoc workflows.
- `qa plan` turns markdown context into a validated scenario YAML draft.
- In agent mode, Codex or Claude Code proposes YAML; Newton accepts it only after schema validation.
- `qa plan` writes `<input-stem>.<agent>.plan.json` as planning provenance, including selected agent, input, prompt/raw output paths, accepted scenario path, and validation status.
- Planning provenance is audit/replay metadata, not an execution contract.
- Outputs are normalized under `qa/runs/<run_id>/`.
- `result.json` is the machine-readable contract.
- `qa-report.md` is the human-readable summary.
- Web runs can override scenario target URLs with `--base-url` for local fixtures, preview deployments, or staging environments.
- Failure evidence is stored in the run directory and referenced from both output files.
