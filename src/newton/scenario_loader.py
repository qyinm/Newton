from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from newton.models import Scenario


class ScenarioLoadError(RuntimeError):
    """Raised when a scenario file cannot be loaded or validated."""


def load_scenario(path: Path) -> Scenario:
    if not path.exists():
        raise ScenarioLoadError(f"scenario file not found: {path}")

    try:
        raw: Any = yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        raise ScenarioLoadError(f"invalid yaml in {path}: {exc}") from exc

    if raw is None:
        raise ScenarioLoadError(f"scenario file is empty: {path}")

    try:
        return Scenario.model_validate(raw)
    except ValidationError as exc:
        raise ScenarioLoadError(f"invalid scenario {path}: {exc}") from exc
