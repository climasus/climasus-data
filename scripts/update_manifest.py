"""Update the climasus-data manifest: checksums for every file it lists.

Before 2026-09-16 this script recomputed the MD5 of the eight parquet assets
only. The thirty JSON entries were copied forward from the previous manifest
verbatim, md5 included, and the last line stamped ``last_updated`` with today's
date - so every JSON entry carried the hash it was first written with while the
file claimed to be current. Measured at that point: 11 of 38 checksums stale,
oldest from May, against a ``last_updated`` of the day before.

It also never *added* a JSON file, only preserved what was already listed,
which is why both pt-pt dictionaries had never been in the inventory while
their pt-en and pt-es siblings were.

Now every listed file is hashed, and JSON files found under DATA_DIRS are added
if missing. ``rows`` is recomputed for parquet and otherwise preserved when
present - fifteen entries carry it and fifteen do not, so it is never invented.
"""

from __future__ import annotations

import datetime
import hashlib
import json
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]

# Directories the inventory covers. Scanned for JSON files to add.
#
# `viz/` came in on 21/09/2026 (D7). It used to be left out as a scope
# decision rather than a missing checksum, because the manifest held no
# entry for it at all. The decision was settled by looking at who reads
# it: `climasus4py/viz/plot_aggregate_map.py` and `plot_aggregate_ts.py`
# both load `viz/viz_labels.json` and `viz/viz_config.json` at run time.
# They are consumed data, not scratch files, so leaving them out meant two
# files the package reads were outside the integrity contract — which is
# exactly the gap M99 (c) is about.
DATA_DIRS = ("assets", "dictionaries", "disease_groups", "geo", "metadata",
             "templates", "viz")


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


def _entry(rel: str, anterior: dict | None) -> dict:
    """Fresh entry for one file: size and md5 always recomputed.

    ``rows`` comes from the parquet metadata for parquet, and is carried over
    for anything else only when the previous entry had it. Fifteen JSON entries
    carry a variable count and fifteen do not, so there is no convention to
    infer - inventing one would put a made-up number next to a real checksum.
    """
    path = ROOT / rel
    entry = {
        "path": rel,
        "size_bytes": path.stat().st_size,
        "md5": file_md5(path),
    }
    if rel.endswith(".parquet"):
        entry["rows"] = parquet_rows(path)
    elif anterior is not None and "rows" in anterior:
        entry["rows"] = anterior["rows"]
    return entry


def update_manifest(version: str | None = None, verbose: bool = True) -> dict:
    if version is None:
        version = _package_version()
    manifest_path = ROOT / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    anteriores = {item["path"]: item for item in manifest.get("files", [])}

    # everything the manifest lists and that still exists, plus every JSON and
    # parquet under DATA_DIRS - so a new data file cannot stay invisible
    caminhos = {p for p in anteriores if (ROOT / p).is_file()}
    for base in DATA_DIRS:
        for padrao in ("*.json", "*.parquet"):
            caminhos |= {p.relative_to(ROOT).as_posix()
                         for p in (ROOT / base).rglob(padrao)}

    sumidos = sorted(set(anteriores) - caminhos)
    novos = sorted(caminhos - set(anteriores))
    entradas = {rel: _entry(rel, anteriores.get(rel)) for rel in sorted(caminhos)}
    mudados = sorted(rel for rel, e in entradas.items()
                     if rel in anteriores and e["md5"] != anteriores[rel].get("md5"))

    manifest["version"] = version
    manifest["last_updated"] = datetime.date.today().isoformat()
    manifest["files"] = [entradas[key] for key in sorted(entradas)]
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    resumo = {"total": len(entradas), "md5_corrigido": mudados,
              "acrescentados": novos, "removidos": sumidos}
    if verbose:
        print(f"manifest: {len(entradas)} arquivos")
        for rotulo, lista in (("md5 corrigido", mudados),
                              ("acrescentado", novos),
                              ("removido (nao existe mais)", sumidos)):
            print(f"  {rotulo}: {len(lista)}")
            for rel in lista:
                print(f"      {rel}")
    return resumo


if __name__ == "__main__":
    update_manifest()
