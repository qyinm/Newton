from pathlib import Path


def test_readme_starts_with_release_demo_flow():
    readme = Path("README.md").read_text()

    assert readme.index("## Install") < readme.index("## First Release Demo")
    assert readme.index("## First Release Demo") < readme.index("## Claude Code Plugin")
    assert "newton qa plan-bundle qa/dogfood/login/inputs/ticket.md" in readme
    assert "newton qa run qa/dogfood/login/scenario/login-smoke.generated.yaml" in readme
    assert "failed_report: qa/dogfood/login/runs/run_*/qa-report.md" in readme
    assert "qa/dogfood/login/runs/run_*/playwright-trace.zip" in readme
    assert "qa/dogfood/login/bug-ticket-draft.md" in readme


def test_readme_explains_artifact_locations_and_troubleshooting():
    readme = Path("README.md").read_text()

    assert "qa/dogfood/login/plan/qa-scope.md" in readme
    assert "qa/dogfood/login/runs/index.jsonl" in readme
    assert "docs/troubleshooting.md" in readme


def test_troubleshooting_covers_release_demo_failure_modes():
    troubleshooting = Path("docs/troubleshooting.md").read_text()

    for snippet in [
        "python -m playwright install chromium",
        "newton qa validate",
        "Unsupported selector payload",
        "python -m playwright show-trace",
        "Codex or Claude failures",
        "--agent-command",
    ]:
        assert snippet in troubleshooting
