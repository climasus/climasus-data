"""Update climasus-data manifest entries for generated parquet assets."""

from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]


def file_md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parquet_rows(path: Path) -> int:
    return pq.ParquetFile(path).metadata.num_rows


def _package_version() -> str:
    """Read version from pyproject.toml to avoid hardcoding."""
    import tomllib  # stdlib >= 3.11; falls back to tomli on 3.10
    try:
        pyproject = ROOT / "pyproject.toml"
        with open(pyproject, "rb") as f:
            return tomllib.load(f)["project"]["version"]
    except Exception:
        return "unknown"


def update_manifest(version: str | None = None) -> None:
    if version is None:
        version = _package_version()
    manifest_path = ROOT / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    existing = {
        item["path"]: item
        for item in manifest.get("files", [])
        if not item["path"].endswith(".parquet") and (ROOT / item["path"]).is_file()
    }

    for path in sorted((ROOT / "assets").rglob("*.parquet")):
        rel = path.relative_to(ROOT).as_posix()
        existing[rel] = {
            "path": rel,
            "size_bytes": path.stat().st_size,
            "md5": file_md5(path),
            "rows": parquet_rows(path),
        }

    manifest["version"] = version
    manifest["last_updated"] = datetime.date.today().isoformat()
    manifest["files"] = [existing[key] for key in sorted(existing)]
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    update_manifest()
