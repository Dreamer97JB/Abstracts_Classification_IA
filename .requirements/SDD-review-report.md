# SDD Review Report: Bibliometrics and Interactive Scopus Analytics

Date: 2026-06-12
Scope reviewed:
- [.requirements/SDD-requirements.md](/d:/Development/Repositories/AI-models/Abstract-clasif/Abstracts_Classification_IA/.requirements/SDD-requirements.md)
- current roadmap and requirements
- current downstream analysis, reporting, and inference code

## Executive Summary

The SDD is directionally strong, but it is too broad to execute cleanly as one requirement file.

It mixes four different concerns:

1. Bibliometric data contracts and parsing
2. Statistical and network analytics
3. Written reporting outputs
4. Interactive presentation and delivery UX

The current codebase already supports classified-corpus exports, theme outputs, correlation tables, and Markdown/CSV reporting, but it does not yet have:

- a dedicated bibliometrics domain module
- robust reference parsing
- network modeling or GraphML export
- interactive analytics artifacts

Recommendation: split the SDD into a small requirement set, not because the idea is wrong, but because the implementation surfaces are different and the repo already separates work by phase and artifact contract.

## What Exists Today

The current reusable base is real and useful:

- [src/abstract_classifier/io/sources.py](/d:/Development/Repositories/AI-models/Abstract-clasif/Abstracts_Classification_IA/src/abstract_classifier/io/sources.py:12) already normalizes core source fields including `title`, `authors`, `doi`, `abstract`, `author_keywords`, `index_keywords`, `references`, and `year`.
- [src/abstract_classifier/inference.py](/d:/Development/Repositories/AI-models/Abstract-clasif/Abstracts_Classification_IA/src/abstract_classifier/inference.py:147) already produces classified corpus artifacts with lineage, scores, review flags, and `predictions.csv`.
- [src/abstract_classifier/analysis.py](/d:/Development/Repositories/AI-models/Abstract-clasif/Abstracts_Classification_IA/src/abstract_classifier/analysis.py:38) already orchestrates downstream analysis bundles over a classified artifact.
- [src/abstract_classifier/theme_analysis.py](/d:/Development/Repositories/AI-models/Abstract-clasif/Abstracts_Classification_IA/src/abstract_classifier/theme_analysis.py:69) already generates per-record themes plus a summary using keywords first and TF-IDF fallback.
- [src/abstract_classifier/client_reporting.py](/d:/Development/Repositories/AI-models/Abstract-clasif/Abstracts_Classification_IA/src/abstract_classifier/client_reporting.py:62) already writes:
  - `client_results.csv`
  - label x theme correlations
  - label x keyword correlations
  - author summary
  - reference summary
  - Markdown report

There are also real production-like artifacts under `reports/phase10/scopus_only_predict` and `reports/phase10/scopus_only_analyze`, which means the Scopus-only execution path already exists in artifact form.

## Main Gaps Against the SDD

### 1. `client_reporting.py` is carrying too much responsibility

This is the biggest architectural match with the SDD diagnosis.

- [src/abstract_classifier/client_reporting.py](/d:/Development/Repositories/AI-models/Abstract-clasif/Abstracts_Classification_IA/src/abstract_classifier/client_reporting.py:281) builds author summaries.
- [src/abstract_classifier/client_reporting.py](/d:/Development/Repositories/AI-models/Abstract-clasif/Abstracts_Classification_IA/src/abstract_classifier/client_reporting.py:320) builds reference summaries.
- [src/abstract_classifier/client_reporting.py](/d:/Development/Repositories/AI-models/Abstract-clasif/Abstracts_Classification_IA/src/abstract_classifier/client_reporting.py:411) renders the Markdown report.

That confirms the SDD concern: analytics logic and report rendering are coupled in one module.

### 2. Reference parsing is currently shallow

The current implementation is not yet bibliometrics-grade:

- [src/abstract_classifier/client_reporting.py](/d:/Development/Repositories/AI-models/Abstract-clasif/Abstracts_Classification_IA/src/abstract_classifier/client_reporting.py:616) extracts reference authors by splitting on `;` and taking the first comma-delimited fragment.

This is fine for lightweight summaries, but not enough for:

- style detection
- DOI extraction
- year extraction
- parsed reference outputs
- parse confidence
- author normalization across cited references

### 3. Theme logic partially overlaps the SDD, but not fully

- [src/abstract_classifier/theme_analysis.py](/d:/Development/Repositories/AI-models/Abstract-clasif/Abstracts_Classification_IA/src/abstract_classifier/theme_analysis.py:86) builds `theme_text` from `title + abstract`.
- [src/abstract_classifier/theme_analysis.py](/d:/Development/Repositories/AI-models/Abstract-clasif/Abstracts_Classification_IA/src/abstract_classifier/theme_analysis.py:215) uses author/index keywords as direct theme assignments before TF-IDF fallback.

So the repo already has a valid theme subsystem, but it does not yet match the SDD's fuller analytics text contract of:

- `title + abstract + author_keywords + index_keywords`

for clustering-oriented analysis.

### 4. No network analysis module exists yet

There is no `bibliometrics.py`, no `network_analysis.py`, and no CLI for bibliometrics in the current package.

That means the SDD is not an incremental config tweak. It is a genuine new subsystem.

### 5. No interactive presentation layer exists today

Current outputs are CSV, JSON, and Markdown. The repo does not currently expose:

- a dashboard command
- an offline interactive HTML analytics bundle
- a local app framework in base dependencies

`plotly` appears in GPU/WSL requirement files, but not in [requirements/base.txt](/d:/Development/Repositories/AI-models/Abstract-clasif/Abstracts_Classification_IA/requirements/base.txt:1), so interactive work is not yet part of the default local stack.

## Should the SDD Be Split?

Yes.

I recommend splitting it into 3 requirement files, with one optional fourth file if you want a stronger product boundary.

### Recommended split

1. `SDD-analytics-foundation.md`
Purpose:
- bibliometric records
- column resolution
- reference parsing
- author normalization
- frequency tables
- matrix outputs
- descriptive stats

Why:
- this is the deterministic data-contract core
- it should be test-heavy and independent from UI concerns

2. `SDD-network-analytics.md`
Purpose:
- co-citation
- co-author
- bibliographic coupling
- node/edge exports
- GraphML and metrics

Why:
- graph construction has its own dependencies, test shape, and performance concerns

3. `SDD-reporting-and-interactive-delivery.md`
Purpose:
- Markdown report
- HTML report
- interactive exploration artifacts
- author and statistics presentation UX

Why:
- this is where the user-facing delivery contract belongs
- it should consume computed artifacts, not own the analytics logic

4. Optional: `SDD-roadmap-alignment.md`
Purpose:
- map this work onto current repo phases
- define whether this becomes candidate Phase 11 or Phase 11 + 12 work

Why:
- the current roadmap explicitly says dashboard work is deferred until after the improved production CSV

## Best Fit With The Existing Roadmap

This repo's roadmap was updated on 2026-05-20 and still places:

- Phase 10 as "Production Re-run and Improved Classified CSV"
- Phase 11 as candidate "Descriptive Statistics and Data Quality Dashboard"
- Phase 12 as candidate "Delivery Packaging and Executive Handoff"

That means your SDD is best treated as post-Phase-10 work, not as an in-place extension of the currently active release gate.

Practical mapping:

- analytics foundation + deterministic bibliometrics = Phase 11 core
- interactive HTML/statistics experience = late Phase 11 or Phase 12

## Recommended Delivery Shape For The Interactive Part

Given the repo's current design, I do not recommend a web app as the first implementation.

The repo is artifact-first, CLI-first, and explicitly lists "Web app or API delivery" as out of scope in the current requirements.

Best first interactive delivery:

- generate an offline HTML analytics bundle from the Scopus classified corpus
- keep it fully reproducible from a CLI command
- make it openable locally in a browser with no server required

### Why this is the right first move

- matches the current artifact workflow
- easier to version and deliver to the client
- avoids introducing app hosting and session state too early
- still gives an interactive way to explore:
  - top authors
  - cited authors
  - label distributions
  - theme distributions
  - keyword filters
  - network previews

### Suggested interactive outputs

- `reports/analytics/scopus/index.html`
- `reports/analytics/scopus/data/*.csv`
- `reports/analytics/scopus/data/*.json`
- `reports/analytics/scopus/networks/*.graphml`
- `reports/analytics/scopus/networks/*.html`

### Suggested first interactive screens

1. Corpus overview
- total articles
- label distribution
- theme distribution
- keyword coverage
- reference parse success

2. Authors
- top corpus authors
- top cited authors
- author x label table
- author x theme table

3. Themes and keywords
- theme x label
- keyword x label
- filterable article counts

4. Networks
- co-citation preview
- co-author preview
- bibliographic coupling preview

## Recommended Implementation Order

1. Extract bibliometric logic out of `client_reporting.py`.
2. Add deterministic parsed-reference outputs and tests.
3. Add author/theme/label matrix outputs.
4. Add descriptive stats JSON and richer Markdown report.
5. Add network exports.
6. Add offline interactive HTML bundle that consumes the saved CSV/JSON artifacts.

This order keeps the data contracts stable before presentation work.

## Concrete Repo-Level Recommendations

### Architecture

- Add `src/abstract_classifier/bibliometrics.py`
- Add `src/abstract_classifier/network_analysis.py`
- Add `src/abstract_classifier/analytics_reporting.py`
- Add `src/abstract_classifier/commands/bibliometrics.py`
- Keep `client_reporting.py` as a compatibility layer at most, or retire it after migration

### Config

- Add `configs/bibliometrics.toml`
- keep aliases for Scopus column resolution there, not inside report code

### Tests

New tests should be added before UI work:

- `tests/test_bibliometrics_reference_parser.py`
- `tests/test_bibliometrics_author_frequency.py`
- `tests/test_bibliometrics_matrices.py`
- `tests/test_network_analysis.py`
- `tests/test_bibliometrics_command.py`

### Dependencies

Base stack likely needs expansion for the interactive requirement.

Most likely additions:

- `networkx`
- `plotly`

Possibly later:

- `pyvis` for graph HTML previews, if you want lightweight standalone network views

## Decision

The SDD should be split.

Not because it is too ambitious, but because it spans:

- deterministic analytics contracts
- graph analytics
- client-facing delivery

Those should evolve as separate requirement files with explicit dependencies and acceptance criteria.

## Suggested Next Step

Create these files:

1. `.requirements/SDD-analytics-foundation.md`
2. `.requirements/SDD-network-analytics.md`
3. `.requirements/SDD-reporting-and-interactive-delivery.md`

If you want, the next step I can take is to draft those three requirement files directly from the current SDD and align them to the repo's Phase 10 -> Phase 11 boundary.
