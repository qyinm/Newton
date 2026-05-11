import json
import subprocess
from pathlib import Path

from newton.agent_planning_bundle import generate_planning_bundle_with_agent
from newton.models import ARTIFACT_CONTRACT_VERSION


def _valid_payload() -> dict[str, object]:
    return {
        "plan_id": "login",
        "title": "Login",
        "qa_scope": {
            "goal": "Users can securely log in with email and password.",
            "in_scope": ["Successful login", "Secure feedback"],
            "out_of_scope": ["Browser matrix"],
        },
        "checklist": [
            {
                "title": "User can open login page",
                "risk_category": "functional",
                "priority": "P0",
                "source_reference": "login-ticket.md",
            }
        ],
        "test_cases": [
            {
                "id": "TC-001",
                "title": "User can open login page",
                "priority": "P0",
                "precondition": "Staging is reachable",
                "steps": "Open /login",
                "expected_result": "Login page is visible",
                "environment": "dev/stg/prod",
                "risk_category": "functional",
                "source_reference": "login-ticket.md",
            }
        ],
        "risk_map": [
            {"area": "functional", "priority": "P0", "rationale": "Login blocks access"},
            {"area": "edge case", "priority": "P1", "rationale": "Invalid input"},
            {"area": "network failure", "priority": "P1", "rationale": "Timeouts"},
            {"area": "permission/role", "priority": "P1", "rationale": "Locked users"},
            {"area": "policy conflict", "priority": "P1", "rationale": "Secure feedback"},
            {"area": "regression", "priority": "P1", "rationale": "Existing login smoke"},
        ],
        "qa_estimate": {
            "size": "S",
            "reasoning": ["Small login bundle"],
            "manual_qa_time": ["30 minutes"],
            "assumptions": ["Staging is reachable"],
            "evidence_factors": [
                {
                    "factor": "checklist_items",
                    "value": "1 checklist item",
                    "evidence": "Login ticket has one core login check.",
                    "source_reference": "login-ticket.md",
                }
            ],
        },
        "automation_candidates": [
            {
                "title": "User can open login page",
                "recommendation": "Recommended",
                "reason": "Stable smoke signal",
            }
        ],
    }


def test_codex_agent_uses_output_last_message_file_when_stdout_is_noisy(tmp_path: Path):
    seen_argv: list[str] = []

    def fake_run(argv, **kwargs):
        seen_argv.extend(argv)
        assert kwargs["input"]
        assert 'Set "plan_id" to exactly "login".' in kwargs["input"]
        assert kwargs["capture_output"] is True
        output_flag_index = argv.index("--output-last-message")
        last_message_path = Path(argv[output_flag_index + 1])
        last_message_path.write_text(json.dumps(_valid_payload()))
        return subprocess.CompletedProcess(
            argv,
            0,
            stdout="OpenAI Codex transcript and token summary, not JSON",
            stderr="skill loader warning\n",
        )

    bundle_dir = generate_planning_bundle_with_agent(
        Path("qa/inputs/login-ticket.md"),
        source_paths=[Path("qa/inputs/login-policy.md")],
        out_dir=tmp_path,
        agent="codex",
        run=fake_run,
    )

    assert bundle_dir == tmp_path / "login"
    assert seen_argv[:3] == ["codex", "exec", "--sandbox"]
    assert "--output-last-message" in seen_argv
    assert json.loads((bundle_dir / "manifest.json").read_text())["contract_version"] == ARTIFACT_CONTRACT_VERSION
    assert json.loads((bundle_dir / "bundle-generation.codex.json").read_text())["plan_id"] == "login"
    raw_output = (bundle_dir / "bundle-generation.codex.raw.txt").read_text()
    assert "OpenAI Codex transcript" in raw_output
    assert "skill loader warning" in raw_output
