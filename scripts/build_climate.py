"""Build cached INMET station and observation Parquets."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
FIXTURE_ROOT = ROOT.parent / "fixture_reais"

_COLUMN_MAP = {
    "data": "date",
    "Data": "date",
    "DATA (YYYY-MM-DD)": "date",
    "precipitacao": "precipitation",
    "PRECIPITACAO TOTAL, HORARIO (mm)": "precipitation",
    "TEMPERATURA DO AR - BULBO SECO, HORARIA (C)": "temp_mean",
    "TEMPERATURA MAXIMA NA HORA ANT. (AUT) (C)": "temp_max",
    "TEMPERATURA MINIMA NA HORA ANT. (AUT) (C)": "temp_min",
    "UMIDADE RELATIVA DO AR, HORARIA (%)": "humidity",
    "PRESSAO ATMOSFERICA AO NIVEL DA ESTACAO, HORARIA (mB)": "pressure",
    "VENTO, VELOCIDADE HORARIA (m/s)": "wind_speed",
    "RADIACAO GLOBAL (Kj/m2)": "radiation",
}

_OBS_COLUMNS = [
    "station_id",
    "date",
    "temp_mean",
    "temp_max",
    "temp_min",
    "precipitation",
    "humidity",
    "pressure",
    "wind_speed",
    "radiation",
]


def build_observations(csv_paths: list[str | Path], *, year: int) -> None:
    """Build observation asset from already-downloaded INMET CSV files."""
    frames = []
    for path in csv_paths:
        df = pd.read_csv(path, sep=";", decimal=",", encoding="latin1", skip_blank_lines=True)
        df = df.rename(columns={col: _COLUMN_MAP.get(col, col) for col in df.columns})
        if "station_id" not in df.columns:
            df["station_id"] = _station_id_from_filename(path)
        df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
        for col in _OBS_COLUMNS:
            if col not in df.columns:
                df[col] = pd.NA
        frames.append(df[_OBS_COLUMNS])

    out = _daily_observations(pd.concat(frames, ignore_index=True))
    out_dir = ASSETS / "climate"
    out_dir.mkdir(parents=True, exist_ok=True)
    out.to_parquet(out_dir / f"inmet_observations_{year}.parquet", compression="snappy", index=False)


def build_stations(stations_csv: str | Path) -> None:
    """Build station asset from a normalized station CSV."""
    df = pd.read_csv(stations_csv)
    columns = {
        "station_id": "station_id",
        "name": "name",
        "state": "state",
        "lat": "lat",
        "lon": "lon",
        "elevation": "elevation",
        "start_date": "start_date",
        "end_date": "end_date",
    }
    missing = [col for col in columns if col not in df.columns]
    if missing:
        raise ValueError(f"Station CSV missing columns: {', '.join(missing)}")
    out_dir = ASSETS / "climate"
    out_dir.mkdir(parents=True, exist_ok=True)
    df[list(columns)].to_parquet(out_dir / "inmet_stations.parquet", compression="snappy", index=False)


def build_observations_from_climasus4r(parquet_path: str | Path, *, year: int) -> None:
    """Build observation asset from climasus4r INMET fixture output."""
    df = pd.read_parquet(parquet_path)
    out = pd.DataFrame(
        {
            "station_id": df["station_code"].astype(str),
            "date": pd.to_datetime(df["date"], errors="coerce").dt.date,
            "temp_mean": pd.to_numeric(df.get("tair_dry_bulb_c"), errors="coerce"),
            "temp_max": pd.to_numeric(df.get("tair_max_c"), errors="coerce"),
            "temp_min": pd.to_numeric(df.get("tair_min_c"), errors="coerce"),
            "precipitation": pd.to_numeric(df.get("rainfall_mm"), errors="coerce"),
            "humidity": pd.to_numeric(df.get("rh_mean_porc"), errors="coerce"),
            "pressure": pd.to_numeric(df.get("patm_mb"), errors="coerce"),
            "wind_speed": pd.to_numeric(df.get("ws_2_m_s"), errors="coerce"),
            "radiation": pd.to_numeric(df.get("sr_kj_m2"), errors="coerce"),
        }
    )
    out = _daily_observations(out)
    out_dir = ASSETS / "climate"
    out_dir.mkdir(parents=True, exist_ok=True)
    out.to_parquet(out_dir / f"inmet_observations_{year}.parquet", compression="snappy", index=False)


def build_stations_from_climasus4r(parquet_path: str | Path) -> None:
    """Build station asset from climasus4r station metadata fixture."""
    df = pd.read_parquet(parquet_path)
    out = pd.DataFrame(
        {
            "station_id": df["station_code"].astype(str),
            "name": df["station_name"].astype(str),
            "state": df["federal_unit"].astype(str),
            "lat": pd.to_numeric(df["latitude"], errors="coerce"),
            "lon": pd.to_numeric(df["longitude"], errors="coerce"),
            "elevation": pd.to_numeric(df["altitude"], errors="coerce"),
            "start_date": pd.to_datetime(df["foundation_date"], errors="coerce").dt.date,
            "end_date": pd.NaT,
        }
    )
    out_dir = ASSETS / "climate"
    out_dir.mkdir(parents=True, exist_ok=True)
    out.to_parquet(out_dir / "inmet_stations.parquet", compression="snappy", index=False)


def _station_id_from_filename(path: str | Path) -> str:
    return Path(path).stem.split("_")[0]


def _daily_observations(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate hourly observations to one row per station/date."""
    aggregations = {
        "temp_mean": "mean",
        "temp_max": "max",
        "temp_min": "min",
        "precipitation": "sum",
        "humidity": "mean",
        "pressure": "mean",
        "wind_speed": "mean",
        "radiation": "sum",
    }
    out = (
        df.groupby(["station_id", "date"], dropna=True, as_index=False)
        .agg(aggregations)
        .reindex(columns=_OBS_COLUMNS)
    )
    return out


if __name__ == "__main__":
    fixture_climate_dir = FIXTURE_ROOT / "climate"
    fixture_stations = FIXTURE_ROOT / "metadata" / "station_meta.parquet"

    obs_fixtures = sorted(fixture_climate_dir.glob("*.parquet")) if fixture_climate_dir.is_dir() else []

    if not obs_fixtures:
        raise SystemExit(
            "No fixture parquet files found in fixture_reais/climate/. "
            "Import this module and call build_observations() with explicit source files, "
            "or add INMET parquet fixtures to fixture_reais/climate/."
        )

    # Determine which years are covered by the available fixtures
    import re
    year_pattern = re.compile(r"(\d{4})")
    years_seen: set[int] = set()
    all_frames: list = []
    import pandas as _pd
    for fixture_path in obs_fixtures:
        match = year_pattern.search(fixture_path.stem)
        year = int(match.group(1)) if match else 2023
        df = _pd.read_parquet(fixture_path)
        out = _pd.DataFrame(
            {
                "station_id": df["station_code"].astype(str),
                "date": _pd.to_datetime(df["date"], errors="coerce").dt.date,
                "temp_mean": _pd.to_numeric(df.get("tair_dry_bulb_c"), errors="coerce"),
                "temp_max": _pd.to_numeric(df.get("tair_max_c"), errors="coerce"),
                "temp_min": _pd.to_numeric(df.get("tair_min_c"), errors="coerce"),
                "precipitation": _pd.to_numeric(df.get("rainfall_mm"), errors="coerce"),
                "humidity": _pd.to_numeric(df.get("rh_mean_porc"), errors="coerce"),
                "pressure": _pd.to_numeric(df.get("patm_mb"), errors="coerce"),
                "wind_speed": _pd.to_numeric(df.get("ws_2_m_s"), errors="coerce"),
                "radiation": _pd.to_numeric(df.get("sr_kj_m2"), errors="coerce"),
            }
        )
        all_frames.append((year, out))
        years_seen.add(year)

    # Write one Parquet per year (aggregating all stations for that year)
    for year in sorted(years_seen):
        year_frames = [frame for y, frame in all_frames if y == year]
        combined = _pd.concat(year_frames, ignore_index=True)
        combined = _daily_observations(combined)
        out_dir = ASSETS / "climate"
        out_dir.mkdir(parents=True, exist_ok=True)
        combined.to_parquet(out_dir / f"inmet_observations_{year}.parquet", compression="snappy", index=False)
        print(f"  [{year}] {len(combined['station_id'].unique())} estações, {len(combined)} linhas")

    if fixture_stations.is_file():
        build_stations_from_climasus4r(fixture_stations)
        print(f"  Estações: {fixture_stations}")
    else:
        print("  Aviso: station_meta.parquet não encontrado em fixture_reais/metadata/ — inmet_stations.parquet não gerado.")
