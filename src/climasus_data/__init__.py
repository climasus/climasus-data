"""climasus-data: shared metadata catalog for climasus4r and climasus4py.

Provides access to dictionaries, disease groups, geo data, and metadata
JSON files used by both R and Python climasus packages.

Usage::

    import climasus_data

    # Get a Path to a data file
    path = climasus_data.get_path("geo/municipios.json")

    # Load a JSON file directly
    data = climasus_data.load_json("metadata/datasus_systems.json")

    # Get the root data directory
    root = climasus_data.data_root()
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

__version__ = "0.1.5"

# ---------------------------------------------------------------------------
# Data root resolution
# ---------------------------------------------------------------------------

_DATA_ROOT: Path | None = None


def _find_data_root() -> Path:
    """Locate the data files directory.

    When installed as a wheel, data files are alongside __init__.py
    (via hatch force-include). In editable/dev mode, they live at the
    repo root (parent of src/).
    """
    pkg_dir = Path(__file__).resolve().parent

    # 1. Installed wheel: manifest.json is next to __init__.py
    if (pkg_dir / "manifest.json").is_file():
        return pkg_dir

    # 2. Editable install / dev: walk up to find manifest.json at repo root
    for parent in pkg_dir.parents:
        if (parent / "manifest.json").is_file():
            return parent

    raise FileNotFoundError(
        "climasus-data files not found. Ensure the package is installed correctly "
        "or that manifest.json exists in the repository root."
    )


def data_root() -> Path:
    """Return the root directory containing climasus-data files."""
    global _DATA_ROOT
    if _DATA_ROOT is None:
        _DATA_ROOT = _find_data_root()
    return _DATA_ROOT


def get_path(relative: str) -> Path:
    """Return absolute path to a file inside climasus-data.

    Parameters
    ----------
    relative : str
        Path relative to the data root, e.g. ``"geo/municipios.json"``.
    """
    return data_root() / relative


@lru_cache(maxsize=32)
def load_json(relative: str) -> Any:
    """Load and cache a JSON file from climasus-data.

    Parameters
    ----------
    relative : str
        Path relative to the data root, e.g. ``"metadata/datasus_systems.json"``.
    """
    path = get_path(relative)
    if not path.is_file():
        raise FileNotFoundError(
            f"File not found in climasus-data: {relative}\n"
            f"Expected at: {path}\n"
            "Ensure the package is installed correctly and up to date."
        )
    with open(path, encoding="utf-8") as f:
        return json.load(f)
