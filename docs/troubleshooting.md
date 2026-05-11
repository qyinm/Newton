# Troubleshooting

Use this when the release demo or a local web run fails before a product bug is clear.

## Playwright Browser Setup

Run the doctor first:

```bash
newton qa doctor web
```

Common fixes:

- Missing Playwright package: `python -m pip install -e '.[web]'`
- Missing Chromium browser: `python -m playwright install chromium`
- Missing host dependencies: `python -m playwright install --with-deps chromium`
- Unreachable app URL: rerun `newton qa run` with the intended `--base-url`

When setup fails during `newton qa run`, Newton still writes `result.json` and `qa-report.md` under the run directory.

## Scenario Validation

Validate before opening a browser:

```bash
newton qa validate qa/dogfood/login/scenario/login-smoke.generated.yaml
```

Validation failures usually mean one of these:

- Unsupported web action: replace it with a documented action from `docs/scenario-schema.md`.
- Unsupported selector payload: use one selector family per step, such as `role/name`, `test_id`, `text`, `css`, `label`, `placeholder`, `alt_text`, or `title`.
- Missing web target `base_url`: set `targets[].base_url` or pass `--base-url` at run time.
- Backend mismatch: `playwright` is web-only in v0.1.
- Invalid timeout: `timeout_ms` must be greater than zero.

Newton includes the step id, action, and selector payload in validation errors so the scenario can be fixed without rerunning Playwright.

## Selector Failures And Traces

When a browser run fails, start with the generated report:

```bash
cat qa/dogfood/login/runs/<run-id>/qa-report.md
```

Then inspect evidence:

```bash
open qa/dogfood/login/runs/<run-id>/failure-step-*.png
python -m playwright show-trace qa/dogfood/login/runs/<run-id>/playwright-trace.zip
```

Prefer stable selectors in this order: `role/name`, `test_id`, label or placeholder, visible text, then CSS. If Playwright reports a strict-mode violation, the selector matched more than one element; narrow the selector before treating the result as a product bug.

Playwright trace and video files are third-party artifacts. Newton redacts values in its own `result.json`, `qa-report.md`, handoff packets, and bug drafts, but traces and videos may still contain browser-level input events, DOM snapshots, screenshots, network payloads, or storage state.

## Codex And Claude Agent Commands

Template mode is deterministic local code and does not call external agents. Use it first when debugging:

```bash
newton qa plan-bundle qa/dogfood/login/inputs/ticket.md --agent template --out qa/dogfood/login --bundle-dir-name plan
newton qa plan qa/dogfood/login/inputs/ticket.md --agent template --target web --out qa/dogfood/login/scenario
```

For Codex or Claude failures:

- Confirm the CLI exists on `PATH` and is authenticated.
- Read the saved prompt and raw output next to the generated artifact.
- Use `newton qa bundle-validate` or `newton qa validate` on accepted artifacts.
- Treat `--agent-command` as an explicit override of Newton's safer defaults; Newton prints a warning and records override provenance.

Useful audit files:

```text
bundle-generation.codex.prompt.txt
bundle-generation.codex.raw.txt
bundle-review.codex.prompt.txt
bundle-review.codex.raw.txt
login_ticket.codex.prompt.txt
login_ticket.codex.raw.txt
```
