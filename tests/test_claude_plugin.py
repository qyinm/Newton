from __future__ import annotations

import json
from pathlib import Path


MARKETPLACE_PATH = Path(".claude-plugin/marketplace.json")
PLUGIN_ROOT = Path("plugins/newton")


def test_claude_marketplace_exposes_newton_plugin():
    marketplace = json.loads(MARKETPLACE_PATH.read_text())

    assert marketplace["name"] == "newton"
    assert marketplace["owner"]["name"] == "qyinm"
    assert "description" not in marketplace
    assert marketplace["plugins"] == [
        {
            "name": "newton",
            "source": "./plugins/newton",
            "description": "Newton QA CLI wrapper for Claude Code",
            "version": "0.1.0",
            "category": "testing",
            "tags": ["qa", "playwright", "agent-native"],
        }
    ]


def test_claude_plugin_manifest_points_at_commands():
    manifest = json.loads((PLUGIN_ROOT / ".claude-plugin" / "plugin.json").read_text())

    assert manifest["name"] == "newton"
    assert manifest["version"] == "0.1.0"
    assert manifest["commands"] == "./commands/"
    assert manifest["description"] == "Newton QA CLI wrapper for Claude Code"
    assert manifest["author"]["name"] == "qyinm"


def test_claude_plugin_commands_wrap_newton_cli():
    expected_commands = {
        "newton-setup.md": ["scripts/install.sh", "newton version"],
        "newton-dogfood.md": ["newton qa bundle-validate", "newton qa validate", "newton qa runs"],
        "newton-plan.md": ["newton qa plan-bundle", "newton qa plan"],
        "newton-run.md": ["newton qa run", "--backend playwright"],
        "newton-bug-draft.md": ["newton qa tracker-update-from-run", "newton qa bug-draft"],
    }

    for filename, snippets in expected_commands.items():
        command = PLUGIN_ROOT / "commands" / filename
        assert command.exists(), filename
        text = command.read_text()
        assert text.startswith("---\n"), filename
        assert "description:" in text
        for snippet in snippets:
            assert snippet in text


def test_readme_documents_claude_plugin_install_path():
    readme = Path("README.md").read_text()

    assert "claude plugin marketplace add qyinm/Newton" in readme
    assert "claude plugin install newton@newton" in readme
    assert "/newton-setup" in readme
    assert "/newton-dogfood" in readme
