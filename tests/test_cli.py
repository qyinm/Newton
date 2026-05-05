from pathlib import Path

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


def test_qa_report_prints_existing_report_path(tmp_path: Path):
    run_dir = tmp_path / "run_123"
    run_dir.mkdir(parents=True)
    report_path = run_dir / "qa-report.md"
    report_path.write_text("# report")

    result = CliRunner().invoke(app, ["qa", "report", str(run_dir)])

    assert result.exit_code == 0
    assert str(report_path) in result.stdout
