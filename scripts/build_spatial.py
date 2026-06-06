"""Build cached Brazilian geometries as WKT Parquet files.

Offline release script. Runtime packages must read the generated Parquets
instead of importing geobr.
"""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"


def _code_as_string(series: pd.Series) -> pd.Series:
    """Normalize geobr numeric codes without a trailing .0."""
    numeric = pd.to_numeric(series, errors="coerce").astype("Int64")
    return numeric.astype(str)


def _region_slug(value: object) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.lower().replace("-", "_").replace(" ", "_")


def _state_region_map() -> dict[str, str]:
    regions = json.loads((ROOT / "metadata" / "regions.json").read_text(encoding="utf-8"))
    mapping: dict[str, str] = {}
    ibge_macro = regions.get("categories", {}).get("ibge_macro", {})
    for region_slug, region_data in ibge_macro.get("regions", {}).items():
        for state in region_data.get("states", []):
            mapping[str(state)] = str(region_slug)
    return mapping


def _state_code_map() -> dict[int, str]:
    states = json.loads((ROOT / "metadata" / "uf_codes.json").read_text(encoding="utf-8"))
    return {int(meta["code"]): uf for uf, meta in states.get("states", {}).items()}


def _local_municipalities(state_region: dict[str, str]) -> pd.DataFrame:
    data = json.loads((ROOT / "geo" / "municipios.json").read_text(encoding="utf-8-sig"))
    state_codes = _state_code_map()
    rows = []
    for item in data:
        state = state_codes.get(int(item["codigo_uf"]))
        rows.append(
            {
                "code_muni": str(int(item["geocodigo"])),
                "name": str(item["municipio"]),
                "geometry_wkt": f"POINT ({float(item['longitude'])} {float(item['latitude'])})",
                "state": state,
                "region": state_region.get(state or ""),
            }
        )
    return pd.DataFrame(rows)


def _to_wkt_frame(
    gdf,
    *,
    code_col: str,
    name_col: str,
    out_code: str,
    state_region: dict[str, str] | None = None,
) -> pd.DataFrame:
    df = pd.DataFrame(
        {
            out_code: _code_as_string(gdf[code_col]),
            "name": gdf[name_col].astype(str),
            "geometry_wkt": gdf.geometry.map(lambda geom: geom.wkt if geom is not None else None),
        }
    )
    if "abbrev_state" in gdf.columns:
        df["state"] = gdf["abbrev_state"].astype(str)
        if state_region is not None:
            df["region"] = df["state"].map(state_region)
    if "name_region" in gdf.columns:
        df["region"] = gdf["name_region"].map(_region_slug)
    return df


def build() -> None:
    import geobr

    out_dir = ASSETS / "spatial"
    out_dir.mkdir(parents=True, exist_ok=True)
    state_region = _state_region_map()

    municipalities = geobr.read_municipality(simplified=False)
    municipalities_df = _to_wkt_frame(
        municipalities,
        code_col="code_muni",
        name_col="name_muni",
        out_code="code_muni",
        state_region=state_region,
    )
    local_municipalities = _local_municipalities(state_region)
    local_codes = set(local_municipalities["code_muni"])
    municipalities_df = municipalities_df[municipalities_df["code_muni"].isin(local_codes)]
    missing = local_municipalities[
        ~local_municipalities["code_muni"].isin(municipalities_df["code_muni"])
    ]
    municipalities_df = pd.concat([municipalities_df, missing], ignore_index=True).sort_values(
        "code_muni"
    )
    municipalities_df.to_parquet(
        out_dir / "municipalities.parquet", compression="snappy", index=False
    )

    states = geobr.read_state(simplified=False)
    states_df = _to_wkt_frame(
        states,
        code_col="code_state",
        name_col="name_state",
        out_code="code_state",
    )
    states_df["state"] = states["abbrev_state"].astype(str)
    states_df["region"] = states_df["state"].map(state_region)
    states_df.to_parquet(out_dir / "states.parquet", compression="snappy", index=False)

    regions = geobr.read_region(simplified=False)
    regions_df = _to_wkt_frame(
        regions,
        code_col="code_region",
        name_col="name_region",
        out_code="code_region",
    )
    regions_df["region"] = regions["name_region"].map(_region_slug)
    regions_df.to_parquet(out_dir / "regions.parquet", compression="snappy", index=False)


if __name__ == "__main__":
    build()
