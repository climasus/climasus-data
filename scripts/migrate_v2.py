from __future__ import annotations

import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
METADATA = ROOT / "metadata"
SUS_SYSTEMS_PATH = METADATA / "sus_systems.json"
DATASUS_SOURCES_PATH = METADATA / "datasus_sources.json"
OUTPUT_PATH = METADATA / "datasus_systems.json"

DUPLICATE_FIELDS = ("temporal_granularity", "requires_month")

SOURCE_FIELD_ORDER = (
    "source",
    "family",
    "file_format",
    "filename_template",
    "url_templates",
    "geographic_scope",
    "partition_filter",
    "disease_code",
)

SUS_FIELD_ORDER = (
    "category",
    "full_name",
    "description",
    "temporal_granularity",
    "requires_month",
    "cache_days",
    "is_national",
    "coverage",
    "availability",
    "climate_sensitive",
    "data_characteristics",
)


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def add_ordered_fields(
    output: OrderedDict[str, Any],
    source: dict[str, Any],
    field_order: tuple[str, ...],
    skip: set[str] | None = None,
) -> None:
    skip = skip or set()
    for field in field_order:
        if field in source and field not in skip:
            output[field] = source[field]
    for field, value in source.items():
        if field not in output and field not in skip:
            output[field] = value


def merge_system(
    system: str,
    sus_meta: dict[str, Any] | None,
    source_meta: dict[str, Any] | None,
) -> OrderedDict[str, Any]:
    sus_meta = sus_meta or {}
    source_meta = source_meta or {}

    errors: list[str] = []
    for field in DUPLICATE_FIELDS:
        if field in sus_meta and field in source_meta and sus_meta[field] != source_meta[field]:
            errors.append(
                f"{system}.{field}: sus_systems={sus_meta[field]!r}; "
                f"datasus_sources={source_meta[field]!r}"
            )

    if errors:
        raise ValueError("\n".join(errors))

    merged: OrderedDict[str, Any] = OrderedDict()
    add_ordered_fields(merged, source_meta, SOURCE_FIELD_ORDER, set(DUPLICATE_FIELDS))
    add_ordered_fields(merged, sus_meta, SUS_FIELD_ORDER)
    return merged


def build_catalog() -> OrderedDict[str, Any]:
    sus_catalog = load_json(SUS_SYSTEMS_PATH)
    source_catalog = load_json(DATASUS_SOURCES_PATH)

    sus_systems = sus_catalog.get("systems", {})
    source_systems = source_catalog.get("systems", {})

    systems: OrderedDict[str, Any] = OrderedDict()
    for system in sorted(set(sus_systems) | set(source_systems)):
        systems[system] = merge_system(
            system=system,
            sus_meta=sus_systems.get(system),
            source_meta=source_systems.get(system),
        )

    catalog: OrderedDict[str, Any] = OrderedDict()
    catalog["schema_version"] = 2
    catalog["description"] = (
        "Unified DATASUS systems catalog "
        "(replaces sus_systems.json + datasus_sources.json)"
    )
    catalog["last_updated"] = "2026-04-26"
    catalog["sources"] = source_catalog.get("sources", {})
    catalog["template_variables"] = source_catalog.get("template_variables", {})
    catalog["systems"] = systems
    if "categories" in sus_catalog:
        catalog["categories"] = sus_catalog["categories"]
    return catalog


def main() -> int:
    try:
        catalog = build_catalog()
    except ValueError as exc:
        print("Divergent duplicate fields found. Migration aborted:", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1

    with OUTPUT_PATH.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
