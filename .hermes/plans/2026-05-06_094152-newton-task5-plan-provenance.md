# Task 5 Plan: Minimal `newton qa plan` Provenance Artifact

## Goal

Add a minimal provenance artifact for every `newton qa plan` run that records:

- selected planning agent
- input context path
- prompt path, when applicable
- raw output path, when applicable
- accepted scenario path, when validation succeeds
- validation status

This should make agent-generated QA artifacts observable and replayable without adding retries, ranking, multi-agent behavior, semantic judging, or an event store.

## Current context / assumptions

- Current branch is `main`.
- Latest pushed implementation is `82a1531 feat: add qa plan agent harness`.
- `newton qa plan` currently supports:
  - `--agent template`
  - `--agent codex`
  - `--agent claude`
- Agent planning lives in `src/newton/agent_planner.py`.
- CLI routing lives in `src/newton/cli.py`.
- Existing agent behavior:
  - builds a shared prompt with `build_agent_prompt(...)`
  - runs Codex or Claude through a subprocess
  - saves raw stdout to `<input-stem>.<agent>.raw.txt`
  - extracts YAML into a temporary candidate file
  - validates with `load_scenario(candidate_path)`
  - writes `<scenario-id>.generated.yaml` only after validation succeeds
- Deterministic/template planning lives in `src/newton/planner.py` and is now the fallback/reference path.
- This task should stay provenance-only.

## Proposed approach

Introduce a small plan provenance record written next to generated scenario artifacts in the selected `--out` directory.

Recommended artifact shape:

```text
<out-dir>/<input-stem>.<agent>.plan.json
```

Example for Codex:

```text
qa/scenarios/login_ticket.codex.plan.json
```

Keep JSON intentionally flat and easy to inspect:

```json
{
  "agent": "codex",
  "input_path": "tests/fixtures/inputs/login_ticket.md",
  "target": "web",
  "base_url": "http://127.0.0.1:8000",
  "prompt_path": "qa/scenarios/login_ticket.codex.prompt.txt",
  "raw_output_path": "qa/scenarios/login_ticket.codex.raw.txt",
  "accepted_scenario_path": "qa/scenarios/login-smoke.generated.yaml",
  "validation_status": "accepted",
  "validation_error": null
}
```

For failed validation:

```json
{
  "agent": "codex",
  "input_path": "tests/fixtures/inputs/login_ticket.md",
  "target": "web",
  "base_url": "http://127.0.0.1:8000",
  "prompt_path": "qa/scenarios/login_ticket.codex.prompt.txt",
  "raw_output_path": "qa/scenarios/login_ticket.codex.raw.txt",
  "accepted_scenario_path": null,
  "validation_status": "rejected",
  "validation_error": "agent output did not validate; raw output saved to ..."
}
```

For `--agent template`, use the same artifact concept but allow prompt/raw paths to be null:

```json
{
  "agent": "template",
  "input_path": "tests/fixtures/inputs/login_ticket.md",
  "target": "web",
  "base_url": "http://127.0.0.1:8000",
  "prompt_path": null,
  "raw_output_path": null,
  "accepted_scenario_path": "qa/scenarios/login-smoke.generated.yaml",
  "validation_status": "accepted",
  "validation_error": null
}
```

## Step-by-step plan

1. **Add focused failing tests first**
   - Add or extend tests in `tests/test_agent_planner.py`:
     - valid fake agent output creates:
       - accepted scenario YAML
       - raw output file
       - prompt file
       - provenance JSON
     - provenance JSON records:
       - `agent`
       - `input_path`
       - `target`
       - `base_url`
       - `prompt_path`
       - `raw_output_path`
       - `accepted_scenario_path`
       - `validation_status: accepted`
       - `validation_error: null`
     - invalid fake agent output creates provenance JSON with:
       - `validation_status: rejected`
       - `accepted_scenario_path: null`
       - non-empty `validation_error`
       - raw output path preserved
   - Add or extend tests in `tests/test_cli.py`:
     - `newton qa plan ... --agent codex --agent-command <fake-command>` prints the existing `planned:` and `valid:` output unchanged.
     - Optional: assert provenance file exists in the `--out` directory.

2. **Add a tiny provenance helper**
   - Preferred low-risk option: implement inside `src/newton/agent_planner.py` first.
   - Possible helper functions:
     - `plan_provenance_path(input_path: Path, agent: str, out_dir: Path) -> Path`
     - `_write_plan_provenance(path: Path, data: dict[str, object]) -> None`
   - Keep it simple JSON via Python stdlib `json.dumps(..., indent=2)`.
   - Avoid new dependencies.

3. **Persist the agent prompt**
   - In `plan_scenario_with_agent(...)`, after `out_dir.mkdir(...)`, write:
     - `<input-stem>.<agent>.prompt.txt`
   - Use the exact prompt sent to the agent.
   - Record that path in provenance.

4. **Write provenance on successful agent planning**
   - After `load_scenario(candidate_path)` succeeds and accepted YAML is written:
     - write plan JSON with `validation_status: accepted`.
   - Keep current return type as `Path` to avoid broad API churn.
   - Do not change CLI output unless needed.

5. **Write provenance on failed agent planning**
   - For subprocess failure:
     - raw output is already saved.
     - write provenance with `validation_status: rejected` and `validation_error`.
   - For schema validation failure:
     - raw output is already saved.
     - candidate YAML may exist temporarily; do not expose it unless already useful.
     - write provenance before raising `AgentPlanningError`.
   - Preserve current failure behavior: command still fails.

6. **Add template provenance with minimal code churn**
   - Option A, smallest: add provenance writing in `src/newton/cli.py` after `plan_scenario_from_markdown(...)` succeeds for `--agent template`.
   - Option B, cleaner but slightly more invasive: add a helper module like `src/newton/plan_provenance.py` shared by template and agent paths.
   - Recommended: Option B only if duplication becomes awkward; otherwise keep it simple.

7. **Update docs**
   - `README.md`
     - Add one short sentence under planning docs: every `qa plan` writes a small provenance JSON next to outputs.
   - `docs/qa-planning.md`
     - Add artifact examples.
   - `docs/agent-runtime-usage.md`
     - State that agents should treat provenance JSON as audit/replay metadata, not as an execution contract.

8. **Run verification**
   - Focused tests first:
     ```bash
     /opt/homebrew/bin/uv run --python 3.13 --with-editable '.[dev,web]' pytest tests/test_agent_planner.py tests/test_cli.py::test_qa_plan_agent_codex_uses_shared_agent_contract -q
     ```
   - Full test suite:
     ```bash
     /opt/homebrew/bin/uv run --python 3.13 --with-editable '.[dev,web]' pytest -q
     ```
   - Manual CLI smoke with fake or template mode:
     ```bash
     rm -rf /tmp/newton-task5-plan-check
     /opt/homebrew/bin/uv run --python 3.13 --with-editable '.[dev,web]' \
       newton qa plan tests/fixtures/inputs/login_ticket.md --agent template --target web --out /tmp/newton-task5-plan-check
     ```
   - Verify expected artifacts exist:
     ```text
     /tmp/newton-task5-plan-check/login-smoke.generated.yaml
     /tmp/newton-task5-plan-check/login_ticket.template.plan.json
     ```

## Files likely to change

- `src/newton/agent_planner.py`
  - Save prompt file.
  - Write accepted/rejected provenance JSON for `codex` and `claude` agent runs.

- `src/newton/cli.py`
  - Add minimal provenance write for `--agent template`, unless shared helper makes this unnecessary.

- `src/newton/plan_provenance.py` *(optional)*
  - Only create if shared JSON writing between template and agent paths would otherwise duplicate too much code.

- `tests/test_agent_planner.py`
  - Add accepted/rejected provenance assertions.

- `tests/test_cli.py`
  - Add CLI-level provenance existence assertion.

- `README.md`
  - Short documentation note.

- `docs/qa-planning.md`
  - Artifact examples and expected files.

- `docs/agent-runtime-usage.md`
  - Agent contract/provenance clarification.

## Tests / validation

Minimum acceptance criteria:

- `--agent codex` with fake command writes:
  - prompt file
  - raw output file
  - accepted scenario YAML
  - provenance JSON with `validation_status: accepted`
- invalid fake agent output writes:
  - raw output file
  - provenance JSON with `validation_status: rejected`
  - no accepted scenario path
  - command still fails
- `--agent template` writes:
  - accepted scenario YAML
  - provenance JSON with `agent: template`
  - `prompt_path: null`
  - `raw_output_path: null`
- Existing CLI output remains compatible:
  - `planned: ...`
  - `valid: ...`
- Full suite passes.

## Risks / tradeoffs

- **Path format drift**
  - Risk: absolute paths make artifacts less portable.
  - Recommendation: record paths as strings exactly as Newton resolved/wrote them for now; do not build a path abstraction yet.

- **Template path awkwardness**
  - Risk: provenance belongs conceptually to planning, but template planner currently only returns a path.
  - Recommendation: keep the public return type unchanged and write template provenance at CLI boundary for this task.

- **Too much lineage too soon**
  - Risk: adding IDs, timestamps, hashes, event store, or parent-child lineage expands scope.
  - Recommendation: do not add those in Task 5.

- **Failure provenance coverage**
  - Risk: exceptions before `out_dir` exists or before paths are known can complicate recording.
  - Recommendation: only guarantee provenance once input exists, agent is selected, and `out_dir` has been created.

## Explicit non-goals

- No retry loop.
- No best-of-N generation.
- No Codex vs Claude comparison.
- No multi-agent orchestration.
- No semantic quality judge.
- No automatic `qa run` after planning.
- No persistent EventStore.
- No immutable seed spec system.
- No scenario evolution or self-healing.
- No browser recording.
- No cloud sandbox or Crabbox-style remote runner.

## Recommended commit message

```text
feat: record qa plan provenance artifacts
```
