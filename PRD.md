# PRD: Sprint QA Copilot

## 1. Summary

Sprint QA Copilot, implemented as **Newton**, is an **agent-native, web-first QA harness** for product teams.

The v0.1 release promise is: **Generate a source-backed QA plan and run web smoke scenarios with evidence.**

Newton is designed to run on top of coding agents such as **Claude Code**, **Codex CLI**, and **Hermes Agent**, while also remaining usable from a plain terminal or CI job. Instead of relying on one-off prompting, Newton gives those agents a replayable QA contract: structured inputs, explicit commands, normalized run artifacts, and evidence-backed outputs.

It helps QA engineers turn upcoming sprint context into defensible QA estimates, test cases, checklists, risk maps, web smoke scenarios, and bug ticket drafts. The first version does not try to replace human QA judgment. It helps QA know what to test, why it matters, how long it should take, what risks may be missed, and how to execute deterministic web checks when the scenario is stable enough.

The product starts from a real QA workflow:

- QA joins design reviews before the sprint starts.
- QA estimates the testing schedule from incomplete feature scope.
- QA reads Figma UI, annotations, Notion policy docs, and issue tickets.
- QA writes test cases or checklists.
- Developers deploy features to dev, then staging, then production.
- QA runs tests manually, files bugs, suggests improvements, and flags policy conflicts.
- QA resources are always short, especially around E2E testing and repeated regression work.

The initial product wedge is:

> Help a junior or mid-level QA engineer produce a senior-grade QA plan from Figma, policy docs, and sprint tickets.

And the system-level product framing is:

> Give AI coding agents a file-first QA harness they can call to validate product behavior, generate QA artifacts, and return evidence-backed reports.

## 2. Problem

QA teams are asked to estimate and execute testing before product scope is fully stable.

In practice, QA engineers must infer upcoming functionality from design reviews, Figma annotations, Notion policy docs, Jira or Linear tickets, and conversations with PM/design/dev. This creates several recurring problems:

- QA estimates are not trusted or not followed.
- Test cases focus on visible UI and happy-path behavior.
- Edge cases, network failures, permission states, policy conflicts, and regression areas are missed.
- QA spends too much time converting scattered context into test cases.
- Bug reports repeat manual formatting work.
- Test automation comes too late because the team does not first know which flows are worth automating.

The pain is strongest for junior QA engineers and overloaded QA teams.

## 3. Target Users

### Primary User

Junior to mid-level QA engineer on a product team.

They participate in design reviews, estimate QA effort, write test cases/checklists, run dev/stg/prod testing, and file bugs.

### Secondary Users

- QA lead who reviews QA scope and estimates.
- PM who wants release risk visibility.
- Developer who wants reproducible bug reports.
- Automation QA engineer who wants to identify high-value automation candidates.

## 4. User Jobs

### Job 1: Estimate QA Effort

As a QA engineer, I want to estimate QA time from feature scope so that I can explain why a sprint needs 3 days, 5 days, or more for QA.

### Job 2: Generate Test Scope

As a QA engineer, I want to turn Figma, annotations, policy docs, and tickets into test cases/checklists so that I do not miss important behavior.

### Job 3: Find Missing Risks

As a junior QA engineer, I want the system to suggest edge cases, network cases, permission cases, regression areas, and policy inconsistencies so that I can test closer to a senior QA level.

### Job 4: Track Environment Testing

As a QA engineer, I want dev, staging, and production test progress separated so that I can see what passed where and what still needs verification.

### Job 5: Draft Bug Tickets

As a QA engineer, I want failed checks to become clean bug ticket drafts with reproduction steps, expected behavior, actual behavior, evidence, severity, and environment.

## 5. Non-Goals

The first version will not:

- Fully automate mobile E2E execution.
- Self-heal selectors.
- Control iOS Simulator or Android Emulator.
- Replace Maestro, Playwright, XCTest, or Appium.
- Guarantee QA schedule accuracy.
- Automatically approve releases.
- Replace human QA judgment.
- Depend on a single agent runtime or chat product.
- Hide QA execution behind opaque prompt-only behavior.

Those are later layers. The first product is the web-first QA planning and execution loop, not a general-purpose execution runner.

Newton should be agent-native, but not agent-dependent: the same artifacts and commands should work whether the caller is Hermes, Claude Code, Codex, or a human in the terminal.

## 6. Product Principles

### CLI-first and artifact-first

The system should produce files that humans and agents can inspect:

- `qa-plan.md`
- `test-cases.csv`
- `checklist.md`
- `risk-map.md`
- `bug-ticket.md`
- `automation-candidates.md`

### Evidence over vibes

Every QA estimate should cite concrete evidence:

- number of screens
- number of policy rules
- number of affected user roles
- number of state combinations
- affected environments
- integration points
- regression areas

### Manual-first, automation-second

The product should first make manual QA better. Automation should come from repeated, stable, high-value checks.

### Agent-assisted, deterministic where it matters

The agent can draft, classify, and suggest. Final QA scope, severity, and release sign-off remain human-reviewed.

## 7. MVP Scope

The v0.1 MVP locks one release-quality loop: generate a source-backed QA plan, create a web smoke scenario, run it locally or against staging, and preserve evidence that another human or agent can inspect.

### MVP 1: Web-First QA Planning and Execution

This is the first release priority.

Newton must accept product or ticket context, produce source-backed QA planning artifacts, accept structured scenario input, validate it, run deterministic web checks where possible, and persist normalized artifacts that any agent can inspect or replay.

Required outputs for MVP 1:

- `qa-scope.md`
- `qa-estimate.md`
- `checklist.md`
- `test-cases.csv`
- `qa/runs/<run_id>/result.json`
- `qa/runs/<run_id>/qa-report.md`
- evidence files when available

Required commands for MVP 1:

- `newton qa plan-bundle`
- `newton qa bundle-validate`
- `newton qa plan`
- `newton qa validate`
- `newton qa run`
- `newton qa report`

Release-quality execution target for MVP 1:

- web smoke scenarios through Playwright

Primary runtime targets for MVP 1:

- plain terminal
- CI job
- Claude Code
- Codex CLI
- Hermes Agent

### MVP 2: Broader QA Planning Intelligence

After the v0.1 loop is stable, Newton expands planning quality, source extraction depth, review gates, bug-draft workflows, and automation candidate generation.

### 7.1 Input Collection

MVP supports manual input through files and pasted text.

Inputs:

- sprint description
- feature ticket text
- Figma screen notes or exported design text
- Notion policy docs or copied policy sections
- known regression areas
- environment list: dev, stg, prod

Out of scope for MVP:

- direct Figma OAuth integration
- direct Notion OAuth integration
- Jira/Linear API integration
- automatic PR diff analysis

### 7.2 Scope Digest

The system generates a concise feature summary:

- feature name
- user-facing behavior
- affected screens
- affected roles
- affected policies
- dependencies
- unknowns

Output: `qa-scope.md`

### 7.3 QA Estimate

The system estimates QA effort using a visible scoring model.

Estimate factors:

- screen count
- state count
- policy complexity
- role/permission complexity
- integration complexity
- environment coverage
- regression risk
- data setup complexity
- expected retest count

Output:

```text
Estimated QA effort: 5 days

Reasoning:
- 12 affected screens
- 3 user roles
- 4 policy rules
- dev/stg/prod verification required
- payment and notification regression risk
- at least 2 retest cycles expected
```

Output: `qa-estimate.md`

### 7.4 Test Case and Checklist Generation

The system generates both structured test cases and a lightweight checklist.

Test case fields:

- ID
- title
- priority
- precondition
- steps
- expected result
- environment
- risk category
- source reference

Checklist sections:

- UI checks
- functional checks
- policy checks
- edge cases
- network cases
- permission/role cases
- regression checks
- analytics/logging checks, optional
- release checks

Outputs:

- `test-cases.csv`
- `checklist.md`

### 7.5 Risk Map

The system highlights likely missed areas.

Risk categories:

- edge case
- network failure
- permission/role
- policy conflict
- data state
- cross-environment config
- regression
- localization/copy
- accessibility
- analytics/event tracking

Output: `risk-map.md`

### 7.6 Environment Run Tracker

The system creates a dev/stg/prod tracking template.

Each test can be marked:

- not run
- pass
- fail
- blocked
- needs retest

Output: `qa-run-tracker.md`

### 7.7 Bug Ticket Draft

For failed checklist items, the system drafts a bug ticket.

Fields:

- title
- environment
- build/version
- severity
- priority
- reproduction steps
- expected result
- actual result
- evidence links
- suspected area
- related policy/design reference

Output: `bug-ticket-draft.md`

### 7.8 Automation Candidate Report

The system identifies which checks are good candidates for automation.

Criteria:

- repeated across releases
- stable selector/UI
- high business value
- easy setup
- clear expected result
- low flakiness risk

Output: `automation-candidates.md`

## 8. Example Workflow

```text
1. QA attends design review.
2. QA exports or pastes Figma annotations and policy docs.
3. QA runs Sprint QA Copilot.
4. System generates:
   - scope digest
   - QA estimate
   - risk map
   - TC/checklist
   - dev/stg/prod tracker
5. QA reviews and edits the plan.
6. Developers deploy to dev.
7. QA runs checklist and marks results.
8. Failed checks become bug ticket drafts.
9. Repeated stable checks become automation candidates.
```

## 9. CLI Concept

```bash
newton qa validate qa/scenarios/login.yaml
newton qa run qa/scenarios/login.yaml --backend web
newton qa report qa/runs/latest

# planning layer
newton qa ingest ./qa/inputs/
newton qa plan --sprint 1.21
newton qa estimate --plan latest
newton qa generate-tests --plan latest
newton qa risk-map --plan latest
newton qa run-tracker --env dev,stg,prod
newton qa bug-draft --from failed-check.md
newton qa automation-candidates --from checklist.md
```

The command surface should remain stable across agent runtimes so a Claude Code task, a Codex workflow, a Hermes skill, and a CI job can all invoke the same Newton contract.

## 10. Output Directory

```text
qa/
  inputs/
    sprint.md
    figma-notes.md
    policy.md
    tickets.md
  plans/
    2026-05-05-sprint-1.21/
      qa-scope.md
      qa-estimate.md
      risk-map.md
      checklist.md
      test-cases.csv
      qa-run-tracker.md
      automation-candidates.md
      bug-ticket-draft.md
      manifest.json
```

## 11. Success Metrics

### User Value Metrics

- Time to first QA plan under 10 minutes.
- QA estimate includes explicit supporting evidence.
- QA engineer accepts at least 70% of generated checklist items after editing.
- User reports at least 3 useful missed-risk suggestions per feature.
- Bug ticket draft requires less than 2 minutes of editing.

### Product Quality Metrics

- Generated test cases cite their source context.
- No uncited high-confidence claims.
- Risk suggestions are categorized.
- Estimates are deterministic for the same input.
- Outputs can be edited as plain files.

## 12. MVP Acceptance Criteria

The MVP is acceptable when a user can:

1. Validate a Newton scenario file from the terminal.
2. Run a deterministic QA scenario against a supported backend.
3. Persist `result.json` and `qa-report.md` under `qa/runs/<run_id>/`.
4. Produce evidence artifacts when the backend supports them.
5. Re-run the same scenario through the same command contract from a coding agent or CI job.
6. Add sprint/ticket/design/policy text into `qa/inputs/`.
7. Generate a QA scope summary.
8. Generate a QA estimate with evidence.
9. Generate test cases and a checklist.
10. Generate a risk map that includes edge, network, permission, policy, and regression risks.
11. Track dev/stg/prod testing status.
12. Draft a bug ticket from a failed checklist item.
13. Identify automation candidates.

## 13. Future Roadmap

### V1: QA Planning Assistant

- File-based input
- QA estimate
- TC/checklist generation
- risk map
- bug ticket draft
- automation candidate report

### V2: Tool Integrations

- Figma integration
- Notion integration
- Jira/Linear integration
- GitHub PR diff integration
- Slack summary ingestion

### V3: Broader Execution Harness

- deeper Playwright web runner coverage
- experimental Maestro runner
- simulator/device run logs
- screenshot/video evidence
- JUnit export
- dev/stg/prod run comparison

### V4: Remote Runner

- static macOS host
- Crabbox-like remote execution
- warm macOS runner lease
- artifact collection
- PR comments

### V5: Assisted Self-Healing

- selector registry
- runtime UI tree comparison
- replacement candidate suggestions
- rerun validation
- human-reviewed canonical flow updates

## 14. Open Questions

- Which post-v0.1 mobile QA path should be explored first: Maestro compile artifacts, simulator execution, or another adapter?
- Should the primary output be test cases, checklist, or QA estimate?
- Which tool matters first: Figma, Notion, Jira/Linear, or GitHub?
- Should the first product be CLI-only or include a local web UI?
- How much estimation logic should be rule-based versus model-generated?
- What format do QA engineers already use for TC/checklist in the target team?
- What bug tracker fields are mandatory in the target workflow?

## 15. Recommended First Build

Build the file-based CLI and web-first executable harness first.

The first demo should show Newton working as a QA harness that can be called from a terminal or an agent runtime.

The first demo should take one real sprint feature or stable smoke flow and produce:

- source-backed QA planning artifacts
- validated scenario input
- `qa/runs/<run_id>/result.json`
- `qa/runs/<run_id>/qa-report.md`
- evidence artifacts when available

Then the planning layer should produce:

- `qa-scope.md`
- `qa-estimate.md`
- `risk-map.md`
- `checklist.md`
- `test-cases.csv`
- `bug-ticket-draft.md`

Do not start with full E2E automation or a hosted platform. The first value is a replayable agent-native QA harness that generates source-backed plans and runs web smoke scenarios with deterministic evidence; broader execution targets remain roadmap work.
