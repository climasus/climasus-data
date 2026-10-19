"""Build the municipal census Parquet from censobr microdata.

Offline release script, in the mould of ``build_spatial.py``: it runs
once when the data package is prepared, and the runtime packages read
the Parquet it writes instead of downloading 672 MB.

**Why this exists.** ``assets/census/census_2010.parquet`` was generated
data — ``runif()`` with ``seed=2010``, not the IBGE Census. The proof
needs no inside knowledge: São Paulo **capital** appeared with
``pct_urban = 0.3265`` when the capital is 100% urban by definition, and
its ``income_per_capita`` came out at exactly 100.0, the minimum of the
file's range. The three proportions all stopped at 0.990 and the national
distribution of ``pct_urban`` was uniform between 0.1 and 0.99 (M139).

That file was also the **only** vintage with socioeconomic columns — the
2022 one carries population and coordinates — so every socioeconomic
indicator computable from Python came from invented numbers.

**The source.** ``climasus4r::sus_census_join`` gets its data from
**censobr** (IPEA), which downloads Parquet files from a public GitHub
release and caches them. There is nothing R-specific in the format: the
file reads from DuckDB directly, verified at 251 columns and 20,635,472
person-level rows. This script aggregates that microdata to municipality
level, producing the **same 34 variables the R produces, under the same
names**, so the two sides stay comparable column by column (M140).

**Separate from build_census.py on purpose.** That script builds the
**2022** vintage from climasus4r's municipio metadata
(build_from_municipio_meta), which is what produces
municipality_name, is_capital, latitude and longitude.
It is still the right script for that vintage and is left untouched —
this one only builds 2010, from a different source and with a different
schema.

Usage::

    python scripts/build_census_2010.py                 # uses the censobr cache
    python scripts/build_census_2010.py --download      # fetches if absent
    python scripts/build_census_2010.py --keep-synthetic

Run ``scripts/update_manifest.py`` afterwards.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import urllib.request
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DESTINO = ROOT / "assets" / "census"

#: Where censobr keeps what it downloads. Reused when present so the
#: release build does not re-fetch 672 MB that is already on disk.
CACHE_CENSOBR = (
    Path.home() / "Documents" / ".climasus4r_cache" / "census"
    / "data_release_v0.5.0"
)
ARQUIVO = "2010_population_v0.5.0.parquet"
URL = (
    "https://github.com/ipeaGIT/censobr/releases/download/"
    f"data_release_v0.5.0/{ARQUIVO}"
)

#: censobr code → the name ``climasus4r`` gives the aggregate, minus the
#: ``_sum`` suffix it appends. Extracted from the R's own catalogue
#: (``sus_census_select``, 304 variables) matched against the 34 columns
#: its ``sus_census_join`` actually emits — all 34 resolved, none guessed.
VARIAVEIS: dict[str, str] = {
    "V0300": "control",
    "V0010": "sample_weight",
    "V6033": "calculated_age_years_months",
    "V6036": "calculated_age_years",
    "V6037": "calculated_age_months",
    "V6511": "main_job_gross_income_value",
    "V6513": "main_job_income",
    "V6514": "main_job_income_minimum_wages",
    "V6521": "other_jobs_gross_income_value",
    "V6524": "other_jobs_income_minimum_wages",
    "V6525": "all_jobs_income",
    "V6526": "all_jobs_income_minimum_wages",
    "V6527": "total_monthly_income_july_2010",
    "V6528": "total_monthly_income_minimum_wages",
    "V6529": "household_income_july_2010",
    "V6530": "household_income_minimum_wages",
    "V6531": "household_income_per_capita",
    "V6532": "household_income_per_capita_minimum_wages",
    "V0653": "weekly_work_hours",
    "V6591": "total_other_income_value",
    "V6631": "how_many_sons_born_alive",
    "V6632": "how_many_daughters_born_alive",
    "V6633": "total_children_born_alive",
    "V6641": "how_many_sons_alive",
    "V6642": "how_many_daughters_alive",
    "V6643": "total_children_alive",
    "V6660": "last_child_age",
    "V6691": "how_many_sons_stillborn",
    "V6692": "how_many_daughters_stillborn",
    "V6693": "total_children_stillborn",
    "V6800": "total_children_born_alive_stillborn",
    "V5060": "number_people_family",
    "V5070": "family_income_per_capita",
    "V5080": "family_income_per_capita_minimum_wages",
}

#: Carried through unaggregated — censobr already has them per row, and
#: they are constant within a municipality.
GEOGRAFICAS = ["code_state", "abbrev_state", "name_state",
               "code_region", "name_region"]


def _fonte(baixar: bool) -> Path:
    local = CACHE_CENSOBR / ARQUIVO
    if local.is_file():
        print(f"  usando o cache do censobr: {local}")
        print(f"  {local.stat().st_size / 1048576:.0f} MB")
        return local
    if not baixar:
        raise SystemExit(
            f"Microdado ausente em {local}.\n"
            f"Rode com --download para buscar de {URL}\n"
            f"(672 MB), ou rode censobr::read_population(2010) no R uma "
            f"vez para preencher o cache."
        )
    CACHE_CENSOBR.mkdir(parents=True, exist_ok=True)
    print(f"  baixando {URL}")
    urllib.request.urlretrieve(URL, local)
    print(f"  {local.stat().st_size / 1048576:.0f} MB")
    return local


def construir(fonte: Path) -> duckdb.DuckDBPyRelation:
    """Aggregate person-level microdata to one row per municipality."""
    con = duckdb.connect()
    p = fonte.as_posix()

    presentes = {c for c in con.sql(f"SELECT * FROM '{p}' LIMIT 0").columns}
    faltando = [c for c in VARIAVEIS if c not in presentes]
    if faltando:
        raise SystemExit(
            f"O microdado não traz {len(faltando)} das variáveis "
            f"esperadas: {faltando}. A release do censobr pode ter "
            f"mudado; confira o VARIAVEIS deste script."
        )

    # SUM, like the R's aggregation_fun="sum" default. The weighting is
    # NOT applied here for the same reason the R does not apply it: the
    # R's own output is a plain sum, and sample_weight travels as one of
    # the 34 columns so the consumer can weight if they need to.
    somas = ",\n        ".join(
        f'SUM(TRY_CAST("{cod}" AS DOUBLE)) AS "{nome}_sum"'
        for cod, nome in VARIAVEIS.items()
    )
    geo = ",\n        ".join(f'ANY_VALUE("{c}") AS "{c}"'
                             for c in GEOGRAFICAS if c in presentes)

    sql = f"""
        SELECT
        CAST(code_muni AS VARCHAR) AS municipality_code,
        {geo},
        COUNT(*) AS n_records,
        {somas}
        FROM '{p}'
        WHERE code_muni IS NOT NULL
        GROUP BY code_muni
        ORDER BY code_muni
    """
    return con.sql(sql)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--download", action="store_true",
                    help="baixa o microdado se não estiver em cache")
    ap.add_argument("--keep-synthetic", action="store_true",
                    help="não aposenta o census_2010.parquet gerado")
    args = ap.parse_args()

    print("build_census: censobr 2010 -> municipal\n")
    fonte = _fonte(args.download)

    print("\n  agregando 20,6 milhões de registros por município...")
    rel = construir(fonte)
    df = rel.df()
    print(f"  {len(df):,} municípios x {df.shape[1]} colunas")

    # Sanity: the IBGE has 5,570 municipalities. Fewer means the source
    # is partial; more means code_muni carries something unexpected.
    if not 5_000 <= len(df) <= 5_600:
        print(f"  AVISO: {len(df)} municípios está fora do esperado "
              f"(~5.570)")

    DESTINO.mkdir(parents=True, exist_ok=True)
    antigo = DESTINO / "census_2010.parquet"
    if antigo.is_file() and not args.keep_synthetic:
        aposentado = DESTINO / "census_2010_SINTETICO.parquet.old"
        shutil.move(str(antigo), str(aposentado))
        print(f"\n  gerado aposentado como {aposentado.name}")
        print("   (apague à mão depois de conferir o novo)")

    saida = DESTINO / "census_2010.parquet"
    df.to_parquet(saida, index=False)
    print(f"  escrito {saida.relative_to(ROOT)} "
          f"({saida.stat().st_size / 1048576:.1f} MB)")

    print("\n  amostra -- São Paulo capital (3550308):")
    cap = df[df.municipality_code.astype(str).str.startswith("3550308")]
    if len(cap):
        for c in ("n_records", "household_income_per_capita_sum",
                  "total_children_born_alive_sum"):
            if c in cap.columns:
                print(f"    {c:42} {cap.iloc[0][c]:,.0f}")

    print("\n  rode scripts/update_manifest.py agora.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
