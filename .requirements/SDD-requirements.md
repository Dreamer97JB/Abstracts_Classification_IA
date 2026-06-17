# SDD — Extensión Bibliométrica, Temática y de Redes para Corpus Scopus

## 1. Objetivo

Añadir al proyecto actual un módulo de análisis bibliométrico y temático sobre el corpus Scopus para obtener:

1. Frecuencia de autores citados y autores del corpus.
2. Extracción de autores desde referencias/citaciones en formatos APA, IEEE u otros formatos similares.
3. Cluster de palabras, palabras clave y temáticas.
4. Matrices cruzadas entre etiquetas/tipología, autores, temas, palabras clave y clasificaciones.
5. Estadística descriptiva simple del corpus.
6. Redes de citación, co-citación, coautoría y relación entre autores.
7. Reporte escrito con hallazgos cuantitativos, por ejemplo:

   * “El 30% de artículos habla de covid.”
   * “De ese 30%, el 50% está clasificado como realismo moderado/crítico.”
   * “El autor X aparece mayoritariamente en artículos clasificados como constructivismo fuerte/relativismo.”

## 2. Diagnóstico técnico

El proyecto ya tiene piezas relevantes:

* `theme_analysis.py`: análisis de temáticas usando TF-IDF.
* `client_reporting.py`: generación de reportes, resumen de autores y referencias.
* `taxonomy.py`: taxonomía canónica de seis clases.
* `inference.py`: inferencia de clasificación teórica.
* `io/sources.py`: normalización de fuentes con aliases para título, autores, DOI y año.

El problema es que el análisis bibliométrico actual está demasiado mezclado con `client_reporting.py`. Eso es mal diseño.

### Code smells actuales

1. **God module parcial en `client_reporting.py`**
   Mezcla reporting, parsing de autores, parsing de referencias, correlaciones y render markdown. Eso rompe SRP.

2. **Parsing de referencias débil**
   Extraer autores desde referencias con regex simple sirve para demo, no para análisis confiable tipo Mendeley/Scopus.

3. **Falta de modelo intermedio bibliométrico**
   No existe una capa clara para representar:

   * referencia cruda,
   * referencia parseada,
   * autores normalizados,
   * menciones,
   * relación artículo → referencia,
   * relación artículo → autor citado.

4. **Falta de redes explícitas**
   El sistema no modela nodos/aristas para redes de citación, coautoría, co-citación o bibliographic coupling.

5. **Riesgo de porcentajes falsos**
   No se debe decir “30% habla de covid” si no se define si “habla de covid” viene de keyword exacta, tema inferido, cluster semántico o texto completo.

## 3. The Better Way

Crear una capa nueva llamada `bibliometrics`, separada de `client_reporting`, y conectarla al pipeline existente.

Arquitectura propuesta:

```text
Scopus source
   ↓
io/sources.py
   ↓
normalized corpus
   ↓
inference.py ───────────────┐
theme_analysis.py ──────────┤
methodology_pipeline.py ────┤
bibliometrics.py ───────────┤
network_analysis.py ────────┤
   ↓                        ↓
analytics_reporting.py → report.md / report.html / csv / json / graph files
```

`client_reporting.py` debe consumir outputs ya calculados, no calcularlo todo internamente.

## 4. Alcance funcional

### 4.1 Frecuencia de autores

El sistema debe calcular tres frecuencias distintas:

| Métrica                     | Fuente                                    | Significado                                              |
| --------------------------- | ----------------------------------------- | -------------------------------------------------------- |
| `corpus_author_count`       | columna `Authors`                         | Veces que un autor aparece como autor de artículo Scopus |
| `cited_author_count`        | columna `References` / `Cited References` | Veces que un autor aparece citado en bibliografía        |
| `article_citation_coverage` | referencias parseadas por artículo        | Cuántos artículos citan a ese autor al menos una vez     |

No mezclar estas métricas. Son cosas distintas.

### 4.2 Extracción de autores desde referencias

Entrada esperada:

```text
Smith, J., & Brown, P. (2020). Title...
[1] J. Smith and P. Brown, "Title", Journal, 2020.
Smith J, Brown P. Title. Journal. 2020.
```

Salida normalizada:

```csv
record_id,reference_index,reference_raw,style_guess,first_author,year,title_fragment,doi,authors_raw,authors_normalized,parse_confidence
```

Reglas mínimas:

1. Detectar DOI con regex.
2. Detectar año entre 1800 y año actual.
3. Detectar estilo probable:

   * `APA_LIKE`
   * `IEEE_LIKE`
   * `VANCOUVER_LIKE`
   * `UNKNOWN`
4. Extraer autores antes del año o antes del título.
5. Normalizar nombres:

   * quitar dobles espacios,
   * quitar puntuación innecesaria,
   * conservar tildes,
   * generar `author_key` en minúscula sin acentos para deduplicación.
6. Asignar `parse_confidence`:

   * `HIGH`: autor + año + DOI o título.
   * `MEDIUM`: autor + año.
   * `LOW`: solo fragmento de autor.
   * `FAILED`: no parseable.

### 4.3 Matrices solicitadas

#### Matriz autor citado × clasificación

Permite responder: “Autores referenciados en cuál realismo”.

```csv
cited_author_key,cited_author_display,label_id,label_name,article_count,mention_count,share_within_author,share_within_label
```

Ejemplo conceptual:

| Autor citado | Realismo fuerte | Realismo moderado/crítico | Constructivismo fuerte | Total |
| ------------ | --------------: | ------------------------: | ---------------------: | ----: |
| Merton       |               2 |                        15 |                      1 |    18 |
| Latour       |               0 |                         3 |                     22 |    25 |

#### Matriz tema × clasificación

```csv
theme,label_id,label_name,article_count,share_within_theme,share_within_label
```

Sirve para frases tipo:

> El 30% de artículos habla de covid; dentro de ese subconjunto, el 50% está clasificado como realismo moderado/crítico.

#### Matriz keyword × clasificación

```csv
keyword,keyword_source,label_id,label_name,article_count,keyword_count,share_within_keyword
```

`keyword_source` debe distinguir:

* `AUTHOR_KEYWORD`
* `INDEX_KEYWORD`
* `TFIDF_TERM`
* `CLUSTER_TERM`

#### Matriz autor citado × tema

```csv
cited_author_key,cited_author_display,theme,article_count,mention_count,share_within_author
```

#### Matriz programa/realismo × autor representativo

Opcional, si se desea conectar con la tipología teórica base:

```csv
program_name,representative_author,label_id,label_name,source
```

## 5. Clusters de palabras y temáticas

### 5.1 Fuentes de texto

Para cada artículo se debe construir un texto analítico:

```text
title + abstract + author_keywords + index_keywords
```

No usar referencias bibliográficas para cluster de temas del artículo, porque contaminaría el contenido con títulos de libros/artículos citados.

### 5.2 Métodos mínimos

Implementar dos niveles:

#### Nivel 1 — Determinístico

Usar TF-IDF por artículo y por grupo de clasificación:

```text
label_id → top términos TF-IDF
theme → top términos TF-IDF
```

Ventaja: reproducible, barato y suficiente para estadística descriptiva.

#### Nivel 2 — Clustering semántico opcional

Generar embeddings por artículo y clusterizar:

```text
article_text → embedding → clustering → cluster_id
```

El SDD no debe obligar a usar LLM. Si se usan embeddings, deben ser opcionales y cacheados.

### 5.3 Outputs

```csv
word_clusters.csv
```

Columnas:

```csv
cluster_id,cluster_label,term,term_score,term_count,article_count,dominant_label_id,dominant_label_name,dominant_theme
```

```csv
article_clusters.csv
```

Columnas:

```csv
record_id,cluster_id,cluster_label,cluster_score,label_id,label_name,themes,keywords
```

## 6. Redes de citación y relación entre autores

### 6.1 Tipos de redes

Implementar cuatro redes, no una sola:

#### 1. Red artículo → autor citado

Nodo artículo conectado con autores citados.

```text
Article A → Latour
Article A → Bloor
Article B → Latour
```

#### 2. Red de co-citación de autores

Dos autores están relacionados si aparecen citados en el mismo artículo.

```text
Latour -- Bloor, weight = número de artículos que citan a ambos
```

#### 3. Red de coautoría

Autores del corpus relacionados si escriben juntos un artículo Scopus.

```text
Autor A -- Autor B, weight = artículos coautorados
```

#### 4. Bibliographic coupling

Dos artículos están relacionados si comparten autores citados, DOI citado o referencia.

```text
Article A -- Article B, weight = referencias compartidas
```

### 6.2 Formato de nodos

```csv
network_nodes.csv
```

Columnas:

```csv
node_id,node_type,label,display_name,count,dominant_label_id,dominant_label_name,degree,betweenness,pagerank,community_id
```

`node_type`:

* `ARTICLE`
* `CORPUS_AUTHOR`
* `CITED_AUTHOR`
* `KEYWORD`
* `THEME`
* `LABEL`

### 6.3 Formato de aristas

```csv
network_edges.csv
```

Columnas:

```csv
source,target,edge_type,weight,evidence_count,source_records
```

`edge_type`:

* `ARTICLE_CITES_AUTHOR`
* `CO_CITED_AUTHOR`
* `CO_AUTHOR`
* `ARTICLE_BIBLIOGRAPHIC_COUPLING`
* `AUTHOR_THEME`
* `AUTHOR_LABEL`
* `KEYWORD_LABEL`

### 6.4 Métricas de red

Calcular mínimo:

* `degree`
* `weighted_degree`
* `betweenness`
* `pagerank`
* `community_id`

Exportar:

```text
reports/analytics/networks/co_citation_authors.graphml
reports/analytics/networks/co_citation_authors.html
reports/analytics/networks/co_author.graphml
reports/analytics/networks/bibliographic_coupling.graphml
```

GraphML permite abrir en Gephi. HTML permite revisión rápida en navegador/Colab.

## 7. Estadística descriptiva simple

Generar `descriptive_stats.json` y sección markdown con:

```json
{
  "total_articles": 0,
  "articles_with_abstract": 0,
  "articles_with_keywords": 0,
  "articles_with_references": 0,
  "total_corpus_authors": 0,
  "total_cited_authors": 0,
  "total_references_raw": 0,
  "total_references_parsed": 0,
  "reference_parse_success_rate": 0.0,
  "labels_distribution": {},
  "themes_distribution": {},
  "top_keywords": [],
  "top_cited_authors": [],
  "top_word_clusters": []
}
```

## 8. Reporte escrito

Generar:

```text
reports/analytics/scopus_analytics_report.md
reports/analytics/scopus_analytics_report.html
```

Estructura:

```markdown
# Informe de análisis bibliométrico y temático — Corpus Scopus

## 1. Resumen ejecutivo
- Total de artículos analizados.
- Cobertura de abstracts, keywords y referencias.
- Clasificación dominante.
- Temas dominantes.
- Autores citados más frecuentes.
- Clusters principales.

## 2. Distribución de clasificaciones
Tabla y gráfico.

## 3. Temáticas más repetidas
Top temas y participación porcentual.

## 4. Palabras clave más repetidas
Separar Author Keywords, Index Keywords y términos TF-IDF.

## 5. Autores más citados
Tabla con frecuencia absoluta y porcentaje.

## 6. Autores por tipo de realismo
Matriz autor × clasificación.

## 7. Cruces analíticos
Ejemplos:
- covid × realismo
- keyword × clasificación
- tema × clasificación
- autor citado × clasificación
- autor citado × tema

## 8. Redes
- Red de co-citación.
- Red de coautoría.
- Red de bibliographic coupling.
- Comunidades detectadas.
- Autores puente.

## 9. Calidad de datos
- Referencias no parseadas.
- Artículos sin keywords.
- Artículos sin abstract.
- Ambigüedad de autores.
- Recomendaciones de limpieza.

## 10. Conclusiones
Hallazgos principales y limitaciones.
```

## 9. Nuevos módulos propuestos

### 9.1 `src/abstract_classifier/bibliometrics.py`

Responsabilidad: parsing bibliométrico.

Funciones públicas:

```python
load_bibliometric_config(...)
build_bibliometric_outputs(...)
parse_references(...)
extract_cited_authors(...)
normalize_author_name(...)
build_author_frequency(...)
build_author_label_matrix(...)
build_author_theme_matrix(...)
```

No debe renderizar reportes. No debe generar gráficos.

### 9.2 `src/abstract_classifier/network_analysis.py`

Responsabilidad: construir grafos y métricas.

Funciones públicas:

```python
build_network_outputs(...)
build_cocitation_graph(...)
build_coauthor_graph(...)
build_bibliographic_coupling_graph(...)
compute_network_metrics(...)
export_network_files(...)
```

### 9.3 `src/abstract_classifier/analytics_reporting.py`

Responsabilidad: reporte final.

Funciones públicas:

```python
build_analytics_report(...)
render_markdown_report(...)
render_html_report(...)
```

### 9.4 `src/abstract_classifier/commands/bibliometrics.py`

Nuevo comando CLI:

```bash
python -m abstract_classifier bibliometrics \
  --input reports/inference/latest/predictions.csv \
  --source scopus \
  --output-dir reports/analytics/scopus
```

### 9.5 Extensión de `commands/analyze.py`

Agregar flag:

```bash
python -m abstract_classifier analyze \
  --input reports/inference/latest/predictions.csv \
  --include-bibliometrics \
  --output-dir reports/analytics/scopus
```

## 10. Configuración

Crear:

```text
configs/bibliometrics.toml
```

Contenido esperado:

```toml
[input]
source_dataset = "scopus"

[columns]
title = ["Title", "Article Title", "Título"]
abstract = ["Abstract", "Resumen"]
authors = ["Authors", "Author full names", "Autores"]
author_keywords = ["Author Keywords", "Keywords"]
index_keywords = ["Index Keywords", "Indexed Keywords"]
references = ["References", "Cited References", "Bibliography", "Referencias"]
doi = ["DOI"]
year = ["Year", "Publication Year", "Año"]

[references]
split_strategy = "auto"
min_author_token_length = 3
min_parse_confidence = "LOW"

[themes]
min_term_frequency = 2
max_terms = 200
ngram_min = 1
ngram_max = 3

[networks]
min_edge_weight = 2
max_nodes_html = 300
compute_betweenness = true
community_detection = true

[report]
top_n_authors = 30
top_n_keywords = 30
top_n_themes = 30
top_n_clusters = 20
```

## 11. Modelo de datos intermedio

### 11.1 `BibliometricRecord`

```python
@dataclass(frozen=True)
class BibliometricRecord:
    record_id: str
    title: str
    abstract: str
    year: int | None
    doi: str | None
    corpus_authors: tuple[str, ...]
    author_keywords: tuple[str, ...]
    index_keywords: tuple[str, ...]
    references_raw: tuple[str, ...]
    label_id: str | None
    label_name: str | None
    themes: tuple[str, ...]
```

### 11.2 `ParsedReference`

```python
@dataclass(frozen=True)
class ParsedReference:
    record_id: str
    reference_index: int
    reference_raw: str
    style_guess: str
    first_author: str | None
    year: int | None
    title_fragment: str | None
    doi: str | None
    authors: tuple[str, ...]
    parse_confidence: str
```

### 11.3 `AuthorMention`

```python
@dataclass(frozen=True)
class AuthorMention:
    record_id: str
    author_key: str
    author_display: str
    mention_source: str
    label_id: str | None
    theme: str | None
```

`mention_source`:

* `CORPUS_AUTHOR`
* `CITED_AUTHOR`

## 12. Reglas de cálculo

### 12.1 Porcentaje de artículos por tema

```text
theme_article_share = artículos_con_tema / total_artículos
```

### 12.2 Porcentaje de una clasificación dentro de un tema

```text
label_share_within_theme = artículos_con_tema_y_label / artículos_con_tema
```

Ejemplo:

```text
total_articles = 100
articles_with_covid = 30
articles_with_covid_and_realism = 15

covid_share = 30 / 100 = 30%
realism_within_covid = 15 / 30 = 50%
```

### 12.3 Frecuencia de autor citado

```text
cited_author_count = número total de menciones en referencias
cited_author_article_count = número de artículos únicos donde aparece citado
```

No usar solo `mention_count`, porque un artículo puede citar varias obras del mismo autor.

### 12.4 Red de co-citación

Para cada artículo:

```text
cited_authors = autores citados únicos del artículo
crear combinaciones de pares
sumar +1 al peso de cada par
```

## 13. Outputs obligatorios

Directorio:

```text
reports/analytics/scopus/
```

Archivos:

```text
descriptive_stats.json
scopus_analytics_report.md
scopus_analytics_report.html

tables/client_results_enriched.csv
tables/parsed_references.csv
tables/author_frequency.csv
tables/cited_author_frequency.csv
tables/author_label_matrix.csv
tables/author_theme_matrix.csv
tables/theme_label_matrix.csv
tables/keyword_label_matrix.csv
tables/word_clusters.csv
tables/article_clusters.csv

networks/network_nodes.csv
networks/network_edges.csv
networks/co_citation_authors.graphml
networks/co_author.graphml
networks/bibliographic_coupling.graphml
networks/co_citation_authors.html
```

## 14. Integración con pipeline actual

### Entrada mínima

El módulo debe aceptar un DataFrame ya clasificado, con columnas posibles:

```text
record_id
title
abstract
authors
author_keywords
index_keywords
references
doi
year
predicted_label_id
predicted_label_name
theme
themes
```

Debe resolver aliases mediante configuración.

### Salida hacia reporting

`client_reporting.py` no debe parsear referencias. Debe recibir:

```python
bibliometric_artifacts.parsed_references
bibliometric_artifacts.author_frequency
bibliometric_artifacts.author_label_matrix
bibliometric_artifacts.theme_label_matrix
bibliometric_artifacts.network_summary
```

## 15. Estrategia de implementación para Codex

### Paso 1 — Crear contratos

Crear dataclasses y tests unitarios para:

* `BibliometricRecord`
* `ParsedReference`
* `AuthorMention`
* `BibliometricArtifacts`

### Paso 2 — Resolver columnas Scopus

Implementar:

```python
resolve_bibliometric_columns(frame, config)
```

Debe fallar con error claro si no encuentra columnas mínimas:

* título o abstract,
* autores,
* referencias,
* label o clasificación.

### Paso 3 — Parser de referencias

Implementar parser tolerante:

1. `split_references(raw)`
2. `guess_reference_style(reference)`
3. `extract_doi(reference)`
4. `extract_year(reference)`
5. `extract_author_segment(reference, style_guess, year)`
6. `split_reference_authors(author_segment)`
7. `normalize_author_name(author)`

### Paso 4 — Frecuencias

Implementar:

* corpus authors,
* cited authors,
* authors by label,
* authors by theme.

### Paso 5 — Matrices

Implementar matrices con `groupby` y porcentajes.

### Paso 6 — Clusters de palabras

Reusar lógica de `theme_analysis.py` cuando sea posible.

No duplicar normalización de términos.

### Paso 7 — Redes

Implementar NetworkX encapsulado en `network_analysis.py`.

No mezclar NetworkX con reporting.

### Paso 8 — Reporte

Generar markdown primero. HTML puede ser conversión simple o template.

### Paso 9 — CLI

Agregar comando `bibliometrics`.

### Paso 10 — Tests

Agregar tests:

```text
tests/test_bibliometrics_reference_parser.py
tests/test_bibliometrics_author_frequency.py
tests/test_bibliometrics_matrices.py
tests/test_network_analysis.py
tests/test_bibliometrics_command.py
```

## 16. Criterios de aceptación

### Parsing

* Dado un set de referencias APA, IEEE y Vancouver-like, el sistema extrae autores y año con confianza `HIGH` o `MEDIUM`.
* Las referencias no parseables no rompen el pipeline; se exportan con `parse_confidence = FAILED`.

### Frecuencias

* El sistema diferencia autores del corpus y autores citados.
* La misma persona con variantes simples de nombre se consolida en un `author_key`.

### Matrices

* Se genera matriz autor citado × clasificación.
* Se genera matriz tema × clasificación.
* Se genera matriz keyword × clasificación.
* Los porcentajes suman correctamente dentro de su dimensión.

### Redes

* Se genera red de co-citación.
* Se genera red de coautoría.
* Se genera red de bibliographic coupling.
* Se exportan nodos, aristas y GraphML.

### Reporte

* El reporte incluye estadística descriptiva simple.
* El reporte incluye top autores citados.
* El reporte incluye top temas y top keywords.
* El reporte incluye cruces interpretables con clasificación.
* El reporte no inventa conclusiones cuando la cobertura de datos sea baja.

## 17. Riesgos y mitigaciones

| Riesgo                                       | Impacto | Mitigación                                            |
| -------------------------------------------- | ------- | ----------------------------------------------------- |
| Referencias Scopus vienen en formatos mixtos | Alto    | Parser tolerante + confidence score                   |
| Autores homónimos                            | Medio   | Normalización conservadora, no fusionar agresivamente |
| Variantes de nombre                          | Alto    | `author_key` normalizado + tabla de aliases opcional  |
| Keywords vacías                              | Medio   | fallback TF-IDF desde título + abstract               |
| Gráficos inmanejables                        | Medio   | filtro `min_edge_weight` y `max_nodes_html`           |
| Conclusiones falsas por baja cobertura       | Alto    | sección obligatoria de calidad de datos               |

## 18. Decisión arquitectónica

No usar un LLM como núcleo del análisis.

Razón: este requerimiento es bibliométrico/estadístico. Debe ser reproducible. El LLM puede ayudar a nombrar clusters o redactar conclusiones, pero no debe calcular métricas ni decidir frecuencias.

Pipeline correcto:

```text
Deterministic parsing + statistics + network analysis + optional embeddings
```

## 19. Definition of Done

El desarrollo se considera completo cuando:

1. El comando `bibliometrics` corre sobre el corpus Scopus.
2. Se generan todos los CSV obligatorios.
3. Se genera reporte markdown y HTML.
4. Se generan GraphML y HTML de redes.
5. Existen tests unitarios para parser, matrices y redes.
6. Los porcentajes de los cruces son verificables con tests.
7. El módulo no aumenta la responsabilidad de `client_reporting.py`.
8. El pipeline actual de clasificación no se rompe.
