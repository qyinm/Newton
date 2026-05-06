# Task 5 Plan: Minimal `qa plan` provenance artifact

## Goal

Add the smallest useful Ouroboros-inspired next step to Newton: every `newton qa plan` run should leave behind a lightweight, replay/debug-friendly planning provenance artifact.

This should make agent planning observable without turning Newton into a full agent loop, judge, retry system, or product QA brain.

## Recommended Task 5

> Task 5: Add a minimal `newton qa plan` provenance artifact that records the selected agent, input context path, prompt/raw output paths, accepted scenario path, and validation status for each planning run.

## Current context / assumptions

- Current branch: `main`.
- Latest relevant commit: `82a1531 feat: add qa plan agent harness`.
- `newton qa plan --agent <template|codex|claude>` already exists.
- Agent mode is implemented in `src/newton/agent_planner.py`.
- Template fallback is implemented in `src/newton/planner.py`.
- CLI entrypoint is `src/newton/cli.py`.
- Current test file for agent planning is `tests/test_agent_planner.py`.
- Newton currently validates generated scenario YAML with `load_scenario()` before accepting it.
- Invalid agent output is already preserved as `<input-stem>.<agent>.raw.txt`.

## Why this is the right next step

This is the smallest non-overengineered way to reflect more of Ouroboros:

- Ouroboros-like: observable agent execution contract and artifact trail.
- Newton-like: file-first QA harness, validated scenario YAML, local CLI.
- Not over-specified: no retries, no ranking, no multi-agent, no semantic judge, no self-healing.

The user concern was that Newton should be inspired by Ouroboros/crabbox. Task 4 added the agent harness. Task 5 should make that harness auditable.

## Proposed approach

Add a small JSON metadata file next to generated planning artifacts.

Example output files after agent planning:

```text
qa/scenarios/login_ticket.codex.prompt.txt
qa/scenarios/login_ticket.codex.raw.txt
qa/scenarios/agent-login-smoke.generated.yaml
qa/scenarios/login_ticket.codex.plan.json
```

Example `login_ticket.codex.plan.json`:

```json
{
  "agent": "codex",
  "input_path": "tests/fixtures/inputs/login_ticket.md",
  "target": "web",
  "base_url": "http://127.0.0.1:8000",
  "prompt_path": "login_ticket.codex.prompt.txt",
  "raw_output_path": "login_ticket.codex.raw.txt",
  "accepted_scenario_path": "agent-login-smoke.generated.yaml",
  "validation_status": "accepted",
  "scenario_id": "agent-login-smoke"
}
```

For invalid agent output:

```json
{
  "agent": "codex",
  "input_path": "tests/fixtures/inputs/login_ticket.md",
  "target": "web",
  "base_url": "http://127.0.0.1:8000",
  "prompt_path": "login_ticket.codex.prompt.txt",
  "raw_output_path": "login_ticket.codex.raw.txt",
  "accepted_scenario_path": null,
  "validation_status": "rejected",
  "scenario_id": null,
  "error": "agent output did not validate"
}
```

Keep it as JSON for now because it is easy to assert in tests and easy for agents to consume later.

## Step-by-step plan

### 1. Add failing tests first

Update `tests/test_agent_planner.py`.

Add test: `test_agent_planner_writes_accepted_plan_provenance`

Expected behavior:

- Use fake Codex command returning valid YAML.
- Call `plan_scenario_with_agent(...)`.
- Assert generated scenario exists.
- Assert provenance JSON exists at:

```text
<out_dir>/login_ticket.codex.plan.json
```

- Assert JSON fields:
  - `agent == "codex"`
  - `input_path` ends with `tests/fixtures/inputs/login_ticket.md`
  - `target == "web"`
  - `base_url == "http://127.0.0.1:8000"`
  - `prompt_path == "login_ticket.codex.prompt.txt"`
  - `raw_output_path == "login_ticket.codex.raw.txt"`
  - `accepted_scenario_path == "agent-login-smoke.generated.yaml"`
  - `validation_status == "accepted"`
  - `scenario_id == "agent-login-smoke"`

Add test: `test_agent_planner_writes_rejected_plan_provenance`

Expected behavior:

- Fake command returns invalid YAML.
- `plan_scenario_with_agent(...)` raises `AgentPlanningError`.
- Raw output file exists.
- Provenance JSON exists.
- JSON fields:
  - `validation_status == "rejected"`
  - `accepted_scenario_path is None`
  - `scenario_id is None`
  - `error` contains validation failure summary.

Optional but still small:

- Assert prompt file exists and contains `Output only valid Newton scenario YAML`.

### 2. Confirm RED

Run focused tests:

```bash
/opt/homebrew/bin/uv run --python 3.13 --with-editable '.[dev,web]' \
  pytest tests/test_agent_planner.py -q
```

Expected: new provenance tests fail because no `.plan.json` / prompt file exists yet.

### 3. Implement minimal provenance writer

Modify `src/newton/agent_planner.py` only if possible.

Implementation sketch:

- Import `json`.
- After `out_dir.mkdir(...)`, define:

```python
prompt_path = out_dir / f"{input_path.stem}.{agent}.prompt.txt"
raw_output_path = out_dir / f"{input_path.stem}.{agent}.raw.txt"
plan_path = out_dir / f"{input_path.stem}.{agent}.plan.json"
```

- Write prompt before running the agent:

```python
prompt_path.write_text(prompt)
```

- Add small helper:

```python
def _write_plan_provenance(...):
    plan_path.write_text(json.dumps(data, indent=2) + "\n")
```

- On success, write `validation_status: accepted` after `load_scenario(candidate_path)` succeeds.
- On command failure or validation failure, write `validation_status: rejected` before raising `AgentPlanningError`.

Keep paths relative to `out_dir` inside JSON for portability.

### 4. Keep template mode unchanged for now

Do **not** add provenance to `--agent template` in this task unless implementation becomes trivial.

Reason:

- Task 5 is about agent harness observability.
- Template mode is fallback/reference.
- Expanding template provenance risks scope creep.

If consistency becomes necessary later, add it as a separate small task.

### 5. Update CLI output only if needed

Prefer no CLI output changes.

Current CLI output:

```text
planned: <path>
valid: <scenario-id>
```

Keep it stable.

If we expose provenance path, do it later as a separate UX polish task.

### 6. Update docs lightly

Modify only one or two docs sections:

- `docs/qa-planning.md`
- maybe `docs/agent-runtime-usage.md`

Document:

- agent planning writes prompt/raw/provenance artifacts.
- invalid agent output is rejected but raw/provenance files are preserved.
- provenance is for debugging/replay, not an agent memory or event store.

Avoid adding architecture diagrams or a larger event-store concept.

### 7. Verify

Run focused tests:

```bash
/opt/homebrew/bin/uv run --python 3.13 --with-editable '.[dev,web]' \
  pytest tests/test_agent_planner.py -q
```

Run full suite:

```bash
/opt/homebrew/bin/uv run --python 3.13 --with-editable '.[dev,web]' pytest -q
```

Optional manual check with fake command remains in tests only. Do not require real Codex/Claude auth for CI.

Before commit, remove accidental uv lockfile:

```bash
rm -f uv.lock
```

## Files likely to change

Primary:

- `src/newton/agent_planner.py`
- `tests/test_agent_planner.py`

Docs:

- `docs/qa-planning.md`
- optionally `docs/agent-runtime-usage.md`

No expected changes:

- `src/newton/runner.py`
- `src/newton/backends/web_playwright.py`
- scenario schema models unless a new formal model is explicitly needed, which should be avoided for this task.

## Tests / validation

Minimum expected verification:

```bash
/opt/homebrew/bin/uv run --python 3.13 --with-editable '.[dev,web]' \
  pytest tests/test_agent_planner.py -q

/opt/homebrew/bin/uv run --python 3.13 --with-editable '.[dev,web]' pytest -q
```

Expected final test count should be current `35 passed` plus new tests.

## Risks and tradeoffs

### Risk: provenance turns into event store

Avoid this. The artifact should be one JSON file per `qa plan` run, not a persistent database or lineage system.

### Risk: storing prompt may leak sensitive context

This is acceptable for local-first Newton, but docs should mention that prompt/raw artifacts may contain input context. Do not store credentials intentionally.

### Risk: path portability

Use relative artifact filenames inside JSON where possible. Keep absolute paths out of the provenance file unless needed.

### Risk: expanding into retry/self-healing

Do not add retry, repair, ranking, or quality scoring. This task is observability only.

## Open questions

None blocking.

Small decision during implementation:

- Should rejected provenance be written for command-not-found errors?
  - Recommendation: yes if `out_dir` exists and paths can be written; include `validation_status: "rejected"` and `error`.
  - But do not overcomplicate if `FileNotFoundError` happens before raw output exists.

## Out of scope

Explicitly not included in Task 5:

- multi-agent planning
- Codex vs Claude comparison
- retry loop
- self-healing selectors
- semantic quality judge
- scenario lineage graph
- SQLite/EventStore
- cloud sandbox
- automatic `qa run` after `qa plan`
- GitHub issue/PR ingestion
