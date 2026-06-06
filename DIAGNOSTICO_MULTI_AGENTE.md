# Diagnóstico Multi-Agente — `climasus-data`

**Data:** 8 de maio de 2026  
**Agentes consultados:** Project Analyst · Data Engineer · Data Scientist · Python Code Reviewer · Package Engineer · Documentation Reviewer  
**Modo:** Análise (nenhum arquivo foi alterado)

---

## Índice

1. [Resumo Executivo Consolidado](#1-resumo-executivo-consolidado)
2. [Mapa de Achados por Severidade](#2-mapa-de-achados-por-severidade)
3. [Diagnóstico — Project Analyst](#3-diagnóstico--project-analyst)
4. [Diagnóstico — Data Engineer](#4-diagnóstico--data-engineer)
5. [Diagnóstico — Data Scientist](#5-diagnóstico--data-scientist)
6. [Diagnóstico — Python Code Reviewer](#6-diagnóstico--python-code-reviewer)
7. [Diagnóstico — Package Engineer (PyPI + CRAN)](#7-diagnóstico--package-engineer-pypi--cran)
8. [Diagnóstico — Documentation Reviewer](#8-diagnóstico--documentation-reviewer)
9. [Plano de Ação Consolidado](#9-plano-de-ação-consolidado)
10. [Próximos Agentes Recomendados](#10-próximos-agentes-recomendados)

---

## 1. Resumo Executivo Consolidado

O `climasus-data` é o repositório de dados de referência compartilhado do ecossistema CLIMA-SUS — municípios, regiões, sistemas DATASUS, dicionários, dados climáticos INMET, censitários e espaciais. Serve simultaneamente como pacote Python (PyPI) e pacote R. A **arquitetura conceitual é correta**: JSONs como fonte de verdade, manifesto com MD5 para rastreamento de integridade, API mínima em ambas as linguagens.

Contudo, **5 dos 6 agentes convergiram em 4 problemas sistêmicos graves**:

| # | Problema sistêmico | Severidade | Agentes |
|---|---|---|---|
| **S1** | Assets Parquet da v1.1.0 **não chegam ao usuário via pip** (`pyproject.toml` aponta para diretórios vazios em vez de `assets/`) | 🔴 Bloqueador | Project Analyst, Package Engineer, Data Scientist |
| **S2** | Dados climáticos e IDW **estatisticamente inválidos**: `inmet_observations_2023.parquet` tem 366 linhas (1 estação) e `idw_weights_municipality.parquet` tem top_k=1 em vez de 3 | 🔴 Crítico | Data Engineer, Data Scientist |
| **S3** | **README documenta API que não existe** (`data.update()`, `data.load()` em Python; `climasus_update_data()` em R) — causa erro imediato ao novo usuário | 🔴 Crítico | Package Engineer, Documentation Reviewer, Data Scientist |
| **S4** | **Zero testes Python** e CI publica sem rodar nenhum teste; instância local do pacote R quebra porque `inst/extdata/` está vazio no repositório | 🔴 Crítico | Project Analyst, Package Engineer, Python Code Reviewer |

---

## 2. Mapa de Achados por Severidade

### 🔴 Crítico / Bloqueador (P0–P1)

| ID | Achado | Arquivo(s) | Agente(s) |
|---|---|---|---|
| C1 | `force-include` mapeia `"spatial"`, `"climate"`, `"census"` da raiz (vazios) em vez de `"assets/spatial"`, `"assets/climate"`, `"assets/census"` → Parquets ausentes do wheel | `pyproject.toml L41–73` | Project Analyst, Package Engineer |
| C2 | `inmet_observations_2023.parquet` tem 366 linhas (1 estação × 365 dias) → inutilizável para análise espacial | `scripts/build_climate.py L85–113` | Data Engineer, Data Scientist |
| C3 | `idw_weights_municipality.parquet` tem 5.570 linhas com top_k=1 (equivalente a vizinho mais próximo simples, não IDW) | `scripts/build_idw_weights.py L21` | Data Engineer, Data Scientist |
| C4 | Data hardcoded em `update_manifest.py` — `last_updated` nunca muda | `scripts/update_manifest.py L33` | Project Analyst, Data Engineer, Python Code Reviewer |
| C5 | README documenta API inexistente (`data.update()`, `data.load()` em Python; `climasus_update_data()` em R) | `README.md` | Package Engineer, Documentation Reviewer |
| C6 | Badges PyPI e r-universe apontam para outros pacotes (`readdbc`, `cpp11`) | `README.md L1–3` | Project Analyst, Data Scientist, Package Engineer |
| C7 | `r-pkg/inst/extdata/` vazio → pacote R quebra em instalação local sem CI | `r-pkg/inst/extdata/` | Project Analyst, Package Engineer |
| C8 | CI do PyPI publica sem nenhum step de teste | `.github/workflows/publish-pypi.yml` | Project Analyst, Package Engineer |

### 🟠 Risco (P1–P2)

| ID | Achado | Arquivo(s) | Agente(s) |
|---|---|---|---|
| R1 | `get_path()` sem validação de path traversal — aceita `"../../etc/passwd"` | `src/climasus_data/__init__.py L68` | Python Code Reviewer |
| R2 | `load_json()` retorna objeto mutável cacheado — modificação corrompe o cache | `src/climasus_data/__init__.py L79` | Python Code Reviewer |
| R3 | `_find_data_root()` sobe toda a árvore sem verificar se o `manifest.json` pertence ao pacote | `src/climasus_data/__init__.py L40–55` | Project Analyst, Python Code Reviewer |
| R4 | `sync-r-pkg.yml` faz push direto ao `main` sem abrir PR | `.github/workflows/sync-r-pkg.yml L82–96` | Project Analyst, Package Engineer |
| R5 | `stations.iloc[idx]` sem `reset_index()` após filtro — mapeamento frágil | `scripts/build_idw_weights.py L38` | Python Code Reviewer |
| R6 | `dropna=False` no groupby → registros de "estação desconhecida" propagados ao Parquet | `scripts/build_climate.py L112` | Python Code Reviewer |
| R7 | `build_climate.py` e `build_census.py` dependem de `fixture_reais/` no repositório pai — quebra em clone isolado | `scripts/build_census.py L11`, `build_climate.py L11` | Data Engineer, Python Code Reviewer |
| R8 | Assets Parquet não disponíveis via API R — sem `cd_load_parquet()` nem documentação para acessá-los | `r-pkg/R/climasus_data.R` | Data Scientist, Package Engineer |
| R9 | `global _DATA_ROOT` sem proteção de thread em ambientes multi-worker | `src/climasus_data/__init__.py L54` | Python Code Reviewer |

### 🟡 Má Prática (P2–P3)

| ID | Achado | Arquivo(s) | Agente(s) |
|---|---|---|---|
| M1 | `scripts/` incluído no wheel — ferramentas de manutenção interna distribuídas a todos os usuários | `pyproject.toml L44` | Project Analyst, Python Code Reviewer, Package Engineer |
| M2 | Versão hardcoded como default em `update_manifest()` (`"1.1.0"`) | `scripts/update_manifest.py L18` | Python Code Reviewer |
| M3 | `rglob("*.parquet")` varre todo o repositório — pode incluir arquivos temporários ou de outros projetos | `scripts/update_manifest.py L28` | Python Code Reviewer |
| M4 | `jsonlite` como `Suggests` em vez de `Imports` no DESCRIPTION R — `cd_load()` falha silenciosamente | `r-pkg/DESCRIPTION L34` | Project Analyst |
| M5 | Versão Python (`1.1.0`) e R (`0.1.5`) sem sincronização documentada | `pyproject.toml`, `r-pkg/DESCRIPTION` | Package Engineer, Documentation Reviewer |
| M6 | Classifier `Development Status :: 3 - Alpha` para versão `1.1.0` | `pyproject.toml` | Package Engineer |
| M7 | Dependências dos scripts de build (`scipy`, `shapely`, `geobr`, `censobr`) não declaradas em `[project.optional-dependencies]` | `pyproject.toml` | Project Analyst, Python Code Reviewer |
| M8 | Link da licença no README usa caminho relativo `../LICENSE.md` — quebra no GitHub | `README.md` | Documentation Reviewer |

### 🔵 Lacuna (P2–P4)

| ID | Achado | Agente(s) |
|---|---|---|
| L1 | Zero testes Python (o pacote R tem `tests/testthat/test-api.R`, o Python não tem nada) | Project Analyst, Python Code Reviewer, Package Engineer |
| L2 | Sem tooling configurado no `pyproject.toml` (ruff, mypy, pytest) apesar de `.ruff_cache/` existir | Python Code Reviewer |
| L3 | Schema dos assets Parquet completamente indocumentado | Documentation Reviewer, Data Scientist |
| L4 | Sem seção de instalação no README | Documentation Reviewer |
| L5 | SINAN com apenas 8 de ~30 agravos (faltam TUBE, FAMA, ESQU, HEPA, SRAG...) | Data Scientist |
| L6 | `datasus_columns.json` cobre apenas 4 sistemas (SIM-DO, SIH-RD, SINAN-DENGUE, SINASC) | Data Scientist |
| L7 | Sem catálogo de valores categóricos (RACACOR, SEXO, LOCOCOR, ESTCIV, TIPOBITO...) | Data Scientist |
| L8 | Normais climatológicas INMET presentes apenas como catálogo de variáveis, sem valores reais | Data Scientist, Data Engineer |
| L9 | Sem orquestrador de build (Makefile ou `build_all.py`) — ordem de execução dos scripts não documentada | Data Engineer |
| L10 | Nenhuma validação de schema dos JSONs no CI | Project Analyst, Data Engineer |
| L11 | `census_2010.parquet` não mencionado no README (mas existe no manifesto) | Documentation Reviewer |
| L12 | Sem `load_parquet()` na API Python e R | Data Scientist |
| L13 | `assets/` ausente na árvore de estrutura do README | Documentation Reviewer |
| L14 | Microsregiões e mesorregiões ausentes em `geo/municipios.json` | Data Scientist |
| L15 | Sem CHANGELOG ou NEWS.md no repositório raiz | Project Analyst, Package Engineer |

---

## 3. Diagnóstico — Project Analyst

### Arquitetura do repositório

```
climasus-data/
├── [JSONs de metadados — raiz]         ← fonte de verdade
│    metadata/, geo/, dictionaries/, disease_groups/, templates/
│
├── assets/                             ← Parquets via Git LFS (≥ v1.1.0)
│    spatial/, climate/, census/
│
├── src/climasus_data/__init__.py       ← API Python mínima
│
├── r-pkg/                              ← Pacote R (climasus.data)
│    R/climasus_data.R                  (cd_path, cd_load, cd_list_files, cd_version)
│    inst/extdata/                      ← VAZIO no repo; populado pelo CI
│
├── scripts/                            ← Geradores dos Parquets (uso interno)
│
├── manifest.json                       ← Inventário com MD5 de todos os arquivos
│
└── .github/workflows/
     publish-pypi.yml                   ← Tag → hatch build + PyPI (sem testes)
     sync-r-pkg.yml                     ← Tag → sincroniza JSONs no r-pkg + push direto à main
```

### Bugs críticos

- **C1 (Bloqueador):** `force-include` em `pyproject.toml` mapeia `"spatial"`, `"climate"`, `"census"` da raiz (vazios) em vez de `"assets/spatial"` etc. Usuários PyPI não recebem nenhum Parquet.
- **C4:** Data hardcoded `"2026-05-02"` em `update_manifest.py` — nunca atualiza.
- **C6:** Badges apontam para `readdbc` e `cpp11` — copy-paste não corrigido.

### Riscos

- CI publica sem testes; `sync-r-pkg.yml` faz push direto à `main`; `_find_data_root()` sem verificação de identidade; `inst/extdata/` vazio no repo.

### Pontos fortes

- OIDC Trusted Publishing no CI; Git LFS para Parquets grandes; `manifest.json` com MD5 + `schema_version`; API Python zero-deps runtime; `.gitignore` com comentário explicativo sobre `inst/extdata/`.

---

## 4. Diagnóstico — Data Engineer

### Pipeline de geração de dados

```
build_spatial.py        → municipalities.parquet (geometrias)
      ↓
build_climate.py        → inmet_stations.parquet, inmet_observations_2023.parquet
      ↓
build_idw_weights.py    → idw_weights_municipality.parquet
      ↓
build_census.py         → census_2010.parquet, census_2022.parquet
      ↓
update_manifest.py      → manifest.json (MD5 + metadados)
```

**Nenhum script central documenta ou impõe essa ordem.**

### Bugs críticos de dados

**Bug #1 — `inmet_observations_2023.parquet` com 1 estação** (`build_climate.py L85–113`)  
`build_observations_from_climasus4r()` ingere um único arquivo fixture de 1 estação. O manifesto confirma: 366 linhas (1 estação × 366 dias). Com 636 estações INMET, o esperado seria ≥ 232.140 linhas. Qualquer análise de interpolação espacial usando esse arquivo usa um único ponto para todo o Brasil.

**Bug #2 — `idw_weights_municipality.parquet` com top_k=1** (`build_idw_weights.py L21`)  
O script usa `top_k=3`, mas como apenas 1 estação passa o filtro, o resultado são 5.570 linhas (1 por município), equivalente a vizinho mais próximo simples — não a interpolação IDW, que dá nome ao arquivo.

**Bug #3 — Data hardcoded** (`update_manifest.py L33`)  
```python
manifest["last_updated"] = "2026-05-02"  # nunca muda
```

### Riscos de pipeline

- `FIXTURE_ROOT = ROOT.parent / "fixture_reais"` — dependência externa ao repositório, quebra em clone isolado.
- Schema divergente entre os dois caminhos de `build_census.py` (via `censobr` vs. via fixture).
- `update_manifest.py` não detecta arquivos removidos do disco.
- Sem orquestração — execução fora de ordem gera dados inválidos silenciosamente.

### Pontos fortes de dados

- `geo/municipios.json`: 5.570 municípios com geocódigo IBGE, lat/lon e fuso horário.
- `build_spatial.py` com fallback inteligente: geobr disponível → polígonos completos; senão → POINT.
- `idw_weights`: `np.maximum(..., 1e-9)` previne divisão por zero.
- `manifest.json` com MD5 e contagem de linhas.
- `disease_groups/` com grupos CID-10 e `climate_sensitive` flag.

---

## 5. Diagnóstico — Data Scientist

### Perspectiva epidemiológica

O `climasus-data` tem **potencial alto mas entrega atual baixa** para o analista:

| Camada | Estado | Impacto |
|---|---|---|
| Metadados JSON (regiões, UFs, sistemas) | ✅ Sólidos | Alto |
| `geo/municipios.json` | ✅ Completo (5.570 municípios + fuso horário) | Alto |
| `disease_groups/` com CID-10 | ✅ Bem curado | Médio-Alto |
| Dados climáticos | 🔴 1 estação | Inutilizável |
| IDW weights | 🔴 top_k=1 | Inutilizável |
| Cobertura SINAN | 🟡 8/~30 agravos | Lacuna crítica |
| Catálogo de colunas | 🟡 4 sistemas | Insuficiente |
| Catálogo de valores categóricos | ❌ Inexistente | Lacuna crítica |

### Lacunas críticas para epidemiologistas

| Lacuna | Impacto |
|---|---|
| Sem catálogo de valores categóricos (RACACOR, SEXO, LOCOCOR, ESTCIV...) | O analista não consegue tabular nem etiquetar automaticamente variáveis categóricas do SIM/SIH/SINASC |
| SINAN com apenas 8 agravos (faltam TUBE, FAMA, ESQU, HEPA, SRAG) | Pipeline de ingestão automática falharia para esses sistemas |
| `datasus_columns.json` com apenas 4 sistemas | Detecção automática de sistema falha para SIA-PA, CNES, outros SINAN |
| Sem `load_parquet()` nas APIs | Parquets são cidadãos de segunda classe — sem descoberta guiada |
| `all_date_columns` e `all_numeric_columns` misturados (globais, não por sistema) | Falsos positivos em lógicas de coerção de tipos |

### Pontos fortes para analistas

- `regions.json` com biomas e bacias hidrográficas — raro e valioso.
- `climate_sensitive: true/false` em `disease_groups/` — permite filtragem programática.
- `datasus_systems.json` com templates FTP para os sistemas mais usados.
- `geo/municipios.json` com `fuso_horario` — diferencial para análises no Norte/Acre/Amapá.
- Templates de faixas etárias (WHO, decadal, epidemiológico).

---

## 6. Diagnóstico — Python Code Reviewer

### Análise cirúrgica do código

**Bug B-01 — Data hardcoded** (`update_manifest.py L33`): já detalhado em C4.

**Risco de Segurança S-01 — Path traversal em `get_path()`** (`__init__.py L68`)
```python
def get_path(relative: str) -> Path:
    return data_root() / relative  # sem validação
```
Aceita `"../../etc/passwd"` sem reclamar. Fix imediato:
```python
def get_path(relative: str) -> Path:
    resolved = (data_root() / relative).resolve()
    if not resolved.is_relative_to(data_root().resolve()):
        raise ValueError(f"Path traversal detectado: {relative!r}")
    return resolved
```

**Risco de Segurança S-02 — Cache mutável em `load_json()`** (`__init__.py L79`)
```python
@lru_cache(maxsize=32)
def load_json(relative: str) -> Any:
    return json.load(f)  # retorna dict/list mutável — cache corruptível
```
Fix: `return copy.deepcopy(result)`.

**Risco R-01 — `iloc[idx]` sem `reset_index()`** (`build_idw_weights.py L38`)  
Mapeamento KDTree → DataFrame frágil após filtro de estações.

**Risco R-02 — `dropna=False` no groupby** (`build_climate.py L112`)  
Propaga registros de estação desconhecida (`NaN`) ao Parquet final.

**Má prática P-01 — Versão hardcoded em `update_manifest()`** (`update_manifest.py L18`)  
`default="1.1.0"` divergirá na próxima release.

**Má prática P-02 — `rglob("*.parquet")`** varre todo o repositório (`update_manifest.py L28`)  
Deveria ser restrito a `assets/**/*.parquet`.

**Má prática P-03 — `FIXTURE_ROOT` hardcoded** em dois scripts  
```python
FIXTURE_ROOT = ROOT.parent / "fixture_reais"  # depende do monorepo pai
```

**Lacunas:**
- Zero testes Python.
- Sem `[tool.ruff]`, `[tool.mypy]`, `[tool.pytest.ini_options]` no `pyproject.toml`.
- Dependências de build não declaradas como `optional-dependencies`.
- `global _DATA_ROOT` sem proteção de thread.

### Pontos fortes do código

- `__init__.py` cirúrgico: API mínima, `lru_cache`, erros com mensagens contextuais.
- `from __future__ import annotations` em todos os arquivos.
- `build_spatial.py` com helpers bem separados e normalização Unicode correta.
- `build_idw_weights.py` usa `cKDTree` e `np.maximum(..., 1e-9)` — defensivo e correto.
- `pyproject.toml` com `hatchling` moderno e `force-include` estruturado.

---

## 7. Diagnóstico — Package Engineer (PyPI + CRAN)

### Bloqueador de distribuição

**`pyproject.toml` aponta para diretórios errados (C1):**
```toml
# Atual (ERRADO — diretórios raiz estão vazios):
"spatial" = "climasus_data/spatial"
"climate" = "climasus_data/climate"
"census"  = "climasus_data/census"

# Correto:
"assets/spatial" = "climasus_data/spatial"
"assets/climate" = "climasus_data/climate"
"assets/census"  = "climasus_data/census"
```

### Problemas de empacotamento

| ID | Problema | Fix |
|---|---|---|
| M6 | Classifier `Alpha` para v1.1.0 | Trocar para `4 - Beta` |
| M7 | `scripts/` no wheel | Remover de `force-include` |
| M5 | Versão R `0.1.5` vs Python `1.1.0` | Atualizar DESCRIPTION manualmente |
| M4 | `jsonlite` em Suggests (deveria ser Imports) | Mover para `Imports:` |
| — | URLs `Homepage` = `Repository` no pyproject | Adicionar `Documentation`, `Changelog` |

### Estratégia de Parquets — escolha necessária

O repositório prometeu Parquets na v1.1.0 mas não definiu estratégia de distribuição:

| Opção | Pros | Contras |
|---|---|---|
| **A — Bundled no wheel** (atual, com bug C1 corrigido) | Offline, sem download | Wheel > 150MB |
| **B — GitHub Releases separados** (via `pooch`/`requests`) | Wheel leve | Requer download em runtime |
| **C — Apenas em clone do repo** | Zero custo de infraestrutura | Não serve usuários pip |

**Recomendação:** Documentar claramente qual é a estratégia e corrigir o pyproject.toml de acordo.

### Pontos fortes de empacotamento

- Trusted Publishing (OIDC) — sem `PYPI_API_TOKEN` exposto.
- `hatchling` moderno com layout `src/`.
- `sync-r-pkg.yml` com `R CMD check --as-cran` antes do push.
- `r-pkg/DESCRIPTION` completo com autores, URL, BugReports.

---

## 8. Diagnóstico — Documentation Reviewer

### Problemas críticos de documentação

**API errada no README (B5):**  
Python:
```python
# README (ERRADO):
from climasus import data
data.update()
data.load("metadata/uf_codes.json")

# API real:
import climasus_data
climasus_data.load_json("metadata/uf_codes.json")
```
R:
```r
# README (ERRADO):
climasus_update_data()
climasus_data_path("metadata/uf_codes.json")

# API real:
cd_path("metadata/uf_codes.json")
cd_load("metadata/datasus_systems.json")
```

**Sem instruções de instalação (L4):**  
O README não tem seção de instalação. Não aparece `pip install climasus-data` nem `remotes::install_github()`.

**Schema dos Parquets indocumentado (L3):**  
A v1.1.0 adicionou 6 arquivos Parquet, mas nenhum campo está documentado. O usuário não sabe quais colunas existem em `municipalities.parquet`, nem qual a resolução temporal de `inmet_observations_2023.parquet`.

**`assets/` ausente na árvore do README (L13):**  
A estrutura de diretórios no README omite `assets/` — onde os Parquets realmente estão.

**Link de licença relativo quebra no GitHub (M8):**  
```markdown
[![License: MIT](...)](/LICENSE.md)  # path relativo quebra no GitHub
```

### Pontos fortes de documentação

- Metadados inline nos JSONs: `schema_version`, `description`, `last_updated`, `sources`.
- Multilíngue (PT/EN/ES) em todos os JSONs.
- API R com roxygen2 completo (`@param`, `@return`, `@examples`).
- Scripts de build têm docstrings de módulo e de função.
- `manifest.json` com MD5 para verificação de integridade.

### Quick wins de documentação

1. Corrigir exemplos Python e R no README para refletir a API real.
2. Adicionar seção de instalação (`pip install climasus-data`, `remotes::install_github()`).
3. Corrigir badges PyPI e r-universe.
4. Corrigir link da licença (usar URL absoluta).
5. Adicionar `assets/` na árvore de estrutura.
6. Documentar `census_2010.parquet` (existe mas não está no README).
7. Detalhar `python scripts/update_manifest.py` na seção "Contribuindo".

---

## 9. Plano de Ação Consolidado

### Fase 1 — Bloqueadores imediatos (P0, < 2 horas)

| Ação | Arquivo | Responsável sugerido |
|---|---|---|
| Corrigir `force-include` para `"assets/spatial"`, `"assets/climate"`, `"assets/census"` | `pyproject.toml L41–73` | Package Engineer |
| Corrigir data hardcoded: `datetime.date.today().isoformat()` | `scripts/update_manifest.py L33` | Python Code Reviewer |
| Corrigir badges PyPI e r-universe no README | `README.md L1–3` | Documentation Reviewer |
| Corrigir exemplos de código Python e R no README | `README.md` | Documentation Reviewer |
| Adicionar seção de instalação no README | `README.md` | Documentation Reviewer |
| Adicionar step de testes antes do build no `publish-pypi.yml` | `.github/workflows/publish-pypi.yml` | DevOps Engineer |

### Fase 2 — Bugs e riscos críticos (P1, 1–3 dias)

| Ação | Arquivo | Responsável sugerido |
|---|---|---|
| Adicionar validação de path traversal em `get_path()` | `__init__.py L68` | Python Code Reviewer |
| Retornar `copy.deepcopy()` em `load_json()` | `__init__.py L79` | Python Code Reviewer |
| Adicionar `reset_index(drop=True)` após filtro de estações | `build_idw_weights.py L18` | Python Code Reviewer |
| Corrigir `dropna=False` → `dropna=True` no groupby | `build_climate.py L112` | Python Code Reviewer |
| Mover versão hardcoded para ler de `climasus_data.__version__` | `update_manifest.py L18` | Python Code Reviewer |
| Restringir `rglob` para `assets/**/*.parquet` | `update_manifest.py L28` | Python Code Reviewer |
| Mover `jsonlite` de `Suggests` para `Imports` em DESCRIPTION | `r-pkg/DESCRIPTION L34` | Package Engineer |
| Remover `scripts/` do `force-include` do wheel | `pyproject.toml` | Package Engineer |
| Criar testes Python básicos (`tests/test_api.py`) | `tests/` (novo) | Test Engineer |
| Adicionar verificação de identidade em `_find_data_root()` | `src/climasus_data/__init__.py` | Python Code Reviewer |

### Fase 3 — Qualidade e dados (P2, 1 semana)

| Ação | Arquivo | Responsável sugerido |
|---|---|---|
| Regenerar `inmet_observations_2023.parquet` com múltiplas estações (meta mínima: 50+ estações) | `scripts/build_climate.py` | Data Engineer |
| Regenerar `idw_weights_municipality.parquet` com top_k=3 real (~16.710 linhas) | `scripts/build_idw_weights.py` | Data Engineer |
| Unificar schema de `build_census.py` (escolher 1 schema canônico) | `scripts/build_census.py` | Data Engineer |
| Criar orquestrador `scripts/build_all.py` ou `Makefile` | `scripts/` | Data Engineer |
| Adicionar `[project.optional-dependencies] build = [...]` | `pyproject.toml` | Package Engineer |
| Adicionar `[tool.ruff]`, `[tool.mypy]`, `[tool.pytest.ini_options]` | `pyproject.toml` | Python Code Reviewer |
| Corrigir classifier `Alpha → Beta` e adicionar URLs de Documentation e Changelog | `pyproject.toml` | Package Engineer |
| Sincronizar versão R com Python (`0.1.5 → 1.1.0`) | `r-pkg/DESCRIPTION` | Package Engineer |
| Documentar schema de colunas de cada Parquet no README | `README.md` | Documentation Reviewer |
| Adicionar `assets/` na árvore do README | `README.md` | Documentation Reviewer |
| Substituir push direto por PR automático em `sync-r-pkg.yml` | `.github/workflows/sync-r-pkg.yml` | DevOps Engineer |
| Adicionar validação de JSON no CI (ex: `python -m json.tool`) | `.github/workflows/` | DevOps Engineer |

### Fase 4 — Lacunas analíticas e estruturais (P3, sprints)

| Ação | Valor | Responsável sugerido |
|---|---|---|
| Adicionar 10–15 agravos SINAN ao catálogo (TUBE, FAMA, ESQU, HEPA, SRAG...) | Alto para epidemiologistas | DATASUS Specialist |
| Criar `metadata/datasus_categories.json` com RACACOR, SEXO, LOCOCOR, ESTCIV... | Alto — lacuna crítica | DATASUS Specialist |
| Expandir `datasus_columns.json` para SIA-PA, CNES, outros SINAN | Médio | DATASUS Specialist |
| Separar `all_date_columns` / `all_numeric_columns` por sistema | Médio | Data Engineer |
| Adicionar `load_parquet()` à API Python e `cd_load_parquet()` à API R | Médio | Data Engineer + Package Engineer |
| Adicionar micros/mesorregiões IBGE em `geo/municipios.json` | Médio | Data Engineer |
| Normalais climatológicas reais como Parquet em `assets/climate/inmet_normals.parquet` | Médio | Data Engineer |
| Criar `docs/data-catalog.md` com descrição completa de cada dataset | Alto para usuários | Documentation Reviewer |
| Externalizar `FIXTURE_ROOT` para variável de ambiente | Médio | Backend Engineer |
| Workflow R CMD check independente do sync | Médio | DevOps Engineer |

---

## 10. Próximos Agentes Recomendados

| Agente | Tarefa prioritária |
|---|---|
| **Python Code Reviewer (Modo Implementação)** | Corrigir path traversal, cache mutável, `iloc` sem `reset_index`, `dropna=False`, data/versão hardcoded |
| **DevOps Engineer** | Corrigir `publish-pypi.yml` (testes antes do build); converter `sync-r-pkg.yml` para PR automático; adicionar validação de JSON no CI |
| **Documentation Reviewer (Modo Implementação)** | Corrigir exemplos de código, adicionar instalação, corrigir badges e link de licença, documentar schema dos Parquets |
| **Data Engineer** | Regenerar `inmet_observations_2023.parquet` (multi-estação), `idw_weights_municipality.parquet` (top_k=3 real), unificar schema de census, criar orquestrador de build |
| **Package Engineer** | Corrigir `force-include` (C1), remover `scripts/` do wheel, atualizar classifiers, mover jsonlite para Imports, sincronizar versão R/Python |
| **DATASUS Specialist** | Expandir catálogo SINAN (8→20+ agravos), criar `datasus_categories.json` com valores categóricos, expandir `datasus_columns.json` |
| **Software Architect** | Decidir estratégia canônica de distribuição dos assets Parquet (bundled × on-demand × GitHub Releases); avaliar separação dos scripts de build em pacote independente |

---

*Relatório gerado por: Project Analyst · Data Engineer · Data Scientist · Python Code Reviewer · Package Engineer · Documentation Reviewer*  
*Coordenação: GitHub Copilot (Claude Sonnet 4.6) — 8 de maio de 2026*
