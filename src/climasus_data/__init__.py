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

import copy
import hashlib
import json
import os
import warnings
from functools import lru_cache
from pathlib import Path
from typing import Any

__version__ = "0.2.0"

#: Environment variable that turns an integrity warning into an error.
#:
#: Off by default, and that is the decision recorded as M99 (c), taken on
#: 21/09/2026. A checksum that no longer matches is worth saying out loud,
#: but refusing to load turns an inventory problem into a broken package,
#: and the person who feels it is the end user who edited nothing. A
#: warning naming the file gives the information to whoever can act on it
#: without stopping whoever cannot.
#:
#: Set it in CI, where being strict costs nothing and catches a stale
#: manifest before it ships.
STRICT_ENV = "CLIMASUS_DATA_STRICT"

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


def get_path(relative: str, verify: bool = True) -> Path:
    """Return absolute path to a file inside climasus-data.

    Checks the file against ``manifest.json`` on the way out, when the
    manifest lists it: the manifest is a versioned contract consumed by
    both climasus4r and climasus4py, and a contract nobody checks stops
    being one (M99 c). A mismatch **warns** and returns the path anyway;
    set ``CLIMASUS_DATA_STRICT=1`` to make it raise instead. The check
    happens here rather than in :func:`load_json` because parquet files
    are reached through this function and never through that one, and
    doing it in both would report the same problem twice.

    Each file is hashed and reported at most once per process.

    Parameters
    ----------
    relative : str
        Path relative to the data root, e.g. ``"geo/municipios.json"``.
    verify : bool
        Whether to run the integrity check. ``True`` by default. Pass
        ``False`` where the caller is doing its own — the manifest
        generator, for one, which must be able to read a file precisely
        because its checksum is out of date.
    """
    root = data_root().resolve()
    resolved = (root / relative).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(
            f"Path traversal not allowed: {relative!r} resolves outside the data root."
        )
    if verify:
        _report(str(relative).replace("\\", "/"))
    return resolved


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
        return copy.deepcopy(json.load(f))


# ---------------------------------------------------------------------------
# Integrity: the manifest is a contract, so it gets checked (M99 c)
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def manifest() -> dict[str, Any]:
    """The parsed ``manifest.json``.

    Read directly rather than through :func:`load_json` so an integrity
    check can never recurse into itself.
    """
    with open(data_root() / "manifest.json", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _expected_md5() -> dict[str, str]:
    """``path -> md5`` from the manifest, with forward slashes."""
    return {
        str(item["path"]).replace("\\", "/"): str(item["md5"])
        for item in manifest().get("files", [])
        if item.get("path") and item.get("md5")
    }


def file_md5(path: Path, chunk: int = 1 << 20) -> str:
    """MD5 of a file, read in chunks so a large parquet is not loaded whole."""
    h = hashlib.md5()  # noqa: S324 - inventory checksum, not a security control
    with open(path, "rb") as f:
        for bloco in iter(lambda: f.read(chunk), b""):
            h.update(bloco)
    return h.hexdigest()


def _strict() -> bool:
    return os.environ.get(STRICT_ENV, "").strip().lower() not in (
        "", "0", "false", "no")


@lru_cache(maxsize=256)
def _check_file(relative: str) -> str | None:
    """Compare one file against the manifest; report once per file.

    Returns the message when something is off, or ``None``. Cached by
    path so a file loaded in a loop is hashed once and complained about
    once — a warning repeated a thousand times is noise, and noise is
    how a real one gets missed.

    A file the manifest does not list is **not** an error: the manifest
    covers the published data directories, and a caller may legitimately
    reach for something else.
    """
    esperado = _expected_md5().get(relative)
    if esperado is None:
        return None
    caminho = data_root() / relative
    if not caminho.is_file():
        return f"{relative} is listed in manifest.json and is not on disk"
    obtido = file_md5(caminho)
    if obtido == esperado:
        return None
    return (
        f"{relative} does not match manifest.json: expected md5 {esperado}, "
        f"found {obtido}. Either the file changed without the manifest being "
        f"regenerated (run scripts/update_manifest.py) or the copy is "
        f"corrupt."
    )


#: Paths already warned about, so a file read in a loop complains once.
_JA_AVISADO: set[str] = set()


def _report(relative: str) -> None:
    """Warn — or raise under strict mode — when a file fails its checksum.

    Warns **once per path per process**. `_check_file` being cached only
    stops the re-hashing; without this set the warning still fired on
    every access, and a warning repeated a thousand times in a loop is
    how a real one gets missed.

    Strict mode raises every time: an exception is not noise, and
    swallowing the second one would let a caller catch the first and
    carry on unaware.
    """
    problema = _check_file(relative)
    if problema is None:
        return
    if _strict():
        raise ValueError(f"climasus-data integrity: {problema}")
    if relative in _JA_AVISADO:
        return
    _JA_AVISADO.add(relative)
    warnings.warn(f"climasus-data integrity: {problema}", UserWarning,
                  stacklevel=3)


def verify_integrity(
    paths: list[str] | None = None,
) -> dict[str, list[str]]:
    """Check every file the manifest lists, and return what is wrong.

    The bulk counterpart of the per-file check :func:`get_path` does.
    Meant for CI and for a human asking "is this checkout sound?", which
    is why it **returns** the findings instead of only warning: a caller
    that wants to fail a build needs the list.

    Args:
        paths: Only check these, relative to the data root. ``None``
            checks every entry in the manifest.

    Returns:
        ``{"mismatched": [...], "missing": [...], "ok": [...]}`` with
        paths in each bucket.

    Example:
        >>> import climasus_data as cd
        >>> rel = cd.verify_integrity()
        >>> assert not rel["mismatched"] and not rel["missing"]
    """
    alvos = paths if paths is not None else sorted(_expected_md5())
    saida: dict[str, list[str]] = {"mismatched": [], "missing": [], "ok": []}
    for rel in alvos:
        problema = _check_file(rel)
        if problema is None:
            saida["ok"].append(rel)
        elif "not on disk" in problema:
            saida["missing"].append(rel)
        else:
            saida["mismatched"].append(rel)
    return saida
