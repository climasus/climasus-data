"""Build assets/climate/inmet_station_meta.parquet from the R package's table.

Provenance
----------
climasus4r's ``get_spatial_station_cache()`` downloads

    https://github.com/ByMaxAnjos/climasus4r/raw/refs/heads/master/inst/data_4r/station_meta.parquet

and caches it under ``~/.climasus4r_cache/spatial/station_meta.parquet``. It
then joins the table onto the output of
``sus_climate_compute_indicators()``, which is where thirteen of that
function's sixty default columns come from - the station's identity plus
five climate classifications. Nothing in ``climasus-data`` carried them, so
climasus4py could not produce them at all.

This script converts that table into the shape climasus4py reads. Point it
at a local copy:

    python scripts/build_inmet_station_meta.py path/to/station_meta.parquet

Two changes on the way, both deliberate
---------------------------------------
**Geometry dropped.** R calls ``sf::st_drop_geometry()`` before joining, so
the column never reaches the output.

**One row per station.** The source has 636 rows for 609 stations: 26 codes
appear twice, and none of the 26 pairs is a duplicate - every one disagrees
about ``zona_climatica`` and ``id_link``, and 8 of them also about
``tipo_umidade``, ``distr_umidade``, ``temperatura_id`` and ``descricao``.
The identity columns never disagree.

The shape of the disagreement says what happened: the pairs split between a
land class and ``Massa d'agua`` or ``Zona Economica Exclusiva``, and all 18
of the stations whose *both* candidates are water sit on the coast or
offshore - SALINOPOLIS (PA), JOAO PESSOA (PB), CALCANHAR (RN), and
ARQ. SAO PEDRO E SAO PAULO, which really is in the middle of the Atlantic.
These are points falling on the boundary of the climate polygons, so the
spatial join emitted one row per polygon.

Left as-is, that join **multiplies observation rows**. Measured in R: 100
rows of input for station A134 come back as 200, and any count, mean or sum
over those 26 stations is silently doubled. See M107.

So the table is collapsed to one row per station by a rule with no judgement
in it: **where the source agrees, keep the value; where it contradicts
itself, write null.** Identity survives for every station; the 26 lose only
the fields their own source could not agree on. Picking a side would mean
asserting that a land station sits in a water body - or, for the
archipelago, that it does not.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SAIDA = ROOT / "assets" / "climate" / "inmet_station_meta.parquet"

# every column climasus4r joins onto the indicator output, in its order
COLUNAS = [
    "station_code", "region", "federal_unit", "station_name",
    "latitude", "longitude", "altitude", "foundation_date", "id_link",
    "zona_climatica", "tipo_umidade", "distr_umidade", "temperatura_id",
    "descricao",
]


def collapse(df: pd.DataFrame) -> pd.DataFrame:
    """One row per station_code; contradictory fields become null."""
    def resolve(serie: pd.Series):
        distintos = serie.dropna().unique()
        if len(distintos) == 1:
            return distintos[0]
        if len(distintos) == 0:
            return None
        return None  # the source disagrees: we do not know

    return (df.groupby("station_code", as_index=False, sort=True)
              .agg({c: resolve for c in COLUNAS if c != "station_code"}))


def main(origem: Path) -> None:
    bruto = pd.read_parquet(origem)
    if "geometry" in bruto.columns:
        bruto = bruto.drop(columns=["geometry"])
    faltando = [c for c in COLUNAS if c not in bruto.columns]
    if faltando:
        raise SystemExit(f"a origem nao tem as colunas {faltando}")
    bruto = bruto[COLUNAS]

    dup = bruto["station_code"].duplicated(keep=False)
    saida = collapse(bruto)

    print(f"origem : {len(bruto)} linhas, {bruto['station_code'].nunique()} estacoes")
    print(f"         {int(dup.sum())} linhas com codigo repetido")
    print(f"saida  : {len(saida)} linhas")
    nulos = {c: int(saida[c].isna().sum()) for c in COLUNAS
             if saida[c].isna().any()}
    print(f"nulos por contradicao da fonte: {nulos}")
    assert saida["station_code"].is_unique, "sobrou codigo repetido"
    assert len(saida) == bruto["station_code"].nunique()
    for c in ("region", "federal_unit", "station_name", "latitude", "longitude"):
        assert not saida[c].isna().any(), f"{c} perdeu valor, e nao devia"

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    saida.to_parquet(SAIDA, index=False)
    print(f"escrito: {SAIDA.relative_to(ROOT).as_posix()} "
          f"({SAIDA.stat().st_size:,} bytes)")
    print("rode scripts/update_manifest.py para registrar o checksum")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__.strip().splitlines()[0] +
                         "\n\nuso: build_inmet_station_meta.py <station_meta.parquet>")
    main(Path(sys.argv[1]))
