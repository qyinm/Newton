from pathlib import Path
import json

from typer.testing import CliRunner

from newton.cli import app


def test_version_command_prints_version():
    result = CliRunner().invoke(app, ["version"])

    assert result.exit_code == 0
    assert result.stdout.strip() == "0.1.0"


def test_qa_validate_accepts_valid_scenario():
    result = CliRunner().invoke(
        app,
        ["qa", "validate", "tests/fixtures/scenarios/web_login.yaml"],
    )

    assert result.exit_code == 0
    assert "valid: web-login-smoke" in result.stdout


def test_qa_run_dry_run_writes_artifacts(tmp_path: Path):
    result = CliRunner().invoke(
        app,
        [
            "qa",
            "run",
            "tests/fixtures/scenarios/web_login.yaml",
            "--target",
            "web",
            "--backend",
            "dry-run",
            "--out",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "run:" in result.stdout
    assert list(tmp_path.glob("run_*/result.json"))
    assert list(tmp_path.glob("run_*/qa-report.md"))


def test_qa_run_accepts_base_url_option(tmp_path: Path):
    result = CliRunner().invoke(
        app,
        [
            "qa",
            "run",
            "tests/fixtures/scenarios/web_login.yaml",
            "--target",
            "web",
            "--backend",
            "dry-run",
            "--base-url",
            "http://127.0.0.1:7777",
            "--out",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "status: passed" in result.stdout


def test_qa_run_accepts_plan_provenance_option(tmp_path: Path):
    provenance_path = tmp_path / "login_ticket.template.plan.json"
    provenance_path.write_text(
        json.dumps(
            {
                "agent": "template",
                "input_path": "tests/fixtures/inputs/login_ticket.md",
                "target": "web",
                "base_url": "http://127.0.0.1:8000",
                "prompt_path": None,
                "raw_output_path": None,
                "accepted_scenario_path": "tests/fixtures/scenarios/web_login.yaml",
                "validation_status": "accepted",
                "validation_error": None,
            }
        )
    )

    result = CliRunner().invoke(
        app,
        [
            "qa",
            "run",
            "tests/fixtures/scenarios/web_login.yaml",
            "--target",
            "web",
            "--backend",
            "dry-run",
            "--plan-provenance",
            str(provenance_path),
            "--out",
            str(tmp_path / "runs"),
        ],
    )

    assert result.exit_code == 0
    result_paths = list((tmp_path / "runs").glob("run_*/result.json"))
    assert result_paths
    payload = json.loads(result_paths[0].read_text())
    assert payload["planning"]["provenance_path"] == str(provenance_path)
    assert payload["planning"]["agent"] == "template"
    index_entries = [json.loads(line) for line in (tmp_path / "runs" / "index.jsonl").read_text().splitlines()]
    assert index_entries[0]["planning_provenance_path"] == str(provenance_path)


def test_qa_runs_lists_local_run_index(tmp_path: Path):
    first = CliRunner().invoke(
        app,
        [
            "qa",
            "run",
            "tests/fixtures/scenarios/web_login.yaml",
            "--target",
            "web",
            "--backend",
            "dry-run",
            "--out",
            str(tmp_path / "runs"),
        ],
    )
    second = CliRunner().invoke(
        app,
        [
            "qa",
            "run",
            "tests/fixtures/scenarios/web_login.yaml",
            "--target",
            "web",
            "--backend",
            "dry-run",
            "--out",
            str(tmp_path / "runs"),
        ],
    )
    assert first.exit_code == 0
    assert second.exit_code == 0

    result = CliRunner().invoke(app, ["qa", "runs", "--out", str(tmp_path / "runs")])

    assert result.exit_code == 0
    lines = result.stdout.strip().splitlines()
    assert len(lines) == 2
    for line in lines:
        assert "passed" in line
        assert "web-login-smoke" in line
        assert "web" in line


def test_qa_run_rejects_rejected_plan_provenance(tmp_path: Path):
    provenance_path = tmp_path / "login_ticket.codex.plan.json"
    provenance_path.write_text(
        json.dumps(
            {
                "agent": "codex",
                "input_path": "tests/fixtures/inputs/login_ticket.md",
                "target": "web",
                "base_url": "http://127.0.0.1:8000",
                "prompt_path": "out/login_ticket.codex.prompt.txt",
                "raw_output_path": "out/login_ticket.codex.raw.txt",
                "accepted_scenario_path": None,
                "validation_status": "rejected",
                "validation_error": "invalid scenario",
            }
        )
    )

    result = CliRunner().invoke(
        app,
        [
            "qa",
            "run",
            "tests/fixtures/scenarios/web_login.yaml",
            "--target",
            "web",
            "--backend",
            "dry-run",
            "--plan-provenance",
            str(provenance_path),
            "--out",
            str(tmp_path / "runs"),
        ],
    )

    assert result.exit_code != 0
    combined_output = result.stdout + result.stderr
    assert "plan provenance must be accepted" in combined_output
    assert not (tmp_path / "runs").exists()


def test_qa_plan_bundle_generates_minimal_prd_artifacts(tmp_path: Path):
    result = CliRunner().invoke(
        app,
        [
            "qa",
            "plan-bundle",
            "tests/fixtures/inputs/login_ticket.md",
            "--out",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert f"bundle: {tmp_path / 'login'}" in result.stdout
    assert f"test_cases: {tmp_path / 'login' / 'test-cases.csv'}" in result.stdout
    assert f"estimate: {tmp_path / 'login' / 'qa-estimate.md'}" in result.stdout
    assert f"automation_candidates: {tmp_path / 'login' / 'automation-candidates.md'}" in result.stdout
    assert f"qa_run_tracker: {tmp_path / 'login' / 'qa-run-tracker.md'}" in result.stdout
    assert (tmp_path / "login" / "qa-scope.md").exists()
    assert (tmp_path / "login" / "checklist.md").exists()
    assert (tmp_path / "login" / "test-cases.csv").exists()
    assert (tmp_path / "login" / "risk-map.md").exists()
    assert (tmp_path / "login" / "qa-estimate.md").exists()
    assert (tmp_path / "login" / "automation-candidates.md").exists()
    assert (tmp_path / "login" / "qa-run-tracker.md").exists()
    assert (tmp_path / "login" / "manifest.json").exists()

    manifest = json.loads((tmp_path / "login" / "manifest.json").read_text())
    assert manifest["plan_id"] == "login"
    assert manifest["input_path"] == "tests/fixtures/inputs/login_ticket.md"
    assert manifest["source_paths"] == ["tests/fixtures/inputs/login_ticket.md"]
    assert manifest["artifacts"]["test_cases"] == str(tmp_path / "login" / "test-cases.csv")
    assert manifest["artifacts"]["qa_estimate"] == str(tmp_path / "login" / "qa-estimate.md")
    assert manifest["artifacts"]["automation_candidates"] == str(
        tmp_path / "login" / "automation-candidates.md"
    )
    assert manifest["artifacts"]["qa_run_tracker"] == str(tmp_path / "login" / "qa-run-tracker.md")
    risk_map = (tmp_path / "login" / "risk-map.md").read_text()
    assert "| edge case |" in risk_map
    assert "| network failure |" in risk_map
    assert "| permission/role |" in risk_map
    assert "| policy conflict |" in risk_map
    assert "| regression |" in risk_map


def test_qa_plan_bundle_accepts_additional_markdown_sources(tmp_path: Path):
    policy = tmp_path / "policy.md"
    policy.write_text(
        """# Login Policy

Acceptance criteria:
- Error message does not expose whether email exists
"""
    )

    result = CliRunner().invoke(
        app,
        [
            "qa",
            "plan-bundle",
            "tests/fixtures/inputs/login_ticket.md",
            "--source",
            str(policy),
            "--out",
            str(tmp_path / "plans"),
        ],
    )

    assert result.exit_code == 0
    bundle_dir = tmp_path / "plans" / "login"
    manifest = json.loads((bundle_dir / "manifest.json").read_text())
    assert manifest["source_paths"] == ["tests/fixtures/inputs/login_ticket.md", str(policy)]
    assert "- [ ] Error message does not expose whether email exists" in (
        bundle_dir / "checklist.md"
    ).read_text()


def test_qa_bundle_validate_accepts_generated_bundle(tmp_path: Path):
    result = CliRunner().invoke(
        app,
        [
            "qa",
            "plan-bundle",
            "tests/fixtures/inputs/login_ticket.md",
            "--out",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    bundle_dir = tmp_path / "login"

    validate = CliRunner().invoke(app, ["qa", "bundle-validate", str(bundle_dir)])

    assert validate.exit_code == 0
    assert "valid_bundle: login" in validate.stdout
    assert "artifacts: 8" in validate.stdout
    assert "checklist_items: 5" in validate.stdout
    assert "test_cases: 5" in validate.stdout
    assert "tracker_items: 5" in validate.stdout


def test_qa_bundle_validate_rejects_invalid_bundle(tmp_path: Path):
    result = CliRunner().invoke(
        app,
        [
            "qa",
            "plan-bundle",
            "tests/fixtures/inputs/login_ticket.md",
            "--out",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    bundle_dir = tmp_path / "login"
    (bundle_dir / "qa-estimate.md").unlink()

    validate = CliRunner().invoke(app, ["qa", "bundle-validate", str(bundle_dir)])

    assert validate.exit_code != 0
    assert "missing artifact: qa-estimate.md" in validate.stdout + validate.stderr


def test_qa_bug_draft_generates_bug_ticket_from_failed_tracker_item(tmp_path: Path):
    tracker_path = tmp_path / "qa-run-tracker.md"
    tracker_path.write_text(
        """# QA Run Tracker: Login

## Checklist Status

- [ ] User sees Dashboard
  - env: stg
  - status: failed
  - notes: Dashboard never appears after submit
"""
    )

    result = CliRunner().invoke(app, ["qa", "bug-draft", str(tracker_path)])

    assert result.exit_code == 0
    assert f"bug_ticket_draft: {tmp_path / 'bug-ticket-draft.md'}" in result.stdout
    assert (tmp_path / "bug-ticket-draft.md").exists()


def test_qa_tracker_update_updates_generated_tracker_item(tmp_path: Path):
    result = CliRunner().invoke(
        app,
        [
            "qa",
            "plan-bundle",
            "tests/fixtures/inputs/login_ticket.md",
            "--out",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0
    tracker_path = tmp_path / "login" / "qa-run-tracker.md"

    update = CliRunner().invoke(
        app,
        [
            "qa",
            "tracker-update",
            str(tracker_path),
            "--item",
            "5",
            "--env",
            "stg",
            "--status",
            "failed",
            "--notes",
            "Dashboard never appears after submit",
        ],
    )

    assert update.exit_code == 0
    assert f"updated_tracker: {tracker_path}" in update.stdout
    tracker = tracker_path.read_text()
    assert "- [x] User sees Dashboard" in tracker
    assert "  - env: stg" in tracker
    assert "  - status: failed" in tracker
    assert "  - notes: Dashboard never appears after submit" in tracker

    draft = CliRunner().invoke(app, ["qa", "bug-draft", str(tracker_path)])

    assert draft.exit_code == 0
    draft_text = (tmp_path / "login" / "bug-ticket-draft.md").read_text()
    assert "User sees Dashboard" in draft_text
    assert "Environment: stg" in draft_text


def test_qa_tracker_update_from_run_links_run_result_to_tracker(tmp_path: Path):
    bundle = CliRunner().invoke(
        app,
        [
            "qa",
            "plan-bundle",
            "tests/fixtures/inputs/login_ticket.md",
            "--out",
            str(tmp_path / "plans"),
        ],
    )
    run = CliRunner().invoke(
        app,
        [
            "qa",
            "run",
            "tests/fixtures/scenarios/web_login.yaml",
            "--target",
            "web",
            "--backend",
            "dry-run",
            "--out",
            str(tmp_path / "runs"),
        ],
    )
    assert bundle.exit_code == 0
    assert run.exit_code == 0
    tracker_path = tmp_path / "plans" / "login" / "qa-run-tracker.md"
    run_path = next((tmp_path / "runs").glob("run_*"))

    update = CliRunner().invoke(
        app,
        [
            "qa",
            "tracker-update-from-run",
            str(tracker_path),
            "--item",
            "1",
            "--env",
            "stg",
            "--run",
            str(run_path),
        ],
    )

    assert update.exit_code == 0
    assert f"updated_tracker: {tracker_path}" in update.stdout
    tracker = tracker_path.read_text()
    assert "- stg: passed" in tracker
    assert "- [x] User can open login page" in tracker
    assert f"report: {run_path / 'qa-report.md'}" in tracker


def test_qa_plan_generates_valid_scenario(tmp_path: Path):
    result = CliRunner().invoke(
        app,
        [
            "qa",
            "plan",
            "tests/fixtures/inputs/login_ticket.md",
            "--target",
            "web",
            "--out",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "planned:" in result.stdout
    assert "valid: login-smoke" in result.stdout
    assert (tmp_path / "login-smoke.generated.yaml").exists()

    provenance = json.loads((tmp_path / "login_ticket.template.plan.json").read_text())
    assert provenance == {
        "agent": "template",
        "input_path": "tests/fixtures/inputs/login_ticket.md",
        "target": "web",
        "base_url": "http://127.0.0.1:8000",
        "prompt_path": None,
        "raw_output_path": None,
        "accepted_scenario_path": str(tmp_path / "login-smoke.generated.yaml"),
        "validation_status": "accepted",
        "validation_error": None,
    }


def test_qa_plan_agent_codex_uses_shared_agent_contract(tmp_path: Path):
    fake_agent = tmp_path / "fake-agent.py"
    fake_agent.write_text(
        "import sys\n"
        "prompt = sys.stdin.read()\n"
        "assert 'Output only valid Newton scenario YAML' in prompt\n"
        "print('scenario:')\n"
        "print('  id: cli-agent-login-smoke')\n"
        "print('  title: CLI agent login smoke')\n"
        "print('targets:')\n"
        "print('  - id: web')\n"
        "print('    platform: web')\n"
        "print('    backend: playwright')\n"
        "print('    base_url: http://127.0.0.1:8000')\n"
        "print('steps:')\n"
        "print('  - id: open-login')\n"
        "print('    action: navigate')\n"
        "print('    target:')\n"
        "print('      web:')\n"
        "print('        url: /login.html')\n"
        "print('  - id: assert-dashboard')\n"
        "print('    action: assert_visible')\n"
        "print('    target:')\n"
        "print('      web:')\n"
        "print('        text: Dashboard')\n"
    )

    result = CliRunner().invoke(
        app,
        [
            "qa",
            "plan",
            "tests/fixtures/inputs/login_ticket.md",
            "--agent",
            "codex",
            "--agent-command",
            f"python {fake_agent}",
            "--target",
            "web",
            "--out",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "planned:" in result.stdout
    assert "valid: cli-agent-login-smoke" in result.stdout
    assert (tmp_path / "cli-agent-login-smoke.generated.yaml").exists()
    assert (tmp_path / "login_ticket.codex.prompt.txt").exists()
    assert (tmp_path / "login_ticket.codex.raw.txt").exists()
    assert (tmp_path / "login_ticket.codex.plan.json").exists()


def test_qa_report_prints_existing_report_path(tmp_path: Path):
    run_dir = tmp_path / "run_123"
    run_dir.mkdir(parents=True)
    report_path = run_dir / "qa-report.md"
    report_path.write_text("# report")

    result = CliRunner().invoke(app, ["qa", "report", str(run_dir)])

    assert result.exit_code == 0
    assert str(report_path) in result.stdout
