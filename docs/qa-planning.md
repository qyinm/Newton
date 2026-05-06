# QA Planning

Newton exposes two planning-layer commands:

- `newton qa plan-bundle`: converts markdown product or ticket context into a minimal QA planning bundle.
- `newton qa plan`: converts markdown product or ticket context into a validated Newton scenario YAML draft.

## Planning bundle

Use `plan-bundle` when you want PRD-style QA planning artifacts rather than an executable scenario:

```bash
newton qa plan-bundle qa/inputs/login-ticket.md --out qa/plans
```

Output:

```text
qa/plans/login/qa-scope.md
qa/plans/login/checklist.md
qa/plans/login/risk-map.md
qa/plans/login/qa-estimate.md
qa/plans/login/automation-candidates.md
qa/plans/login/qa-run-tracker.md
qa/plans/login/manifest.json
```

The bundle is intentionally small and deterministic:

- `qa-scope.md`: source, goal, in-scope, and out-of-scope summary.
- `checklist.md`: manual checklist derived from acceptance criteria bullets.
- `risk-map.md`: one minimal functional P0 risk row.
- `qa-estimate.md`: deterministic small-effort estimate with checklist count, P0 basis, source input, manual QA time, and assumptions.
- `automation-candidates.md`: first checklist item recommended for smoke automation; remaining items kept manual for now.
- `qa-run-tracker.md`: initial dev/stg/prod and per-checklist status tracker, all set to `not run`.
- `manifest.json`: machine-readable paths for the bundle artifacts.

It does not call Codex, Claude, or any external agent.

## Tracker updates and bug ticket drafts

Update a generated `qa-run-tracker.md` checklist item from the CLI:

```bash
newton qa tracker-update qa/plans/login/qa-run-tracker.md \
  --item 5 \
  --env stg \
  --status failed \
  --notes "Dashboard never appears after submit"
```

Or link a completed Newton run result to a tracker item:

```bash
newton qa tracker-update-from-run qa/plans/login/qa-run-tracker.md \
  --item 1 \
  --env stg \
  --run qa/runs/run_123
```

Supported statuses are `not run`, `passed`, `failed`, `blocked`, and `needs retest`. Newton updates the selected checklist item and the matching environment status in place. `tracker-update-from-run` maps `passed`/`failed` run results to the same tracker status and records the run report path in notes.

After a human or agent marks a checklist item as failed, generate a minimal bug ticket draft:

```bash
newton qa bug-draft qa/plans/login/qa-run-tracker.md
```

Newton reads the first failed tracker item and writes `bug-ticket-draft.md` next to the tracker by default. The draft includes the failed checklist item, environment, notes, reproduction steps, expected result, actual result, and source tracker path.

## Scenario planning

`newton qa plan` is Newton's scenario planning command. It converts markdown product or ticket context into a validated Newton scenario YAML draft.

## MVP scope

The planner supports two intentionally small modes:

- `--agent template`: deterministic fallback; no external agent call.
- `--agent codex` / `--agent claude`: external agent harness; the agent proposes YAML and Newton accepts it only after schema validation.

Supported deterministic template flow:

- login smoke test
- web target
- optional web+iOS cross-platform target

Input requirements:

- markdown file
- generated scenario is self-validated before the command succeeds

## Usage

Template fallback:

```bash
newton qa plan qa/inputs/login-ticket.md --agent template --target web --out qa/scenarios
```

Codex-backed agent harness:

```bash
newton qa plan qa/inputs/login-ticket.md --agent codex --target web --out qa/scenarios
```

Claude Code uses the same contract and is optional when the CLI is installed and authenticated:

```bash
newton qa plan qa/inputs/login-ticket.md --agent claude --target web --out qa/scenarios
```

Output:

```text
qa/scenarios/login-smoke.generated.yaml
```

Cross-platform draft:

```bash
newton qa plan qa/inputs/login-ticket.md --target web,ios --out qa/scenarios
```

Override the generated web target's base URL:

```bash
newton qa plan qa/inputs/login-ticket.md \
  --target web \
  --base-url https://staging.example.com \
  --out qa/scenarios
```

## Agent harness contract

For `--agent codex` and `--agent claude`, Newton:

1. builds a strict prompt/output contract from the markdown context,
2. runs the selected CLI,
3. extracts YAML from stdout,
4. validates it with Newton's scenario loader,
5. writes `<scenario-id>.generated.yaml` only if validation passes.

Invalid agent output fails the command and preserves raw stdout as `<input-stem>.<agent>.raw.txt` in the output directory.

## Planning provenance

Every successful `qa plan` run writes a flat provenance JSON next to generated scenarios:

```text
qa/scenarios/<input-stem>.<agent>.plan.json
```

For `--agent codex` and `--agent claude`, Newton also preserves the exact prompt and raw stdout:

```text
qa/scenarios/<input-stem>.<agent>.prompt.txt
qa/scenarios/<input-stem>.<agent>.raw.txt
```

The provenance JSON records only the minimal audit trail:

```json
{
  "agent": "codex",
  "input_path": "qa/inputs/login-ticket.md",
  "target": "web",
  "base_url": "http://127.0.0.1:8000",
  "prompt_path": "qa/scenarios/login-ticket.codex.prompt.txt",
  "raw_output_path": "qa/scenarios/login-ticket.codex.raw.txt",
  "accepted_scenario_path": "qa/scenarios/login-smoke.generated.yaml",
  "validation_status": "accepted",
  "validation_error": null
}
```

If agent output is rejected, `validation_status` is `rejected`, `accepted_scenario_path` is `null`, and the raw output remains available for debugging. Template mode uses the same plan JSON with `prompt_path` and `raw_output_path` set to `null`.

## Linking planning to execution

`qa run` can optionally link a run report to an accepted planning provenance file:

```bash
newton qa run qa/scenarios/login-smoke.generated.yaml \
  --target web \
  --backend playwright \
  --base-url http://127.0.0.1:8000 \
  --plan-provenance qa/scenarios/login_ticket.codex.plan.json \
  --out qa/runs
```

Newton does not call the agent again. It reads the provenance JSON and copies only small lineage metadata into `qa/runs/<run_id>/result.json` and `qa-report.md`:

```json
"planning": {
  "provenance_path": "qa/scenarios/login_ticket.codex.plan.json",
  "agent": "codex",
  "input_path": "qa/inputs/login-ticket.md",
  "accepted_scenario_path": "qa/scenarios/login-smoke.generated.yaml",
  "validation_status": "accepted"
}
```

Only `validation_status: "accepted"` provenance can be linked to a run. When Newton knows the scenario file path, the provenance `accepted_scenario_path` must refer to the same scenario being run.

## Generated web selectors

The login smoke template uses stable web selectors:

- email: `role: textbox`, `name: Email`
- password: `test_id: password-input`
- submit: `role: button`, `name: Log in`
- success assertion: visible text `Dashboard`

## Follow-up

A future planning layer can add:

- multiple scenario templates
- richer acceptance-criteria parsing
- Codex/Claude command configuration
- issue/PRD ingestion
- selector mapping from design systems or product metadata
