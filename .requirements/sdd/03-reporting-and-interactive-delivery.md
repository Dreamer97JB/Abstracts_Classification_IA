# SDD 03: Reporting and Interactive Delivery

## 1. Objective

Deliver a client-consumable analytics package for the classified Scopus corpus, including:

- written report
- HTML report
- offline interactive analytics experience

This task consumes outputs from deterministic analytics and, when available, network analytics.

## 2. Dependency

This task depends on:

- `01-analytics-foundation.md`

Optional dependency:

- `02-network-analytics.md`

Hard rule:

- reporting and interactivity must consume persisted artifacts
- they must not recompute core bibliometric metrics in presentation code

## 3. Scope

This task includes:

- Markdown report
- HTML report
- offline interactive HTML bundle
- filterable author/statistics presentation
- artifact packaging for local browser review

This task does not include:

- hosted web application
- API service
- authentication
- multi-user review workflows

## 4. Architectural Boundary

New module required:

- `src/abstract_classifier/analytics_reporting.py`

Optional command:

- `src/abstract_classifier/commands/bibliometrics.py`

or extension of:

- `src/abstract_classifier/commands/analyze.py`

Hard boundaries:

- presentation code must not own reference parsing
- presentation code must not compute centrality metrics directly
- `client_reporting.py` may be migrated or deprecated, but should not remain a God module

## 5. Delivery Strategy Rule

The first interactive implementation must be offline-first.

Required delivery style:

- generated HTML files that open locally in a browser

Explicitly not required for the first version:

- Streamlit app
- Dash app
- Flask/FastAPI app
- notebook-only interaction

Reason:

- the repo is CLI-first and artifact-first
- current project scope defers web-app delivery

## 6. Required Public Functions

The module must expose:

```python
build_analytics_report(...)
render_markdown_report(...)
render_html_report(...)
build_interactive_bundle(...)
```

## 7. Required Written Outputs

Required files:

- `reports/analytics/scopus/scopus_analytics_report.md`
- `reports/analytics/scopus/scopus_analytics_report.html`

## 8. Report Structure Contract

The Markdown and HTML reports must contain these sections:

1. Executive summary
2. Corpus coverage and descriptive stats
3. Classification distribution
4. Themes and keywords
5. Corpus authors
6. Cited authors
7. Analytical crosses
8. Networks
9. Data quality and limitations
10. Conclusions

## 9. Narrative Safety Rules

### 9.1 No invented claims

The report must not state findings that are unsupported by deterministic outputs.

### 9.2 Coverage disclosure

If reference parsing coverage is weak, the report must say so.

### 9.3 Theme claim rule

Claims such as "X% of articles are about covid" must only appear if the operational definition is explicit.

Examples of valid basis:

- keyword match
- TF-IDF-derived theme
- configured theme rule

The report must make the basis visible.

### 9.4 Limitation rule

The report must include a data-quality section covering:

- unparsed references
- missing abstracts
- missing keywords
- author ambiguity risk
- graph filtering assumptions

## 10. Required Interactive Bundle

Root directory:

- `reports/analytics/scopus/interactive/`

Required main file:

- `reports/analytics/scopus/interactive/index.html`

Required supporting assets may include:

- `data/*.csv`
- `data/*.json`
- `assets/*.js`
- `assets/*.css`

Hard rule:

- the interactive bundle must open locally without a running Python server if technically feasible with chosen assets

## 11. Required Interactive Views

### 11.1 Overview

Must show:

- total articles
- label distribution
- theme distribution
- keyword coverage
- references coverage
- parse success rate

### 11.2 Authors

Must show:

- top corpus authors
- top cited authors
- author x label relationships
- author x theme relationships

### 11.3 Themes and keywords

Must show:

- theme x label matrix
- keyword x label matrix
- simple filterable views

### 11.4 Networks

If network outputs exist, show:

- co-citation preview
- co-author preview
- bibliographic coupling preview

If network outputs do not exist yet:

- render a clear "not available" state
- do not fail the whole interactive bundle

## 12. UX Rules

### 12.1 Offline-first rule

Everything must be browsable from generated local artifacts.

### 12.2 Deterministic-data rule

Interactive views must consume persisted CSV/JSON outputs.

### 12.3 Scaled-preview rule

Large tables and graphs must be summarized or filtered for usability.

### 12.4 No hidden server dependency

Do not create a solution that silently requires localhost unless that is explicitly declared and accepted later.

## 13. Suggested Dependencies

Base-compatible additions may include:

- `plotly`

Optional later additions:

- `networkx`
- `pyvis`

Hard rule:

- dependency additions must be justified by actual artifact needs
- do not add a full app framework for the first offline HTML version

## 14. Required Outputs

Required files:

- `reports/analytics/scopus/scopus_analytics_report.md`
- `reports/analytics/scopus/scopus_analytics_report.html`
- `reports/analytics/scopus/interactive/index.html`

Required data payloads for interactivity:

- descriptive stats
- author frequency
- cited author frequency
- author x label matrix
- author x theme matrix
- theme x label matrix
- keyword x label matrix

Optional network payloads:

- network nodes
- network edges

## 15. Testing Requirements

Required tests should verify:

- report generation does not fail on sparse data
- interactive bundle files are produced
- missing optional network artifacts do not break bundle generation
- report sections are present
- narrative logic reflects actual metric sources

Suggested tests:

- `tests/test_analytics_reporting.py`
- `tests/test_interactive_bundle.py`

## 16. Non-Goals

This task must not:

- deploy a web service
- require cloud hosting
- implement user login
- mix raw analytics recomputation into HTML templates

## 17. Acceptance Criteria

This task is complete only when:

1. Markdown and HTML analytics reports are generated from persisted artifacts.
2. The report includes author and general statistics over the classified Scopus corpus.
3. An offline interactive HTML bundle is generated and opens locally.
4. The interactive bundle presents authors, themes, keywords, and corpus-wide statistics.
5. Optional network views degrade gracefully when graph outputs are absent.
6. The implementation remains artifact-driven and reproducible.
