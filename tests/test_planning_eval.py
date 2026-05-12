from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from newton.cli import app
from newton.planning_eval import evaluate_planning_cases


def test_evaluate_planning_cases_scores_committed_login_policy_case(tmp_path: Path):
    result = evaluate_planning_cases(
        Path("qa/evals/planning"),
        out_dir=tmp_path / "eval-runs",
        min_score=100,
    )

    assert result.passed
    assert result.score == 100
    report = json.loads(result.report_json_path.read_text())
    assert report["case_count"] == 1
    assert report["cases"][0]["id"] == "login-policy"
    assert report["cases"][0]["bundle_dir"].endswith("login-policy/bundle")


def test_qa_eval_planning_writes_json_and_markdown_reports(tmp_path: Path):
    result = CliRunner().invoke(
        app,
        [
            "qa",
            "eval-planning",
            "qa/evals/planning",
            "--out",
            str(tmp_path / "eval-runs"),
            "--min-score",
            "100",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "planning_eval_json:" in result.stdout
    assert "planning_eval_markdown:" in result.stdout
    assert "score: 100" in result.stdout
    report = json.loads((tmp_path / "eval-runs" / "planning-eval-report.json").read_text())
    assert report["passed"] is True
    assert report["cases"][0]["checks"][0]["name"] == "bundle_valid"


def test_qa_eval_planning_fails_when_expected_terms_are_missing(tmp_path: Path):
    case_dir = tmp_path / "cases" / "missing-term"
    case_dir.mkdir(parents=True)
    (case_dir / "input.md").write_text(
        """# Billing

Acceptance criteria:
- User can open billing settings.
"""
    )
    (case_dir / "expected.json").write_text(
        json.dumps(
            {
                "id": "missing-term",
                "min_score": 100,
                "required_terms": ["wire transfer approval"],
            }
        )
    )

    result = CliRunner().invoke(
        app,
        [
            "qa",
            "eval-planning",
            str(tmp_path / "cases"),
            "--out",
            str(tmp_path / "eval-runs"),
            "--min-score",
            "100",
        ],
    )

    assert result.exit_code == 1
    report = json.loads((tmp_path / "eval-runs" / "planning-eval-report.json").read_text())
    assert report["passed"] is False
    assert report["cases"][0]["checks"][1]["name"] == "required_terms"
    assert report["cases"][0]["checks"][1]["details"]["missing"] == ["wire transfer approval"]
