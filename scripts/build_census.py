"""Build cached municipal census/indicator Parquets."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
FIXTURE_ROOT = ROOT.parent / "fixture_reais"


def build(year: int = 2022) -> None:
    """Build municipal indicators from censobr when available."""
    import censobr

    population = censobr.read_population(year=year, geo="municipality")
    population = population.rename(columns={"code_muni": "municipality_code"})
    population["municipality_code"] = population["municipality_code"].astype(str)

    frames = [population]
    for loader_name in ("read_household_income",):
        loader = getattr(censobr, loader_name, None)
        if loader is None:
            continue
        frame = loader(year=year, geo="municipality").rename(
            columns={"code_muni": "municipality_code"}
        )
        frame["municipality_code"] = frame["municipality_code"].astype(str)
        frames.append(frame)

    out = frames[0]
    for frame in frames[1:]:
        out = out.merge(frame, on="municipality_code", how="outer")

    out_dir = ASSETS / "census"
    out_dir.mkdir(parents=True, exist_ok=True)
    out.to_parquet(out_dir / f"census_{year}.parquet", compression="snappy", index=False)


def build_from_municipio_meta(parquet_path: str | Path, *, year: int = 2022) -> None:
    """Build a municipal indicators asset from climasus4r municipio metadata."""
    df = pd.read_parquet(parquet_path)
    out = pd.DataFrame(
        {
            "municipality_code": df["municipio"].astype(str),
            "municipality_name": df["name"].astype(str),
            "state_code": df["uf_code"].astype(str),
            "is_capital": df["is_capital"],
            "population_2021": pd.to_numeric(df["pop_21"], errors="coerce").astype("Int64"),
            "population_2025": pd.to_numeric(df["pop_25"], errors="coerce").astype("Int64"),
            "latitude": pd.to_numeric(df["lat"], errors="coerce"),
            "longitude": pd.to_numeric(df["lon"], errors="coerce"),
        }
    )
    out_dir = ASSETS / "census"
    out_dir.mkdir(parents=True, exist_ok=True)
    out.to_parquet(out_dir / f"census_{year}.parquet", compression="snappy", index=False)


if __name__ == "__main__":
    fixture = FIXTURE_ROOT / "metadata" / "municipio_meta.parquet"
    if fixture.is_file():
        build_from_municipio_meta(fixture)
    else:
        build()
