# Post-Release Tracks

Newton v0.1 stays web-first. These tracks describe what comes after the local web QA loop is release-grade.

## iOS Execution Track

The current Maestro support is experimental. Newton may compile iOS bindings into Maestro YAML, but that is not a production-ready device or simulator execution backend.

Before calling iOS execution release-quality, Newton needs:

- simulator lifecycle management
- app install and launch
- Maestro execution
- logs, screenshots, and normalized artifacts
- failure reporting consistent with web runs

## Tool Integration Track

Direct integrations should wait until file-first planning quality is strong. The first integration surface should be export or paste workflows for Figma, Notion, Jira, Linear, and GitHub PR diffs.

Every importer must write plain files under `qa/inputs/` so the rest of the planning contract remains unchanged.

## Hosted Runner Track

Hosted or remote execution should wait until local web execution is trusted. Before implementation, the design must define artifact upload, trace retention, secrets handling, and PR comment behavior.

## Selector Self-Healing Track

Selector self-healing should begin with diagnostics, not automatic mutation. Newton should first store suggested selector replacements as reviewable artifacts, and scenario updates must remain human-reviewed.
