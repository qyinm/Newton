from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from newton.scenario_loader import load_scenario


class PlanningError(RuntimeError):
    """Raised when markdown context cannot be converted to a scenario."""


def plan_scenario_from_markdown(
    input_path: Path,
    target: str,
    out_dir: Path,
    base_url: str = "http://127.0.0.1:8000",
) -> Path:
    if not input_path.exists():
        raise PlanningError(f"input markdown not found: {input_path}")

    markdown = input_path.read_text()
    title = _extract_title(markdown)
    scenario_id = f"{_slugify(title)}-smoke"
    platforms = _parse_targets(target)
    scenario = _build_login_smoke_scenario(
        title=title,
        scenario_id=scenario_id,
        source_ref=str(input_path),
        platforms=platforms,
        base_url=base_url,
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / f"{scenario_id}.generated.yaml"
    output_path.write_text(yaml.safe_dump(scenario, sort_keys=False))

    # Self-validate the generated YAML so qa plan never emits an invalid Newton scenario.
    load_scenario(output_path)
    return output_path


def _extract_title(markdown: str) -> str:
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            title = stripped.lstrip("#").strip()
            if title:
                return title
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:80]
    raise PlanningError("input markdown is empty")


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "scenario"


def _parse_targets(target: str) -> list[str]:
    platforms = [item.strip() for item in target.split(",") if item.strip()]
    if not platforms:
        raise PlanningError("--target must include at least one platform")
    unsupported = sorted(set(platforms) - {"web", "ios"})
    if unsupported:
        raise PlanningError(f"unsupported planning target(s): {', '.join(unsupported)}")
    return platforms


def _build_login_smoke_scenario(
    title: str,
    scenario_id: str,
    source_ref: str,
    platforms: list[str],
    base_url: str,
) -> dict[str, Any]:
    return {
        "scenario": {
            "id": scenario_id,
            "title": f"{title} smoke",
            "source_refs": [source_ref],
            "risk_category": "functional",
            "priority": "P0",
            "environments": ["local"],
        },
        "targets": [_target(platform, base_url) for platform in platforms],
        "steps": _login_steps(platforms),
        "evidence": {
            "screenshots": "on_failure",
            "video": False,
            "logs": True,
            "traces": True,
        },
    }


def _target(platform: str, base_url: str) -> dict[str, Any]:
    if platform == "web":
        return {
            "id": "web",
            "platform": "web",
            "backend": "playwright",
            "base_url": base_url,
        }
    if platform == "ios":
        return {
            "id": "ios",
            "platform": "ios",
            "backend": "maestro",
            "bundle_id": "com.example.app",
            "device": {"model": "iPhone 15"},
        }
    raise PlanningError(f"unsupported platform: {platform}")


def _login_steps(platforms: list[str]) -> list[dict[str, Any]]:
    return [
        _step(
            platforms,
            step_id="open-login",
            action="navigate",
            web={"url": "/login.html"},
            ios={"deep_link": "newton://login"},
        ),
        _step(
            platforms,
            step_id="enter-email",
            action="input_text",
            value="qa@example.com",
            web={"role": "textbox", "name": "Email"},
            ios={"accessibility_id": "emailInput"},
        ),
        _step(
            platforms,
            step_id="enter-password",
            action="input_text",
            value="password123",
            secure=True,
            web={"test_id": "password-input"},
            ios={"accessibility_id": "passwordInput"},
        ),
        _step(
            platforms,
            step_id="submit",
            action="tap",
            web={"role": "button", "name": "Log in"},
            ios={"accessibility_id": "loginButton"},
        ),
        _step(
            platforms,
            step_id="assert-dashboard",
            action="assert_visible",
            web={"text": "Dashboard"},
            ios={"text": "Dashboard"},
        ),
    ]


def _step(
    platforms: list[str],
    *,
    step_id: str,
    action: str,
    web: dict[str, Any],
    ios: dict[str, Any],
    value: str | None = None,
    secure: bool = False,
) -> dict[str, Any]:
    target: dict[str, Any] = {}
    if "web" in platforms:
        target["web"] = web
    if "ios" in platforms:
        target["ios"] = ios

    step: dict[str, Any] = {
        "id": step_id,
        "action": action,
        "target": target,
    }
    if value is not None:
        step["value"] = value
    if secure:
        step["secure"] = True
    return step
