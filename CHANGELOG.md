# Changelog

All notable changes to Newton are tracked here.

## Unreleased

### Added

- Planning benchmark evaluation through `newton qa eval-planning`, with JSON and Markdown reports for source-backed QA planning quality checks.

## v0.1.0

Initial web-first release baseline.

### Added

- Source-backed QA planning bundle generation from sprint context.
- Web scenario validation and dry-run execution through the `newton qa` CLI.
- Playwright web smoke execution with run reports, screenshots, and traces.
- Tracker update and bug draft helpers for the file-first QA loop.
- Official installer path with `uv` first and `pipx` fallback.

### Release-quality in v0.1.0

- File-first QA planning from markdown sprint context using the deterministic template agent or audited Codex/Claude agent runs.
- Web smoke scenario validation and Playwright execution through `newton qa`.
- Evidence artifacts for web runs: `result.json`, `qa-report.md`, screenshots, traces, console and network diagnostics, tracker updates, bug drafts, and agent handoff packets.
- CLI, Claude Code plugin, package build, installer dry-run, and one-command web dogfood demo flows.

### Experimental or post-release

- iOS/Maestro support is compile-only roadmap work, not release-quality mobile E2E.
- Hosted runners, direct OAuth integrations, automatic release approval, and selector self-healing are not part of v0.1.0.
- Third-party Playwright trace internals may include browser-controlled data that Newton cannot redact; Newton redacts sensitive values only in artifacts it renders.
