# climasus-data
[![PyPI version](https://img.shields.io/pypi/v/readdbc.svg)](https://pypi.org/project/climasus-data/)
[![Python Versions](https://img.shields.io/pypi/pyversions/readdbc.svg)](https://pypi.org/project/climasus-data/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](../LICENSE.md)
[![r-universe version](https://r-lib.r-universe.dev/cpp11/badges/version)](https://r-lib.r-universe.dev/cpp11)

Catálogo de metadados compartilhado para os projetos CLIMA-SUS. 

- **Usado por:** [climasus4r](https://github.com/ClimaHealth/climasus4r) (R), [climasus4py](https://github.com/ClimaHealth/climasus4py) (Python)
- **Formato:** JSON, organizado por tema
- **Atualização:** Automática via função/utilitário nas bibliotecas clientes

---

## Estrutura

```
climasus-data/
├── metadata/           # Metadados principais (UFs, regiões, sistemas, clima, colunas DATASUS)
├── templates/          # Templates reutilizáveis (faixas etárias, padrões sazonais)
├── disease_groups/     # Grupos de doenças (CID-10, sensíveis ao clima)
├── dictionaries/       # Dicionários multilíngues (colunas, categorias)
├── geo/                # Geolocalização de municípios
├── manifest.json       # Inventário de arquivos + checksums
└── README.md
```

### Exemplos de arquivos
- `metadata/uf_codes.json`: UFs do Brasil, códigos IBGE, população, área
- `metadata/regions.json`: Macro-regiões, agrupamentos, aliases
- `metadata/datasus_systems.json`: Sistemas DATASUS/SUS, metadados descritivos, fontes FTP, templates de URLs, granularidade e filtros de particao
- `metadata/datasus_columns.json`: Colunas DATASUS (datas, numéricas), assinaturas de sistema e prioridade de detecção por papel (date, cause, age, sex, municipality, state) — compartilhado entre R e Python
- `metadata/sinan_diseases.json`: Códigos de agravos SINAN validados contra FTP DATASUS e documentação PySUS
- `templates/seasonal_patterns.json`: Mapeamento mês → estação por hemisfério (sul/norte); default `"south"`
- `templates/age_groups.json`: Presets de faixas etárias (`who`, `decadal`, `epidemiological_default`); `null` = sem limite superior (Inf em R, 999 em Python)
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
- **Schema version:** `2` (incremente em mudanças incompatíveis nos JSONs)

---

## Fontes dos dados

| Arquivo                  | Fonte   | Descrição |
|--------------------------|---------|-----------|
| metadata/uf_codes.json          | IBGE       | 27 UFs, códigos, nomes, população, área |
| metadata/regions.json           | IBGE       | 5 macro-regiões, agrupamentos, aliases |
| metadata/datasus_systems.json   | DATASUS/PySUS | Definicoes dos sistemas, granularidade, fontes FTP, templates de URL e filtros por particao |
| metadata/datasus_columns.json   | DATASUS    | Colunas datas/numéricas, assinaturas de sistema, prioridade de detecção por papel |
| metadata/sinan_diseases.json    | DATASUS/PySUS | Códigos de agravos SINAN, prefixos de arquivo e disponibilidade observada |
| metadata/inmet_normals.json     | INMET      | Normais climatológicas (1961-1990, 1991-2020) |
| templates/seasonal_patterns.json| Projeto    | Mês → estação por hemisfério (sul/norte) |
| templates/age_groups.json       | WHO/DATASUS| Presets de faixas etárias (who, decadal, epidemiológico) |
| disease_groups/*.json           | CID-10/WHO | Grupos de doenças, sensibilidade climática |
| dictionaries/                   | Projeto    | Traduções multilíngues |
| geo/municipios.json             | IBGE       | Municípios, geocódigos, coordenadas |

---

## Contribuindo

- Para propor correções ou novos metadados, abra um Pull Request ou Issue.
- Siga o padrão dos arquivos existentes (JSON, UTF-8, sem BOM).
- Atualize o `manifest.json` ao adicionar/alterar arquivos.

---

## Licença

MIT — mesmo do projeto principal CLIMA-SUS.
