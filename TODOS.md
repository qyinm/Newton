# Newton Release TODOs

Newton's first serious release target is a **web-first, agent-native QA planning and execution service**.

The release should not try to prove mobile E2E, remote runners, or selector self-healing yet. It should prove that a QA engineer or coding agent can turn sprint context into a defensible QA plan, generate a web executable scenario, run it against a local or staging target, collect evidence, update tracker state, and draft a bug ticket through one replayable CLI/plugin contract.

## Release Principle

- Web execution is the first release-quality backend.
- Planning intelligence is the product wedge; execution evidence makes the plan actionable.
- Every important output must be file-first, inspectable, replayable, and usable by another agent.
- Agent output may draft artifacts, but Newton must validate contracts before accepting them.
- iOS, hosted runners, direct Figma/Notion/Jira/Linear integrations, and selector self-healing are post-release tracks unless needed to explain roadmap direction.

## Dependency Map

1. Release contract and examples must be stable before expanding implementation.
2. Planning quality must improve before marketing the product as "senior-grade QA planning."
3. Web execution must become robust before adding any new execution backend.
4. Evidence, tracker, and bug-draft artifacts must close the QA loop before plugin polish.
5. Packaging, CI, docs, and release checks come after the core dogfood loop is reliable.

## Release Milestones

- **Milestone 0: Contract lock** - Decide and document the v0.1 promise, artifact versioning, and web-first boundary.
- **Milestone 1: Planning quality** - Make source extraction, estimates, risks, and review gates good enough to justify the QA-planning wedge.
- **Milestone 2: Web execution hardening** - Make Playwright runs CI-correct, diagnosable, configurable, and evidence-rich.
- **Milestone 3: QA loop closure** - Preserve per-environment tracker state and create issue-ready bug drafts from run evidence.
- **Milestone 4: Release hygiene** - Prove install, package, plugin, CI, docs, and demo flows from a clean environment.

## P0: Release Contract

### 1. Lock the v0.1 release promise

- [x] Define the exact release promise in `README.md`: "Generate a source-backed QA plan and run web smoke scenarios with evidence."
- [x] Add a short "What Newton is not yet" section: not mobile E2E, not a hosted runner, not a full test management system, not an automatic release approver.
- [x] Align `PRD.md`, `README.md`, and `docs/agent-runtime-usage.md` so the first release consistently says web-first execution.
- [x] Move cross-platform wording into roadmap language where it is not part of v0.1 behavior.

Acceptance:

- A new user can read the first screen of `README.md` and understand the web-first release value.
- No v0.1-facing doc implies production-ready iOS execution.
- `newton qa ...` remains the canonical interface for humans, agents, and CI.

Validation:

```bash
rg -n "cross-platform|iOS|mobile|web-first|hosted|self-healing" README.md PRD.md docs
```

### 2. Define the v0.1 artifact contract as a versioned contract

- [x] Add `contract_version` to planning bundle `manifest.json`.
- [x] Add `contract_version` to `result.json`.
- [x] Document v0.1 required fields for planning bundles and run results in `docs/agent-runtime-usage.md`.
- [x] Add tests that old artifacts without `contract_version` either validate with an explicit compatibility path or fail with a clear migration message.

Acceptance:

- Agents can detect which Newton artifact contract they are reading.
- CI can reject malformed artifacts with actionable errors.

Validation:

```bash
uv run --extra dev --extra web pytest tests/test_planning_bundle_validation.py tests/test_runner.py -v
```

## P0: Planning Intelligence

### 3. Replace the template bundle's shallow parser with structured source extraction

- [x] Create a small internal extraction model for source facts: feature goal, screens, user roles, states, policies, environments, dependencies, regression areas, and unknowns.
- [x] Parse common markdown sections beyond literal `Acceptance criteria`: scope, user stories, requirements, policy, design notes, risks, out of scope, environments.
- [x] Preserve source references for every extracted fact.
- [x] Render extracted facts into `qa-scope.md` and `qa-estimate.md`.
- [x] Add tests for multi-source extraction using ticket, policy, and design-note fixtures.

Acceptance:

- Template mode produces useful planning artifacts from realistic sprint notes without requiring a perfectly formatted `Acceptance criteria` section.
- Each estimate factor cites the source file or section that caused it.

Validation:

```bash
uv run --extra dev --extra web pytest tests/test_planning_bundle.py -v
newton qa plan-bundle qa/dogfood/login/inputs/ticket.md \
  --source qa/dogfood/login/inputs/policy.md \
  --source qa/dogfood/login/inputs/design-notes.md \
  --out /tmp/newton-plan-check \
  --bundle-dir-name plan
newton qa bundle-validate /tmp/newton-plan-check/plan
```

### 4. Add a transparent QA estimate scoring model

- [x] Implement a deterministic scoring table for screens, roles, states, policy rules, integrations, environments, regression risk, data setup, and retest count.
- [x] Convert score bands into size labels and time ranges.
- [x] Render a factor-by-factor table in `qa-estimate.md`.
- [x] Add tests for S, M, and L estimate outcomes.
- [x] Keep agent-backed estimates subject to the same required factor schema.

Acceptance:

- A QA lead can understand why Newton estimated the work as S, M, or L.
- The same input produces the same estimate.

Validation:

```bash
uv run --extra dev --extra web pytest tests/test_planning_bundle.py tests/test_agent_planning_bundle.py -v
```

### 5. Make risk maps source-aware and category-complete

- [ ] Keep the baseline categories: functional, edge case, network failure, permission/role, policy conflict, and regression.
- [ ] Add optional categories when source facts support them: data state, analytics/logging, localization/copy, accessibility, environment config.
- [ ] Include source references and rationale for each non-baseline risk.
- [ ] Add validation that required baseline risks remain present.

Acceptance:

- Risk map is not generic filler; at least non-baseline risks must point to concrete source facts.
- Baseline risks remain deterministic for every bundle.

Validation:

```bash
uv run --extra dev --extra web pytest tests/test_planning_bundle_validation.py tests/test_planning_bundle.py -v
```

### 6. Add planning quality evaluation

- [ ] Expand `bundle-review` into a release gate mode that scores coverage, source grounding, estimate clarity, risk usefulness, and automation suitability.
- [ ] Keep advisory review as a non-blocking mode.
- [ ] Add `newton qa bundle-review --gate` that exits non-zero under a configured score threshold.
- [ ] Add a dogfood review artifact for the login example.

Acceptance:

- Newton can tell a user when a generated QA plan is structurally valid but not release-quality.
- CI can run a planning-quality gate without relying on subjective manual review.

Validation:

```bash
uv run --extra dev --extra web pytest tests/test_bundle_review.py -v
```

## P0: Web-First Execution

### 7. Make web runs CI-correct

- [x] Change `newton qa run` so failed scenario runs exit non-zero by default.
- [x] Add `--allow-failure` for dogfood and diagnostic workflows that intentionally capture a failing run.
- [x] Ensure `result.json`, `qa-report.md`, and `index.jsonl` are still written before the CLI exits non-zero.
- [x] Add CLI tests for passed run exit `0`, failed run exit non-zero, and failed run with `--allow-failure` exit `0`.
- [x] Document how CI should call `newton qa run` for release gates.

Acceptance:

- CI can use Newton as a real gate instead of parsing `status: failed` from stdout.
- Intentional negative demos can still preserve failing evidence without breaking the demo script.

Validation:

```bash
uv run --extra dev --extra web pytest tests/test_cli.py tests/test_runner.py -v
```

### 8. Normalize Playwright setup and preflight failures

- [x] Add a `newton qa doctor web` command that checks Playwright import, Chromium browser availability, and basic headless launch.
- [x] Normalize missing browser binaries, launch failure, missing OS dependencies, and unreachable base URL into Newton-style setup results.
- [x] Ensure setup/preflight failures produce `result.json` and `qa-report.md` when they occur during `newton qa run`.
- [x] Return clear remediation commands when Playwright or Chromium is missing.
- [x] Add tests for doctor success, doctor failure messages, and run-time setup failure artifacts.

Acceptance:

- A new user can diagnose web execution setup without reading stack traces.
- Installer, docs, doctor command, and run failure reports agree on setup commands.

Validation:

```bash
uv run --extra dev --extra web pytest tests/test_cli.py tests/test_web_playwright.py -v
newton qa doctor web
```

### 9. Tighten web scenario validation before execution

- [ ] Add a scenario schema or contract version field for web scenarios.
- [ ] Validate supported web actions before execution instead of discovering unsupported actions mid-run.
- [ ] Validate selector payloads for supported selector families before execution.
- [ ] Include step id, action, and selector payload in validation errors.
- [ ] Add early validation for target/backend compatibility, required base URL, and invalid timeout values.
- [ ] Add tests that invalid web actions and invalid selectors fail at `newton qa validate`.

Acceptance:

- Scenario authors get deterministic validation errors before running a browser.
- CI failures distinguish invalid scenarios from product behavior failures.

Validation:

```bash
uv run --extra dev --extra web pytest tests/test_models.py tests/test_scenario_loader.py tests/test_cli.py -v
```

### 10. Harden selector and action coverage for real web smoke tests

- [ ] Support common selector forms needed for release demos: role/name, test id, text, css, label, placeholder, alt text, and title.
- [ ] Support minimal release actions: navigate, click/tap, fill/input text, checkbox, select option, keyboard press, file upload, and explicit wait.
- [ ] Support assertion actions for URL, URL pattern, text, visibility, hidden/not visible, enabled/disabled state, and value.
- [ ] Add explicit unsupported-selector errors that include the step id and selector payload.
- [ ] Add tests for every selector and action form.

Acceptance:

- Newton can run stable smoke scenarios against common React/Next/SaaS UI patterns.
- Scenario authors get clear errors instead of Playwright internals.

Validation:

```bash
uv run --extra dev --extra web pytest tests/test_web_playwright.py -v
```

### 11. Add web run configuration for production-like environments

- [ ] Add scenario or CLI support for headless mode, browser channel, viewport, locale, timezone, permissions, storage state path, extra headers, and retries.
- [ ] Map `ScenarioTarget.device` or a dedicated web runtime config into Playwright context settings.
- [ ] Redact secure step values in reports and result JSON.
- [ ] Add timeout defaults and per-step override documentation.
- [ ] Add tests proving config is applied and secrets are not emitted.

Acceptance:

- A team can run the same scenario against local, preview, staging, and production-like environments.
- Sensitive login inputs do not leak into reports.

Validation:

```bash
uv run --extra dev --extra web pytest tests/test_runner.py tests/test_reporting.py tests/test_web_playwright.py -v
```

### 12. Make the evidence contract truthful and release-grade

- [ ] Always write a compact run summary into `result.json`.
- [ ] Store screenshots and traces with relative paths.
- [ ] Either implement `video`, `logs`, and `screenshots: after_each_step` artifacts or remove those release-facing claims until implemented.
- [ ] Attach video artifacts to `result.json` and `qa-report.md` if video capture remains enabled.
- [ ] Add optional HTML report export or richer markdown sections for failure diagnosis.
- [ ] Capture console errors and failed network requests when enabled.
- [ ] Add tests for evidence paths, console/network evidence, video handling if enabled, after-each-step screenshots if enabled, and report rendering.

Acceptance:

- A failed web run gives a developer enough context to reproduce or inspect the failure without rerunning immediately.
- Evidence paths are portable inside the run directory.
- The public evidence policy does not promise artifacts Newton does not actually attach.

Validation:

```bash
uv run --extra dev --extra web pytest tests/test_reporting.py tests/test_web_playwright.py tests/test_dogfood.py -v
```

### 13. Add a one-command web dogfood release demo

- [ ] Replace or supplement the static login fixture with a small realistic web app fixture containing success, validation, network-delay, and permission-denied states.
- [ ] Add at least three web scenarios: happy path, validation failure, and permission or policy conflict.
- [ ] Add `scripts/demo-web-release.sh` that starts and stops local fixture servers, generates fresh artifacts, and prints output paths.
- [ ] Remove manual README steps that require a separate `cp` or hard-coded committed run id.
- [ ] Commit representative passing and failing run artifacts that demonstrate screenshot and trace evidence.
- [ ] Document the dogfood flow as the release demo.

Acceptance:

- The release demo shows more than a toy login success/failure.
- Planning artifacts, scenarios, run results, tracker updates, and bug drafts all connect.
- A reviewer can run one command and see the Newton web-first value loop.

Validation:

```bash
uv run --extra dev --extra web pytest tests/test_dogfood.py tests/test_web_playwright.py -v
bash scripts/demo-web-release.sh
```

## P0: QA Loop Closure

### 14. Strengthen tracker updates

- [ ] Track each checklist item across dev, stg, and prod rather than storing only one current environment per item.
- [ ] Preserve historical run links per environment.
- [ ] Support manual status updates and run-derived updates with the same output shape.
- [ ] Add validation for tracker consistency with checklist and test cases.

Acceptance:

- QA can see what passed in dev, what failed in staging, and what remains unverified in production.
- A run update does not erase useful previous environment state.

Validation:

```bash
uv run --extra dev --extra web pytest tests/test_tracker_update.py tests/test_planning_bundle_validation.py -v
```

### 15. Make bug drafts issue-tracker ready

- [ ] Include title, severity, priority, environment, failed step, reproduction steps, expected result, actual result, source references, evidence paths, and suspected owner/area.
- [ ] Use run evidence when `tracker-update-from-run` created the failure.
- [ ] Add `--format markdown|linear|jira` if the field mapping can stay file-first.
- [ ] Add tests for manual failure and run-derived failure drafts.

Acceptance:

- A QA engineer can paste the generated draft into a tracker with minimal editing.
- A developer can find the evidence artifact paths directly from the draft.

Validation:

```bash
uv run --extra dev --extra web pytest tests/test_bug_draft.py tests/test_tracker_update.py -v
```

## P1: Agent and Plugin Surface

### 16. Make natural-language QA routing reliable

- [x] Update `plugins/newton/skills/newton-qa-workflow/SKILL.md` so web-first execution is explicit.
- [x] Add examples for: planning only, scenario generation, web run, tracker update, and bug draft.
- [x] Add a final-response checklist for artifacts, commands run, evidence paths, and remaining risk.
- [x] Add tests that plugin command docs and skill text mention release-quality web flow.

Acceptance:

- A Claude Code user can ask for QA planning or web execution without knowing Newton commands.
- The skill does not imply mobile execution is release-ready.

Validation:

```bash
claude plugin validate plugins/newton
uv run --extra dev --extra web pytest tests/test_claude_plugin.py -v
```

### 17. Add agent handoff packets

- [ ] Add a `newton qa handoff` command that prints or writes a compact artifact summary for another agent.
- [ ] Include bundle path, scenario path, run id, report path, evidence paths, tracker path, and bug draft path when available.
- [ ] Add tests using existing dogfood artifacts.

Acceptance:

- Another agent can continue a QA workflow without scanning the whole repository.
- The handoff packet is deterministic and file-first.

Validation:

```bash
uv run --extra dev --extra web pytest tests/test_cli.py tests/test_dogfood.py -v
```

## P1: Packaging, CI, and Release Hygiene

### 18. Add release build validation

- [x] Add a CI job that builds sdist and wheel.
- [x] Install the built wheel in a clean environment.
- [x] Run `newton version`, `newton qa validate`, `newton qa bundle-validate`, and a dry-run scenario from the installed wheel.
- [x] Keep Playwright browser install in a separate CI step.

Acceptance:

- The package users install is the package CI tested.
- CLI entry point works outside editable install mode.

Validation:

```bash
uv build
python -m pip install --force-reinstall dist/newton_qa-0.1.0-py3-none-any.whl
newton version
```

### 19. Version and changelog discipline

- [ ] Add `CHANGELOG.md` with an initial v0.1.0 section.
- [ ] Decide whether version lives only in `src/newton/__init__.py` or is derived from package metadata.
- [ ] Add a test that CLI `newton version` matches `pyproject.toml`.
- [ ] Add release checklist commands to `README.md`.

Acceptance:

- Release notes and installed version cannot drift silently.

Validation:

```bash
uv run --extra dev --extra web pytest tests/test_cli.py -v
```

### 20. Harden installer verification

- [ ] Add installer dry-run CI coverage for `uv`, `pipx`, `--no-web`, `--ref`, and `--repo`.
- [ ] Document how to install a tagged release.
- [ ] Add a post-install smoke path that does not require repository fixtures.
- [ ] Avoid assuming users run installer from the Newton checkout.

Acceptance:

- One-line install works for a user who has never cloned Newton.
- The installer gives actionable failures when `uv`, `pipx`, Python, or Playwright setup is missing.

Validation:

```bash
uv run --extra dev --extra web pytest tests/test_install_script.py -v
NEWTON_INSTALL_DRY_RUN=1 bash scripts/install.sh --no-web --ref v0.1.0
```

### 21. Split fast and browser CI

- [ ] Keep unit and contract tests fast.
- [ ] Run Playwright integration tests in a browser job.
- [ ] Make the browser job required for release branches and tags.
- [ ] Upload failing Playwright traces and screenshots as CI artifacts.
- [ ] Add branch protection expectation in docs.

Acceptance:

- Contributors get fast feedback, while release CI still proves browser execution.

Validation:

```bash
uv run --extra dev pytest -v
uv run --extra dev --extra web pytest tests/test_web_playwright.py tests/test_dogfood.py -v
```

## P1: Documentation and Examples

### 22. Rewrite README around the release demo

- [ ] Start with install, first QA plan, first web run, and first failure evidence.
- [ ] Keep advanced agent-backed and plugin sections after the main flow.
- [ ] Include expected output snippets for each command.
- [ ] Explain where artifacts are written and how to inspect them.

Acceptance:

- A user can complete the release demo in under ten minutes from the README alone.

Validation:

```bash
rg -n "newton qa plan-bundle|newton qa run|qa-report.md|playwright-trace.zip" README.md
```

### 23. Add troubleshooting docs

- [ ] Document Playwright browser install failures.
- [ ] Document common scenario validation failures.
- [ ] Document selector failures and how to inspect traces.
- [ ] Document agent command failures for Codex and Claude.

Acceptance:

- Common release-demo failures have first-party remediation steps.

Validation:

```bash
rg -n "Playwright|selector|trace|Codex|Claude|validation" docs README.md
```

## P1: Security, Privacy, and Trust

### 24. Redact sensitive values

- [ ] Ensure `secure: true` input values are not written to `result.json`, `qa-report.md`, traces under Newton control, handoff packets, or bug drafts.
- [ ] Add explicit docs for what Newton can and cannot redact from third-party Playwright traces.
- [ ] Add tests for secure step rendering.

Acceptance:

- Users can safely run login scenarios without Newton leaking test credentials in its own artifacts.

Validation:

```bash
uv run --extra dev --extra web pytest tests/test_reporting.py tests/test_web_playwright.py tests/test_bug_draft.py -v
```

### 25. Make external agent execution visibly bounded

- [ ] Document that template mode is deterministic and does not call external agents.
- [ ] Keep Codex/Claude generation prompts and raw outputs saved for audit.
- [ ] Add warnings when `--agent-command` overrides safe defaults.
- [ ] Add tests for command override provenance.

Acceptance:

- Users can choose deterministic local mode or audited agent-backed mode knowingly.

Validation:

```bash
uv run --extra dev --extra web pytest tests/test_agent_planner.py tests/test_agent_planning_bundle.py tests/test_bundle_review.py -v
```

## P2: Post-Release Tracks

### 26. iOS execution track

- [ ] Keep Maestro compile support as experimental until a real device/simulator run is implemented.
- [ ] Add an explicit `experimental` label in docs and output.
- [ ] Later, add simulator lifecycle, app install, Maestro execution, logs, screenshots, and artifact normalization.

Acceptance:

- Users do not confuse Maestro YAML compilation with production-ready iOS execution.

### 27. Tool integration track

- [ ] Add importers only after file-first planning quality is strong.
- [ ] Start with export/paste workflows for Figma, Notion, Jira, Linear, and GitHub PR diffs.
- [ ] Keep every importer writing plain files under `qa/inputs/`.

Acceptance:

- Integrations enrich the same contract instead of creating separate workflows.

### 28. Hosted runner track

- [ ] Design hosted or remote execution only after local web execution is release-grade.
- [ ] Define artifact upload, trace retention, secrets handling, and PR comment behavior before implementation.

Acceptance:

- Hosted execution does not become a second product before the local CLI loop is trusted.

### 29. Selector self-healing track

- [ ] Add selector diagnostics before automatic repair.
- [ ] Require human-reviewed scenario updates.
- [ ] Store suggested selector replacements as reviewable artifacts.

Acceptance:

- Self-healing improves maintainability without hiding broken product behavior.

## Release Gates

- [ ] `uv run --extra dev --extra web pytest` passes.
- [ ] `claude plugin validate .claude-plugin/marketplace.json` passes.
- [ ] `claude plugin validate plugins/newton` passes.
- [ ] `uv build` produces wheel and sdist.
- [ ] Built wheel installs in a clean environment and `newton version` works.
- [ ] Web dogfood demo produces planning bundle, scenario, passing run, failing run, screenshot, trace, tracker update, and bug draft.
- [ ] README first-run instructions are verified from a clean checkout.
- [ ] Release notes describe exactly what is release-quality and what is experimental.

## Scope Traps To Avoid

- Do not build mobile execution before web execution is release-grade.
- Do not build hosted runners before local artifact contracts are stable.
- Do not market template planning as senior-grade until extraction, estimate scoring, and review gates improve.
- Do not add direct Figma/Notion/Jira/Linear OAuth before file-first imports and planning quality work.
- Do not add selector self-healing before selector diagnostics and evidence reporting are strong.
- Do not create a separate plugin workflow that bypasses `newton qa ...`.
