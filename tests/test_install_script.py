from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path


INSTALL_SCRIPT = Path("scripts/install.sh")


def run_install_dry_run(*args: str, path: str | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["NEWTON_INSTALL_DRY_RUN"] = "1"
    env["NEWTON_REPO_URL"] = "https://example.com/qyinm/Newton.git"
    env["NEWTON_REF"] = "test-ref"
    if path is not None:
        env["PATH"] = path
    return subprocess.run(
        ["bash", str(INSTALL_SCRIPT), *args],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def test_install_script_exists_and_is_executable():
    assert INSTALL_SCRIPT.exists()
    assert INSTALL_SCRIPT.stat().st_mode & stat.S_IXUSR


def test_install_script_defaults_to_uv_tool_install_with_web_extra():
    result = run_install_dry_run()

    assert result.returncode == 0
    assert (
        "uv tool install --force git+https://example.com/qyinm/Newton.git@test-ref#egg=newton-qa\\[web\\]"
        in result.stdout
        or "pipx install --force git+https://example.com/qyinm/Newton.git@test-ref#egg=newton-qa\\[web\\]"
        in result.stdout
    )
    assert (
        "uvx --from git+https://example.com/qyinm/Newton.git@test-ref#egg=newton-qa\\[web\\] playwright install chromium"
        in result.stdout
        or "python3 -m playwright install chromium" in result.stdout
    )
    assert "newton version" in result.stdout


def test_install_script_can_skip_web_runtime():
    result = run_install_dry_run("--no-web")

    assert result.returncode == 0
    assert "#egg=newton-qa" in result.stdout
    assert "playwright install chromium" not in result.stdout


def test_readme_documents_official_cli_install_path():
    readme = Path("README.md").read_text()

    assert "curl -fsSL https://raw.githubusercontent.com/qyinm/Newton/main/scripts/install.sh | bash" in readme
    assert "newton version" in readme
