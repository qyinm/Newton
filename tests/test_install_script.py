from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALL_SCRIPT = REPO_ROOT / "scripts" / "install.sh"
README = REPO_ROOT / "README.md"


def fake_path(tmp_path: Path, *commands: str) -> str:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for command in commands:
        path = bin_dir / command
        path.write_text("#!/usr/bin/env sh\nexit 0\n")
        path.chmod(0o755)
    return f"{bin_dir}{os.pathsep}/usr/bin{os.pathsep}/bin"


def run_install_dry_run(
    *args: str,
    path: str | None = None,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["NEWTON_INSTALL_DRY_RUN"] = "1"
    env["NEWTON_REPO_URL"] = "https://example.com/qyinm/Newton.git"
    env["NEWTON_REF"] = "test-ref"
    if path is not None:
        env["PATH"] = path
    return subprocess.run(
        ["/bin/bash", str(INSTALL_SCRIPT), *args],
        text=True,
        capture_output=True,
        check=False,
        env=env,
        cwd=cwd,
    )


def test_install_script_exists_and_is_executable():
    assert INSTALL_SCRIPT.exists()
    assert INSTALL_SCRIPT.stat().st_mode & stat.S_IXUSR


def test_install_script_prefers_uv_tool_install_with_web_extra(tmp_path: Path):
    result = run_install_dry_run(path=fake_path(tmp_path, "uv"), cwd=tmp_path)

    assert result.returncode == 0
    assert "uv tool install --force git+https://example.com/qyinm/Newton.git@test-ref#egg=newton-qa\\[web\\]" in result.stdout
    assert (
        "uvx --from git+https://example.com/qyinm/Newton.git@test-ref#egg=newton-qa\\[web\\] playwright install chromium"
        in result.stdout
    )
    assert "newton version" in result.stdout


def test_install_script_falls_back_to_pipx_and_python_playwright_install(tmp_path: Path):
    result = run_install_dry_run(path=fake_path(tmp_path, "pipx", "python3"), cwd=tmp_path)

    assert result.returncode == 0
    assert "pipx install --force git+https://example.com/qyinm/Newton.git@test-ref#egg=newton-qa\\[web\\]" in result.stdout
    assert "python3 -m playwright install chromium" in result.stdout


def test_install_script_can_skip_web_runtime(tmp_path: Path):
    result = run_install_dry_run("--no-web", path=fake_path(tmp_path, "uv"), cwd=tmp_path)

    assert result.returncode == 0
    assert "#egg=newton-qa" in result.stdout
    assert "playwright install chromium" not in result.stdout


def test_install_script_prints_fixture_free_smoke_path(tmp_path: Path):
    result = run_install_dry_run("--no-web", path=fake_path(tmp_path, "uv"), cwd=tmp_path)

    assert result.returncode == 0
    assert "tmpdir=$(mktemp -d)" in result.stdout
    assert "newton qa plan \"$tmpdir/login-ticket.md\" --agent template --target web --out \"$tmpdir/scenarios\"" in result.stdout
    assert "newton qa validate \"$tmpdir/scenarios/login-smoke.generated.yaml\"" in result.stdout
    assert "qa/dogfood" not in result.stdout
    assert "qa/scenarios/web-login-smoke.yaml" not in result.stdout


def test_install_script_accepts_ref_and_repo_overrides(tmp_path: Path):
    result = run_install_dry_run(
        "--no-web",
        "--ref",
        "v0.1.0",
        "--repo",
        "https://github.com/acme/newton-fork.git",
        path=fake_path(tmp_path, "uv"),
        cwd=tmp_path,
    )

    assert result.returncode == 0
    assert "Installing Newton QA CLI from https://github.com/acme/newton-fork.git@v0.1.0" in result.stdout
    assert "uv tool install --force git+https://github.com/acme/newton-fork.git@v0.1.0#egg=newton-qa" in result.stdout


def test_install_script_errors_without_uv_or_pipx(tmp_path: Path):
    result = run_install_dry_run(path=fake_path(tmp_path), cwd=tmp_path)

    assert result.returncode == 1
    assert "error: install requires uv or pipx." in result.stderr
    assert "Install uv from https://docs.astral.sh/uv/ or install pipx" in result.stderr


def test_readme_documents_official_cli_install_path():
    readme = README.read_text()

    assert "curl -fsSL https://raw.githubusercontent.com/qyinm/Newton/main/scripts/install.sh | bash" in readme
    assert "newton version" in readme


def test_readme_documents_tagged_release_install_and_fixture_free_smoke_path():
    readme = README.read_text()

    assert "bash -s -- --ref v0.1.0" in readme
    assert "mktemp -d" in readme
    assert "newton qa plan \"$tmpdir/login-ticket.md\" --agent template --target web --out \"$tmpdir/scenarios\"" in readme
    assert "newton qa validate \"$tmpdir/scenarios/login-smoke.generated.yaml\"" in readme


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        (("--no-web",), "#egg=newton-qa"),
        (("--ref", "v0.1.0"), "@v0.1.0#egg=newton-qa\\[web\\]"),
        (("--repo", "https://github.com/acme/newton-fork.git"), "git+https://github.com/acme/newton-fork.git@test-ref"),
    ],
)
def test_install_script_dry_run_matrix(tmp_path: Path, args: tuple[str, ...], expected: str):
    result = run_install_dry_run(*args, path=fake_path(tmp_path, "uv"), cwd=tmp_path)

    assert result.returncode == 0
    assert expected in result.stdout
