from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
METADATA = ROOT / "metadata"
SUS_SYSTEMS_PATH = METADATA / "sus_systems.json"
DATASUS_SOURCES_PATH = METADATA / "datasus_sources.json"
DATASUS_SYSTEMS_PATH = METADATA / "datasus_systems.json"


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def compare_value(
    errors: list[str],
    context: str,
    field: str,
    expected: Any,
    actual: Any,
) -> None:
    if actual != expected:
        errors.append(
            f"{context}.{field}: expected {expected!r}, got {actual!r}"
        )


def validate_system_fields(
    errors: list[str],
    system: str,
    old_meta: dict[str, Any],
    new_meta: dict[str, Any],
    old_file: str,
) -> None:
    for field, expected in old_meta.items():
        if field not in new_meta:
            errors.append(f"{system}: missing field {field!r} from {old_file}")
            continue
        compare_value(errors, system, field, expected, new_meta[field])


def validate() -> list[str]:
    sus_catalog = load_json(SUS_SYSTEMS_PATH)
    source_catalog = load_json(DATASUS_SOURCES_PATH)
    consolidated = load_json(DATASUS_SYSTEMS_PATH)

    errors: list[str] = []
    sus_systems = sus_catalog.get("systems", {})
    source_systems = source_catalog.get("systems", {})
    new_systems = consolidated.get("systems", {})

    expected_systems = set(sus_systems) | set(source_systems)
    missing_systems = sorted(expected_systems - set(new_systems))
    extra_systems = sorted(set(new_systems) - expected_systems)

    for system in missing_systems:
        errors.append(f"{system}: missing from consolidated catalog")
    for system in extra_systems:
        errors.append(f"{system}: unexpected in consolidated catalog")

    for system in sorted(expected_systems & set(new_systems)):
        new_meta = new_systems[system]
        if system in sus_systems:
            validate_system_fields(
                errors,
                system,
                sus_systems[system],
                new_meta,
                "sus_systems.json",
            )
        if system in source_systems:
            validate_system_fields(
                errors,
                system,
                source_systems[system],
                new_meta,
                "datasus_sources.json",
            )

    compare_value(
        errors,
        "catalog",
        "sources",
        source_catalog.get("sources", {}),
        consolidated.get("sources"),
    )
    compare_value(
        errors,
        "catalog",
        "template_variables",
        source_catalog.get("template_variables", {}),
        consolidated.get("template_variables"),
    )
    if "categories" in sus_catalog:
        compare_value(
            errors,
            "catalog",
            "categories",
            sus_catalog["categories"],
            consolidated.get("categories"),
        )

    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("Consolidation validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("Consolidation validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
