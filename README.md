# Newton QA

Newton v0.1 release promise: **Generate a source-backed QA plan and run web smoke scenarios with evidence.**

Newton is an agent-native, web-first QA harness that turns sprint context into source-backed planning artifacts, executable web smoke scenarios, and evidence-backed QA reports.

## What Newton is not yet

- Not mobile E2E.
- Not a hosted runner.
- Not a full test management system.
- Not an automatic release approver.

## Install

Install the official CLI directly from GitHub:

```bash
curl -fsSL https://raw.githubusercontent.com/qyinm/Newton/main/scripts/install.sh | bash
newton version
```

The installer uses `uv tool install` when `uv` is available, falls back to `pipx`, and installs the Playwright Chromium browser by default. To install only the base CLI:

```bash
curl -fsSL https://raw.githubusercontent.com/qyinm/Newton/main/scripts/install.sh | bash -s -- --no-web
```

To install a tagged release instead of `main`, pass `--ref` through `bash -s --`:

```bash
curl -fsSL https://raw.githubusercontent.com/qyinm/Newton/main/scripts/install.sh | bash -s -- --ref v0.1.0
```

After installing, smoke the CLI from any directory without cloning this repository:

```bash
tmpdir=$(mktemp -d)
cat > "$tmpdir/login-ticket.md" <<'EOF'
# Login

Users should be able to log in with email and password.

Acceptance criteria:
- User can open login page
- User can enter email
- User can enter password
- User can submit
- User sees Dashboard
EOF
newton qa plan "$tmpdir/login-ticket.md" --agent template --target web --out "$tmpdir/scenarios"
newton qa validate "$tmpdir/scenarios/login-smoke.generated.yaml"
```

## Claude Code Plugin

Newton also ships a thin Claude Code plugin wrapper around the `newton` CLI. Add this repository as a Claude Code plugin marketplace, then install the `newton` plugin:

```bash
claude plugin marketplace add qyinm/Newton
claude plugin install newton@newton
```

Inside Claude Code, use:

```text
/newton-setup
/newton-dogfood
/newton-plan
/newton-run
/newton-bug-draft
```

The plugin also includes the `newton-qa-workflow` skill, which routes natural-language QA planning, execution, tracker, and bug-draft requests through the same `newton qa ...` CLI artifact contract.

If your Claude Code build expects in-session slash commands for plugin management, use the same arguments with `/plugin marketplace add qyinm/Newton` and `/plugin install newton@newton`.

For local development from this checkout:

```bash
python -m pip install -e '.[dev]'
```

For web execution:

```bash
python -m pip install -e '.[dev,web]'
python -m playwright install chromium
```

## Release Checklist

Before tagging a Newton release, update `CHANGELOG.md`, confirm the version in
`pyproject.toml`, and run:

```bash
uv run newton version
uv run --extra dev --extra web pytest tests/test_cli.py -v
uv build
```

## Plan a QA Bundle

Generate a minimal PRD-style planning bundle from markdown product/ticket context:

```bash
newton qa plan-bundle qa/inputs/login-ticket.md \
  --source qa/inputs/login-policy.md \
  --agent template \
  --out qa/plans
```

The repository includes this demo input pair and the checked-in generated bundle under `qa/plans/login/` so agents and CI can validate the PRD planning contract without regenerating fixtures first.

Use `--source` to merge extra markdown sources such as policy notes, staging notes, or design annotations into the same checklist/test-case bundle. `--agent template` is the deterministic fallback and does not call an external agent. `risk-map.md` includes baseline PRD risk categories: edge case, network failure, permission/role, policy conflict, and regression.

To let an external agent draft the bundle while Newton validates and materializes the artifact contract, use `--agent codex` or `--agent claude`:

```bash
newton qa plan-bundle qa/inputs/login-ticket.md \
  --source qa/inputs/login-policy.md \
  --agent codex \
  --out qa/plans
```

Agent-backed bundle generation preserves the prompt, raw stdout, and accepted JSON next to the generated artifacts. The agent must include `qa_estimate.evidence_factors`; each factor cites a provided source path or filename, and Newton rejects the bundle before writing `manifest.json` if the estimate lacks source-linked evidence. Newton verifies source linkage structurally, not semantic truth.

```text
qa/plans/login/bundle-generation.codex.prompt.txt
qa/plans/login/bundle-generation.codex.raw.txt
qa/plans/login/bundle-generation.codex.json
```

Outputs:

```text
qa/plans/login/qa-scope.md
qa/plans/login/checklist.md
qa/plans/login/test-cases.csv
qa/plans/login/risk-map.md
qa/plans/login/qa-estimate.md
qa/plans/login/automation-candidates.md
qa/plans/login/qa-run-tracker.md
qa/plans/login/manifest.json
```

After updating the tracker with a checklist result, generate a bug ticket draft from the first failed item:

```bash
newton qa tracker-update qa/plans/login/qa-run-tracker.md \
  --item 5 \
  --env stg \
  --status failed \
  --notes "Dashboard never appears after submit"
newton qa tracker-update-from-run qa/plans/login/qa-run-tracker.md \
  --item 1 \
  --env stg \
  --run qa/runs/run_123
newton qa bug-draft qa/plans/login/qa-run-tracker.md
```

Output:

```text
qa/plans/login/bug-ticket-draft.md
```

Validate the generated artifact contract before handing the bundle to another agent or CI job:

```bash
newton qa bundle-validate qa/plans/login
```

Expected:

```text
valid_bundle: login
artifacts: 8
checklist_items: 8
test_cases: 8
tracker_items: 8
```

Optionally request an advisory QA review after generation. `bundle-review` does not generate or edit the bundle: `template` is deterministic; `codex` and `claude` use an external agent and preserve prompt/raw output next to the review artifacts. Default external review commands are constrained (`codex` read-only sandbox, `claude` tools disabled); `--agent-command` is an explicit override for tests or custom setups:

```bash
newton qa bundle-review qa/plans/login --agent template
newton qa bundle-review qa/plans/login --agent codex
```

Outputs:

```text
qa/plans/login/bundle-review.template.json
qa/plans/login/bundle-review.template.md
qa/plans/login/bundle-review.codex.prompt.txt
qa/plans/login/bundle-review.codex.raw.txt
qa/plans/login/bundle-review.codex.json
qa/plans/login/bundle-review.codex.md
```

## Plan a Scenario

Generate a scenario draft from markdown product/ticket context. The default `template` agent is deterministic; `codex` and `claude` use the same external-agent YAML contract:

```bash
newton qa plan qa/inputs/login-ticket.md --agent template --target web --out qa/scenarios
newton qa plan qa/inputs/login-ticket.md --agent codex --target web --out qa/scenarios
```

Outputs:

```text
qa/scenarios/login-smoke.generated.yaml
qa/scenarios/login_ticket.template.plan.json
```

Agent-backed planning also records the exact prompt and raw stdout:

```text
qa/scenarios/login_ticket.codex.prompt.txt
qa/scenarios/login_ticket.codex.raw.txt
qa/scenarios/login_ticket.codex.plan.json
```

Experimental roadmap draft, not part of the v0.1 web-first release promise:

```bash
newton qa plan qa/inputs/login-ticket.md --target web,ios --out qa/scenarios
```

`qa plan` validates the generated scenario before returning successfully.

## Validate a Scenario

```bash
newton qa validate qa/scenarios/web-login-smoke.yaml
```

Expected:

```text
valid: web-login-smoke
```

## Dry Run

```bash
newton qa run qa/scenarios/web-login-smoke.yaml --target web --backend dry-run --out qa/runs
```

To link a generated scenario back to its planning provenance, pass the accepted plan JSON:

```bash
newton qa run qa/scenarios/login-smoke.generated.yaml \
  --target web \
  --backend dry-run \
  --plan-provenance qa/scenarios/login_ticket.codex.plan.json \
  --out qa/runs
```

The run `result.json` and `qa-report.md` include a small `planning`/Planning Provenance section with the provenance path, agent, source input, accepted scenario path, and validation status.

Outputs:

```text
qa/runs/index.jsonl
qa/runs/run_*/result.json
qa/runs/run_*/qa-report.md
```

List local run history:

```bash
newton qa runs --out qa/runs
```

Expected:

```text
run_e213334d75db  passed  login-smoke  web
```

## Web Run

Install Chromium once, then run a web scenario with Playwright:

```bash
python -m pip install -e '.[web]'
python -m playwright install chromium
newton qa run qa/scenarios/web-login-smoke.yaml \
  --target web \
  --backend playwright \
  --base-url https://staging.example.com \
  --out qa/runs
```

On failure, Newton writes debuggable evidence into the run directory:

```text
qa/runs/run_*/result.json
qa/runs/run_*/qa-report.md
qa/runs/run_*/failure-step-*.png
qa/runs/run_*/playwright-trace.zip
```

Open traces with:

```bash
python -m playwright show-trace qa/runs/<run_id>/playwright-trace.zip
```

## Dogfood: full QA loop

The checked-in dogfood package under `qa/dogfood/login/` proves the full file-first loop on a realistic multi-source login sprint:

```bash
bash scripts/demo-web-release.sh
```

The demo script starts local fixtures, regenerates the planning bundle, validates three web scenarios, runs passing and failing Playwright cases, updates the tracker from the failed run, writes a bug draft, and prints the artifact paths. The committed dogfood run set includes passing runs plus a failing Playwright run with screenshot and trace evidence.

## Backends

- `dry-run`: validates the full Newton pipeline without opening a browser or simulator
- `playwright`: executes web scenarios and is the v0.1 release-quality backend
- `maestro`: experimental roadmap adapter that compiles Newton iOS bindings to Maestro flow YAML and saves it as an artifact; it is not part of the v0.1 release promise
