# SDD 01: Analytics Foundation

## 1. Objective

Create the deterministic bibliometric foundation for Scopus classified-corpus analytics.

This module must transform a classified Scopus-oriented input artifact into stable, testable, reusable analytics tables that can later be consumed by:

- network analysis
- Markdown/HTML reporting
- offline interactive delivery

This document defines the core data contracts only.

## 2. Scope

This task includes:

- bibliometric input loading
- column alias resolution
- normalized intermediate records
- reference splitting
- reference parsing
- cited-author extraction
- corpus-author normalization
- descriptive statistics
- frequency tables
- cross-matrices
- persisted CSV and JSON outputs

This task does not include:

- graph building
- GraphML export
- community detection
- interactive HTML UI
- dashboard/server work
- final client presentation UX

## 3. Architectural Boundary

New module required:

- `src/abstract_classifier/bibliometrics.py`

Optional supporting command:

- `src/abstract_classifier/commands/bibliometrics.py`

Optional orchestration integration:

- extend `src/abstract_classifier/analysis.py`
- extend `src/abstract_classifier/commands/analyze.py`

Hard boundary:

- `client_reporting.py` must not remain the place where reference parsing logic lives
- report rendering must not be mixed into the bibliometric computation module

## 4. Inputs

### 4.1 Minimum accepted input artifact

The module must accept a CSV artifact that is already classified and includes enough text and metadata to support analytics.

Minimum semantic fields:

- `record_id`
- `title` or title alias
- `abstract` or abstract alias
- `authors` or authors alias
- `references` or references alias
- theory label or prediction label

Preferred additional fields:

- `doi`
- `year`
- `author_keywords`
- `index_keywords`
- `source_dataset`
- `source_sheet`
- `predicted_canonical_id`
- `predicted_label_canonica`

### 4.2 Alias resolution

The module must resolve aliases through config, not hardcoded report logic.

Config file required:

- `configs/bibliometrics.toml`

Minimum alias groups:

- title
- abstract
- authors
- author keywords
- index keywords
- references
- doi
- year
- label id
- label name

## 5. Data Contracts

### 5.1 `BibliometricRecord`

Required contract:

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

Rules:

- immutable
- serializable into rows
- derived deterministically from input

### 5.2 `ParsedReference`

Required contract:

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

### 5.3 `AuthorMention`

Required contract:

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

### 5.4 `BibliometricArtifacts`

Required contract:

```python
@dataclass(frozen=True)
class BibliometricArtifacts:
    enriched_rows: pd.DataFrame
    parsed_references: pd.DataFrame
    corpus_author_frequency: pd.DataFrame
    cited_author_frequency: pd.DataFrame
    author_label_matrix: pd.DataFrame
    author_theme_matrix: pd.DataFrame
    theme_label_matrix: pd.DataFrame
    keyword_label_matrix: pd.DataFrame
    descriptive_stats: dict[str, object]
```

## 6. Required Public Functions

The module must expose these public functions:

```python
load_bibliometric_config(...)
resolve_bibliometric_columns(...)
build_bibliometric_records(...)
split_references(...)
guess_reference_style(...)
extract_doi(...)
extract_year(...)
extract_author_segment(...)
split_reference_authors(...)
normalize_author_name(...)
parse_references(...)
extract_cited_authors(...)
build_author_frequency(...)
build_author_label_matrix(...)
build_author_theme_matrix(...)
build_theme_label_matrix(...)
build_keyword_label_matrix(...)
build_descriptive_stats(...)
build_bibliometric_outputs(...)
```

## 7. Reference Parsing Rules

### 7.1 Supported style guesses

The parser must classify each reference into one of:

- `APA_LIKE`
- `IEEE_LIKE`
- `VANCOUVER_LIKE`
- `UNKNOWN`

### 7.2 DOI rule

The parser must attempt DOI extraction with regex.

If found:

- preserve original DOI text
- store a normalized lowercase DOI in downstream author/reference keys when needed

### 7.3 Year rule

The parser must extract a year only if it falls between:

- `1800`
- current calendar year

### 7.4 Author extraction rule

The parser must attempt to extract authors from the most likely author segment:

- before year when detectable
- before title fragment when style suggests that structure

### 7.5 Confidence rule

Allowed values:

- `HIGH`
- `MEDIUM`
- `LOW`
- `FAILED`

Assignment rules:

- `HIGH`: author plus year plus DOI or title evidence
- `MEDIUM`: author plus year
- `LOW`: partial author evidence only
- `FAILED`: no reliable author parse

### 7.6 Failure rule

Unparseable references must not crash the pipeline.

They must still be exported with:

- original raw reference
- `parse_confidence = FAILED`

## 8. Author Normalization Rules

Normalization must be conservative.

Required behavior:

- trim whitespace
- collapse duplicate spaces
- remove unnecessary punctuation
- preserve accents in display values
- produce `author_key` in lowercase, accent-insensitive form for grouping

Hard boundary:

- do not aggressively merge homonyms
- do not invent identity resolution beyond deterministic normalization

## 9. Required Metrics

### 9.1 Corpus author frequency

Definition:

- how many Scopus corpus articles an author appears on as an article author

### 9.2 Cited author frequency

Definition:

- total number of author mentions across parsed references

### 9.3 Article citation coverage

Definition:

- number of unique articles that cite an author at least once

Hard rule:

- do not collapse mention count and article count into one metric

## 10. Required Matrices

The module must generate:

### 10.1 Cited author x classification

Columns:

```text
cited_author_key,cited_author_display,label_id,label_name,article_count,mention_count,share_within_author,share_within_label
```

### 10.2 Theme x classification

Columns:

```text
theme,label_id,label_name,article_count,share_within_theme,share_within_label
```

### 10.3 Keyword x classification

Columns:

```text
keyword,keyword_source,label_id,label_name,article_count,keyword_count,share_within_keyword
```

Allowed `keyword_source` values:

- `AUTHOR_KEYWORD`
- `INDEX_KEYWORD`
- `TFIDF_TERM`
- `CLUSTER_TERM`

For this task:

- `AUTHOR_KEYWORD`
- `INDEX_KEYWORD`
- `TFIDF_TERM`

must be supported

`CLUSTER_TERM` may remain empty until task 03 or later work introduces clustering outputs.

### 10.4 Cited author x theme

Columns:

```text
cited_author_key,cited_author_display,theme,article_count,mention_count,share_within_author
```

## 11. Descriptive Statistics Contract

Required file:

- `descriptive_stats.json`

Required keys:

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
  "top_cited_authors": []
}
```

## 12. Required Outputs

Directory root:

- `reports/analytics/scopus/`

Required files:

- `descriptive_stats.json`
- `tables/client_results_enriched.csv`
- `tables/parsed_references.csv`
- `tables/author_frequency.csv`
- `tables/cited_author_frequency.csv`
- `tables/author_label_matrix.csv`
- `tables/author_theme_matrix.csv`
- `tables/theme_label_matrix.csv`
- `tables/keyword_label_matrix.csv`

## 13. Testing Requirements

Required tests:

- `tests/test_bibliometrics_reference_parser.py`
- `tests/test_bibliometrics_author_frequency.py`
- `tests/test_bibliometrics_matrices.py`
- `tests/test_bibliometrics_command.py`

Tests must verify:

- alias resolution
- parser tolerance on mixed formats
- correct separation of corpus authors vs cited authors
- correct percentage math
- stable failure behavior on malformed references

## 14. Non-Goals

This task must not:

- render HTML reports
- generate graph visualizations
- open a browser
- add a web server
- introduce LLM-driven metric computation

## 15. Acceptance Criteria

This task is complete only when:

1. A classified Scopus input artifact can be processed end to end.
2. Parsed references are exported without pipeline failure on malformed rows.
3. Corpus-author and cited-author metrics are clearly separated.
4. Required matrices are generated with test-covered percentage calculations.
5. `client_reporting.py` is no longer the owner of reference parsing behavior.
6. Outputs are reusable by later network and reporting tasks.
