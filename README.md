# climasus-data

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](../LICENSE.md)

Catálogo de metadados compartilhado para os projetos CLIMA-SUS.

- **Usado por:** [climasus4r](https://github.com/ClimaHealth/climasus4r) (R), [climasus4py](https://github.com/ClimaHealth/climasus4py) (Python)
- **Formato:** JSON, organizado por tema
- **Atualização:** Automática via função/utilitário nas bibliotecas clientes

---

## Estrutura

```
climasus-data/
├── metadata/           # Metadados principais (UFs, regiões, sistemas, clima)
├── disease_groups/     # Grupos de doenças (CID-10, sensíveis ao clima)
├── dictionaries/       # Dicionários multilíngues (colunas, categorias)
├── geo/                # Geolocalização de municípios
├── manifest.json       # Inventário de arquivos + checksums
└── README.md
```

### Exemplos de arquivos
- `metadata/uf_codes.json`: UFs do Brasil, códigos IBGE, população, área
- `metadata/regions.json`: Macro-regiões, agrupamentos, aliases
- `metadata/sus_systems.json`: Sistemas do SUS (SIM, SIH, SINAN, SINASC)
- `disease_groups/core.json`: Grupos principais de doenças
- `dictionaries/pt-en/columns.json`: Tradução de nomes de colunas PT→EN
- `geo/municipios.json`: 5.570+ municípios, coordenadas, timezone

---

## Como usar

### R (climasus4r)
```r
# Download automático na primeira execução
climasus_update_data()

# Caminho para arquivo específico
climasus_data_path("metadata/uf_codes.json")
```

### Python (climasus4py)
```python
from climasus import data

data.update()  # Baixa/atualiza catálogo
uf_codes = data.load("metadata/uf_codes.json")
```

---

## Versionamento
- O arquivo `manifest.json` lista todos os arquivos e seus MD5.
- As bibliotecas clientes comparam o manifest local/remoto para decidir se precisam atualizar.
- **Schema version:** `1` (incremente em mudanças incompatíveis nos JSONs)

---

## Fontes dos dados

| Arquivo                  | Fonte   | Descrição |
|--------------------------|---------|-----------|
| metadata/uf_codes.json   | IBGE    | 27 UFs, códigos, nomes, população, área |
| metadata/regions.json    | IBGE    | 5 macro-regiões, agrupamentos, aliases |
| metadata/sus_systems.json| DATASUS | Definições dos sistemas, granularidade |
| metadata/inmet_normals.json | INMET | Normais climatológicas (1961-1990, 1991-2020) |
| disease_groups/*.json    | CID-10/WHO | Grupos de doenças, sensibilidade climática |
| dictionaries/            | Projeto | Traduções multilíngues |
| geo/municipios.json      | IBGE    | Municípios, geocódigos, coordenadas |

---

## Contribuindo

- Para propor correções ou novos metadados, abra um Pull Request ou Issue.
- Siga o padrão dos arquivos existentes (JSON, UTF-8, sem BOM).
- Atualize o `manifest.json` ao adicionar/alterar arquivos.

---

## Licença

MIT — mesmo do projeto principal CLIMA-SUS.
