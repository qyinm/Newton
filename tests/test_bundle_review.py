from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from newton.bundle_review import BundleReviewError, review_planning_bundle
from newton.planning_bundle import generate_planning_bundle


EXPECTED_REVIEW_CATEGORIES = {
    "coverage",
    "source_grounding",
    "estimate_clarity",
    "risk_usefulness",
    "automation_suitability",
}


def test_review_planning_bundle_template_writes_advisory_artifacts(tmp_path: Path):
    bundle_dir = generate_planning_bundle(Path("tests/fixtures/inputs/login_ticket.md"), out_dir=tmp_path)

    result = review_planning_bundle(bundle_dir, agent="template")

    assert result.agent == "template"
    assert result.score == 86
    assert result.verdict == "advisory_pass"
    assert result.category_scores == {
        "coverage": 100,
        "source_grounding": 80,
        "estimate_clarity": 90,
        "risk_usefulness": 80,
        "automation_suitability": 80,
    }
    assert result.review_json_path == bundle_dir / "bundle-review.template.json"
    assert result.review_markdown_path == bundle_dir / "bundle-review.template.md"
    payload = json.loads(result.review_json_path.read_text())
    assert payload["agent"] == "template"
    assert payload["bundle_path"] == str(bundle_dir)
    assert payload["score"] == 86
    assert payload["verdict"] == "advisory_pass"
    assert payload["category_scores"] == result.category_scores
    assert payload["gate"] == {"enabled": False, "threshold": None, "passed": None}
    assert payload["findings"][0]["severity"] == "low"
    markdown = result.review_markdown_path.read_text()
    assert "# QA Bundle Review: login" in markdown
    assert "Score: 86" in markdown
    assert "| coverage | 100 |" in markdown
    assert "| automation_suitability | 80 |" in markdown
    assert "This is an advisory review" in markdown


def test_review_planning_bundle_codex_uses_agent_json_contract(tmp_path: Path):
    bundle_dir = generate_planning_bundle(Path("tests/fixtures/inputs/login_ticket.md"), out_dir=tmp_path)

    def fake_run(argv, *, input, text, capture_output, check):
        assert argv == ["fake-codex"]
        assert input is not None
        assert "Review this Newton QA planning bundle" in input
        assert "checklist.md" in input
        assert "test-cases.csv" in input
        return subprocess.CompletedProcess(
            argv,
            0,
            stdout=json.dumps(
                {
                    "score": 72,
                    "verdict": "needs_improvement",
                    "category_scores": {
                        "coverage": 80,
                        "source_grounding": 70,
                        "estimate_clarity": 60,
                        "risk_usefulness": 75,
                        "automation_suitability": 75,
                    },
                    "findings": [
                        {
                            "severity": "medium",
                            "artifact": "test-cases.csv",
                            "finding": "No locked account coverage.",
                            "suggestion": "Add a locked account test case.",
                        }
                    ],
                }
            ),
            stderr="",
        )

    result = review_planning_bundle(bundle_dir, agent="codex", command=["fake-codex"], run=fake_run)

    assert result.agent == "codex"
    assert result.score == 72
    assert result.verdict == "needs_improvement"
    assert set(result.category_scores) == EXPECTED_REVIEW_CATEGORIES
    assert result.prompt_path == bundle_dir / "bundle-review.codex.prompt.txt"
    assert result.raw_output_path == bundle_dir / "bundle-review.codex.raw.txt"
    payload = json.loads((bundle_dir / "bundle-review.codex.json").read_text())
    assert payload["agent"] == "codex"
    assert payload["bundle_path"] == str(bundle_dir)
    assert payload["category_scores"]["estimate_clarity"] == 60
    assert payload["findings"][0]["suggestion"] == "Add a locked account test case."
    markdown = (bundle_dir / "bundle-review.codex.md").read_text()
    assert "| estimate_clarity | 60 |" in markdown
    assert "No locked account coverage." in markdown


def test_review_planning_bundle_default_codex_command_is_read_only(tmp_path: Path):
    bundle_dir = generate_planning_bundle(Path("tests/fixtures/inputs/login_ticket.md"), out_dir=tmp_path)

    def fake_run(argv, *, input, text, capture_output, check):
        assert argv == ["codex", "exec", "--sandbox", "read-only", "-"]
        return subprocess.CompletedProcess(
            argv,
            0,
            stdout=json.dumps(
                {
                    "score": 80,
                    "verdict": "advisory_pass",
                    "category_scores": {
                        "coverage": 80,
                        "source_grounding": 80,
                        "estimate_clarity": 80,
                        "risk_usefulness": 80,
                        "automation_suitability": 80,
                    },
                    "findings": [],
                }
            ),
            stderr="",
        )

    review_planning_bundle(bundle_dir, agent="codex", run=fake_run)


def test_review_planning_bundle_default_claude_command_disables_tools(tmp_path: Path):
    bundle_dir = generate_planning_bundle(Path("tests/fixtures/inputs/login_ticket.md"), out_dir=tmp_path)

    def fake_run(argv, *, input, text, capture_output, check):
        assert argv == ["claude", "-p", "--tools", ""]
        return subprocess.CompletedProcess(
            argv,
            0,
            stdout=json.dumps(
                {
                    "score": 80,
                    "verdict": "advisory_pass",
                    "category_scores": {
                        "coverage": 80,
                        "source_grounding": 80,
                        "estimate_clarity": 80,
                        "risk_usefulness": 80,
                        "automation_suitability": 80,
                    },
                    "findings": [],
                }
            ),
            stderr="",
        )

    review_planning_bundle(bundle_dir, agent="claude", run=fake_run)


def test_review_planning_bundle_requires_complete_category_scores(tmp_path: Path):
    bundle_dir = generate_planning_bundle(Path("tests/fixtures/inputs/login_ticket.md"), out_dir=tmp_path)

    def fake_run(argv, *, input, text, capture_output, check):
        return subprocess.CompletedProcess(
            argv,
            0,
            stdout=json.dumps(
                {
                    "score": 80,
                    "verdict": "advisory_pass",
                    "category_scores": {
                        "coverage": 80,
                        "source_grounding": 80,
                        "estimate_clarity": 80,
                    },
                    "findings": [],
                }
            ),
            stderr="",
        )

    with pytest.raises(BundleReviewError, match="category_scores missing required categories"):
        review_planning_bundle(bundle_dir, agent="codex", command=["fake-codex"], run=fake_run)

    assert (bundle_dir / "bundle-review.codex.raw.txt").exists()
    assert not (bundle_dir / "bundle-review.codex.json").exists()


def test_review_planning_bundle_gate_records_threshold_and_failure(tmp_path: Path):
    bundle_dir = generate_planning_bundle(Path("tests/fixtures/inputs/login_ticket.md"), out_dir=tmp_path)

    result = review_planning_bundle(bundle_dir, agent="template", gate=True, gate_threshold=90)

    assert result.score == 86
    assert result.gate is True
    assert result.gate_threshold == 90
    assert result.gate_passed is False
    payload = json.loads(result.review_json_path.read_text())
    assert payload["gate"] == {"enabled": True, "threshold": 90, "passed": False}
    markdown = result.review_markdown_path.read_text()
    assert "- Mode: release gate" in markdown
    assert "- Gate threshold: 90" in markdown
    assert "- Gate result: failed" in markdown


def test_review_planning_bundle_rejects_invalid_agent_json(tmp_path: Path):
    bundle_dir = generate_planning_bundle(Path("tests/fixtures/inputs/login_ticket.md"), out_dir=tmp_path)

    def fake_run(argv, *, input, text, capture_output, check):
        return subprocess.CompletedProcess(argv, 0, stdout="not json", stderr="")

    with pytest.raises(BundleReviewError, match="agent review output did not validate"):
        review_planning_bundle(bundle_dir, agent="codex", command=["fake-codex"], run=fake_run)

    assert (bundle_dir / "bundle-review.codex.raw.txt").read_text() == "not json"
    assert not (bundle_dir / "bundle-review.codex.json").exists()


def test_review_planning_bundle_validates_bundle_before_review(tmp_path: Path):
    bundle_dir = generate_planning_bundle(Path("tests/fixtures/inputs/login_ticket.md"), out_dir=tmp_path)
    (bundle_dir / "qa-estimate.md").unlink()

    with pytest.raises(BundleReviewError, match="bundle validation failed: missing artifact: qa-estimate.md"):
        review_planning_bundle(bundle_dir, agent="template")

    assert not (bundle_dir / "bundle-review.template.json").exists()


def test_dogfood_login_review_artifact_records_planning_quality_scores():
    artifact_path = Path("qa/dogfood/login/plan/bundle-review.template.json")

    payload = json.loads(artifact_path.read_text())

    assert payload["agent"] == "template"
    assert payload["bundle_path"] == "qa/dogfood/login/plan"
    assert payload["score"] == 88
    assert payload["category_scores"] == {
        "coverage": 100,
        "source_grounding": 80,
        "estimate_clarity": 80,
        "risk_usefulness": 100,
        "automation_suitability": 80,
    }
    assert payload["gate"] == {"enabled": False, "threshold": None, "passed": None}
    markdown = Path("qa/dogfood/login/plan/bundle-review.template.md").read_text()
    assert "| source_grounding | 80 |" in markdown
    assert "| risk_usefulness | 100 |" in markdown
