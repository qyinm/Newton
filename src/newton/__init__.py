from importlib.metadata import PackageNotFoundError, version as _package_version
from pathlib import Path
import tomllib


def _read_version() -> str:
    try:
        return _package_version("newton-qa")
    except PackageNotFoundError:
        pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
        return tomllib.loads(pyproject_path.read_text())["project"]["version"]


__version__ = _read_version()
