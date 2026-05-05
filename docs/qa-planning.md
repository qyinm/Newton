# QA Planning

`newton qa plan` is Newton's first planning-layer command. It converts markdown product or ticket context into a deterministic, validated Newton scenario YAML draft.

## MVP scope

The current planner is intentionally deterministic and template-based. It does not call an LLM yet.

Supported flow:

- login smoke test
- web target
- optional web+iOS cross-platform target

Input requirements:

- markdown file
- first heading becomes the scenario title
- generated scenario is self-validated before the command succeeds

## Usage

```bash
newton qa plan qa/inputs/login-ticket.md --target web --out qa/scenarios
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
- issue/PRD ingestion
- LLM-assisted scenario proposals
- selector mapping from design systems or product metadata
