"""Precompute municipality-to-INMET station IDW weights."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"


def build(top_k: int = 3, power: float = 2.0) -> None:
    from scipy.spatial import cKDTree
    from shapely import wkt

    municipalities = pd.read_parquet(ASSETS / "spatial" / "municipalities.parquet")
    stations = pd.read_parquet(ASSETS / "climate" / "inmet_stations.parquet")
    observed_station_ids = _observed_station_ids()
    if observed_station_ids:
        stations = stations[stations["station_id"].astype(str).isin(observed_station_ids)].reset_index(drop=True).copy()
    if stations.empty:
        raise ValueError("No INMET stations available for IDW weight generation.")

    centroids = municipalities["geometry_wkt"].map(lambda value: wkt.loads(value).centroid)
    muni_xy = np.array([[geom.y, geom.x] for geom in centroids], dtype=float)
    k = min(top_k, len(stations))
    station_xy = stations[["lat", "lon"]].to_numpy(dtype=float)
    tree = cKDTree(station_xy)

    rows = []
    for municipality_code, xy in zip(municipalities["code_muni"].astype(str), muni_xy, strict=False):
        distances, indices = tree.query(xy, k=k)
        distances = np.maximum(np.atleast_1d(distances), 1e-9)
        indices = np.atleast_1d(indices)
        raw = 1.0 / (distances**power)
        weights = raw / raw.sum()
        for idx, weight in zip(indices, weights, strict=False):
            rows.append(
                {
                    "municipality_code": municipality_code,
                    "station_id": str(stations.iloc[int(idx)]["station_id"]),
                    "weight": float(weight),
                }
            )

    out_dir = ASSETS / "climate"
    out_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(
        out_dir / "idw_weights_municipality.parquet",
        compression="snappy",
        index=False,
    )

def _observed_station_ids() -> set[str]:
    paths = sorted((ASSETS / "climate").glob("inmet_observations_*.parquet"))
    if not paths:
        return set()
    ids: set[str] = set()
    for path in paths:
        frame = pd.read_parquet(path, columns=["station_id"])
        ids.update(frame["station_id"].dropna().astype(str).unique())
    return ids


if __name__ == "__main__":
    build()
