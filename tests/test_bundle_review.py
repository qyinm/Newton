from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from newton.bundle_review import BundleReviewError, review_planning_bundle
from newton.planning_bundle import generate_planning_bundle


def test_review_planning_bundle_template_writes_advisory_artifacts(tmp_path: Path):
    bundle_dir = generate_planning_bundle(Path("tests/fixtures/inputs/login_ticket.md"), out_dir=tmp_path)

    result = review_planning_bundle(bundle_dir, agent="template")

    assert result.agent == "template"
    assert result.score == 80
    assert result.verdict == "advisory_pass"
    assert result.review_json_path == bundle_dir / "bundle-review.template.json"
    assert result.review_markdown_path == bundle_dir / "bundle-review.template.md"
    payload = json.loads(result.review_json_path.read_text())
    assert payload["agent"] == "template"
    assert payload["bundle_path"] == str(bundle_dir)
    assert payload["score"] == 80
    assert payload["verdict"] == "advisory_pass"
    assert payload["findings"][0]["severity"] == "low"
    markdown = result.review_markdown_path.read_text()
    assert "# QA Bundle Review: login" in markdown
    assert "Score: 80" in markdown
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
    assert result.prompt_path == bundle_dir / "bundle-review.codex.prompt.txt"
    assert result.raw_output_path == bundle_dir / "bundle-review.codex.raw.txt"
    payload = json.loads((bundle_dir / "bundle-review.codex.json").read_text())
    assert payload["agent"] == "codex"
    assert payload["bundle_path"] == str(bundle_dir)
    assert payload["findings"][0]["suggestion"] == "Add a locked account test case."
    markdown = (bundle_dir / "bundle-review.codex.md").read_text()
    assert "No locked account coverage." in markdown


def test_review_planning_bundle_default_codex_command_is_read_only(tmp_path: Path):
    bundle_dir = generate_planning_bundle(Path("tests/fixtures/inputs/login_ticket.md"), out_dir=tmp_path)

    def fake_run(argv, *, input, text, capture_output, check):
        assert argv == ["codex", "exec", "--sandbox", "read-only", "-"]
        return subprocess.CompletedProcess(
            argv,
            0,
            stdout=json.dumps({"score": 80, "verdict": "advisory_pass", "findings": []}),
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
            stdout=json.dumps({"score": 80, "verdict": "advisory_pass", "findings": []}),
            stderr="",
        )

    review_planning_bundle(bundle_dir, agent="claude", run=fake_run)


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
