# DATASUS systems catalog schema v2

`metadata/datasus_systems.json` is the unified DATASUS systems catalog. It
replaces `metadata/sus_systems.json` and `metadata/datasus_sources.json`.

The top-level shape is:

```jsonc
{
  "schema_version": 2,
  "description": "Unified DATASUS systems catalog (replaces sus_systems.json + datasus_sources.json)",
  "last_updated": "2026-04-26",
  "sources": {
    "datasus_ftp": {
      "protocol": "ftp",
      "base_url": "ftp://ftp.datasus.gov.br/dissemin/publicos",
      "official": true
    }
  },
  "template_variables": {
    "uf": "Two-letter state abbreviation.",
    "yyyy": "Four-digit year.",
    "yy": "Two-digit year.",
    "month": "Two-digit month.",
    "disease_code": "SINAN disease/condition code."
  },
  "systems": {
    "SIM-DO": {
      "source": "datasus_ftp",
      "family": "SIM",
      "file_format": "dbc",
      "filename_template": "DO{uf}{yyyy}.dbc",
      "url_templates": [],
      "geographic_scope": "state",
      "partition_filter": {},
      "disease_code": "DENG",
      "category": "SIM",
      "full_name": {
        "pt": "...",
        "en": "...",
        "es": "..."
      },
      "description": {
        "pt": "...",
        "en": "...",
        "es": "..."
      },
      "temporal_granularity": "annual",
      "requires_month": false,
      "cache_days": 365,
      "is_national": false,
      "coverage": "state",
      "availability": {
        "start_year": 1979,
        "current": true
      },
      "data_characteristics": {}
    }
  }
}
```

System entries keep the flattened fields from `datasus_sources.json` and the
metadata fields from `sus_systems.json`.

Duplicate fields:

- `temporal_granularity` is stored once. Migration must abort if old files
  contain different values for the same system.
- `requires_month` is stored once. Migration must abort if old files contain
  different values for the same system.

Synonym fields are intentionally preserved in this schema:

- `category` and `family`
- `coverage` and `geographic_scope`
- `is_national` and `geographic_scope == "national"`

These fields are not renamed or removed in schema v2 because this migration is
only a consolidation of existing metadata. Naming cleanup belongs in a separate
plan.
