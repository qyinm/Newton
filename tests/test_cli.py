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


def test_qa_bundle_review_template_writes_advisory_review(tmp_path: Path):
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

    review = CliRunner().invoke(app, ["qa", "bundle-review", str(bundle_dir)])

    assert review.exit_code == 0
    assert f"review_json: {bundle_dir / 'bundle-review.template.json'}" in review.stdout
    assert f"review_markdown: {bundle_dir / 'bundle-review.template.md'}" in review.stdout
    assert "score: 80" in review.stdout
    assert "verdict: advisory_pass" in review.stdout
    payload = json.loads((bundle_dir / "bundle-review.template.json").read_text())
    assert payload["agent"] == "template"
    assert payload["score"] == 80


def test_qa_bundle_review_agent_command_writes_review_artifacts(tmp_path: Path):
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
    fake_agent = tmp_path / "fake-review-agent.py"
    fake_agent.write_text(
        "import json, sys\n"
        "prompt = sys.stdin.read()\n"
        "assert 'Review this Newton QA planning bundle' in prompt\n"
        "print(json.dumps({'score': 66, 'verdict': 'needs_improvement', 'findings': [{'severity': 'medium', 'artifact': 'checklist.md', 'finding': 'Missing negative login cases.', 'suggestion': 'Add invalid password coverage.'}]}))\n"
    )

    review = CliRunner().invoke(
        app,
        [
            "qa",
            "bundle-review",
            str(bundle_dir),
            "--agent",
            "codex",
            "--agent-command",
            f"python {fake_agent}",
        ],
    )

    assert review.exit_code == 0
    assert f"review_json: {bundle_dir / 'bundle-review.codex.json'}" in review.stdout
    assert f"review_markdown: {bundle_dir / 'bundle-review.codex.md'}" in review.stdout
    assert "score: 66" in review.stdout
    assert "verdict: needs_improvement" in review.stdout
    assert (bundle_dir / "bundle-review.codex.prompt.txt").exists()
    assert (bundle_dir / "bundle-review.codex.raw.txt").exists()
    markdown = (bundle_dir / "bundle-review.codex.md").read_text()
    assert "Missing negative login cases." in markdown


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


def test_qa_plan_bundle_agent_codex_generates_valid_bundle_with_provenance(tmp_path: Path):
    fake_agent = tmp_path / "fake-bundle-agent.py"
    fake_agent.write_text(
        "import json, sys\n"
        "prompt = sys.stdin.read()\n"
        "assert 'Generate a Newton QA planning bundle' in prompt\n"
        "assert 'qa/inputs/login-ticket.md' in prompt\n"
        "payload = {\n"
        "  'plan_id': 'login',\n"
        "  'title': 'Login',\n"
        "  'qa_scope': {\n"
        "    'goal': 'Users can securely log in with email and password.',\n"
        "    'in_scope': ['Successful login', 'Secure login policy feedback'],\n"
        "    'out_of_scope': ['Cross-browser matrix']\n"
        "  },\n"
        "  'checklist': [\n"
        "    {'title': 'User can open login page', 'risk_category': 'functional', 'priority': 'P0', 'source_reference': 'login-ticket.md'},\n"
        "    {'title': 'Error message does not expose whether email exists', 'risk_category': 'policy conflict', 'priority': 'P1', 'source_reference': 'login-policy.md'}\n"
        "  ],\n"
        "  'test_cases': [\n"
        "    {'id': 'TC-001', 'title': 'User can open login page', 'priority': 'P0', 'precondition': 'Staging is reachable', 'steps': 'Open /login', 'expected_result': 'Login page is visible', 'environment': 'dev/stg/prod', 'risk_category': 'functional', 'source_reference': 'login-ticket.md'},\n"
        "    {'id': 'TC-002', 'title': 'Error message does not expose whether email exists', 'priority': 'P1', 'precondition': 'Invalid login test account exists', 'steps': 'Submit unknown email and wrong password', 'expected_result': 'Generic error is shown', 'environment': 'dev/stg/prod', 'risk_category': 'policy conflict', 'source_reference': 'login-policy.md'}\n"
        "  ],\n"
        "  'risk_map': [\n"
        "    {'area': 'functional', 'priority': 'P0', 'rationale': 'Login blocks account access'},\n"
        "    {'area': 'edge case', 'priority': 'P1', 'rationale': 'Empty and invalid credentials can break form handling'},\n"
        "    {'area': 'network failure', 'priority': 'P1', 'rationale': 'Timeouts need recoverable feedback'},\n"
        "    {'area': 'permission/role', 'priority': 'P1', 'rationale': 'Locked users need correct access handling'},\n"
        "    {'area': 'policy conflict', 'priority': 'P1', 'rationale': 'Error copy must not reveal account existence'},\n"
        "    {'area': 'regression', 'priority': 'P1', 'rationale': 'Existing login smoke can regress'}\n"
        "  ],\n"
        "  'qa_estimate': {\n"
        "    'size': 'S',\n"
        "    'reasoning': ['2 checklist items', 'Policy-sensitive error copy'],\n"
        "    'manual_qa_time': ['Happy path smoke: 15 min', 'Negative/error cases: 20 min'],\n"
        "    'assumptions': ['Staging environment is reachable']\n"
        "  },\n"
        "  'automation_candidates': [\n"
        "    {'title': 'User can open login page', 'recommendation': 'Recommended', 'reason': 'Stable smoke path with clear pass/fail signal.'},\n"
        "    {'title': 'Error message does not expose whether email exists', 'recommendation': 'Manual For Now', 'reason': 'Copy and policy details should be reviewed manually first.'}\n"
        "  ]\n"
        "}\n"
        "print(json.dumps(payload))\n"
    )

    result = CliRunner().invoke(
        app,
        [
            "qa",
            "plan-bundle",
            "qa/inputs/login-ticket.md",
            "--source",
            "qa/inputs/login-policy.md",
            "--agent",
            "codex",
            "--agent-command",
            f"python {fake_agent}",
            "--out",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    bundle_dir = tmp_path / "login"
    assert f"bundle: {bundle_dir}" in result.stdout
    assert (bundle_dir / "bundle-generation.codex.prompt.txt").exists()
    assert (bundle_dir / "bundle-generation.codex.raw.txt").exists()
    assert (bundle_dir / "bundle-generation.codex.json").exists()
    manifest = json.loads((bundle_dir / "manifest.json").read_text())
    assert manifest["agent"] == "codex"
    assert manifest["generation"]["validation_status"] == "accepted"
    assert manifest["generation"]["prompt_path"] == str(bundle_dir / "bundle-generation.codex.prompt.txt")
    assert "Error message does not expose whether email exists" in (bundle_dir / "checklist.md").read_text()

    validate = CliRunner().invoke(app, ["qa", "bundle-validate", str(bundle_dir)])

    assert validate.exit_code == 0
    assert "valid_bundle: login" in validate.stdout
    assert "checklist_items: 2" in validate.stdout
    assert "test_cases: 2" in validate.stdout


def test_qa_plan_bundle_agent_rejects_invalid_output_and_preserves_raw(tmp_path: Path):
    fake_agent = tmp_path / "fake-invalid-bundle-agent.py"
    fake_agent.write_text("print('not json')\n")

    result = CliRunner().invoke(
        app,
        [
            "qa",
            "plan-bundle",
            "qa/inputs/login-ticket.md",
            "--agent",
            "codex",
            "--agent-command",
            f"python {fake_agent}",
            "--out",
            str(tmp_path),
        ],
    )

    assert result.exit_code != 0
    combined_output = result.stdout + result.stderr
    assert "agent planning bundle output did not validate" in combined_output
    bundle_dir = tmp_path / "login"
    assert (bundle_dir / "bundle-generation.codex.prompt.txt").exists()
    assert (bundle_dir / "bundle-generation.codex.raw.txt").read_text().strip() == "not json"
    assert not (bundle_dir / "manifest.json").exists()


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
