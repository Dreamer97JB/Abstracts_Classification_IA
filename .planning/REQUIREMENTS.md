# Requirements: Abstracts Classification IA

**Defined:** 2026-04-02
**Core Value:** Deliver defensible automatic classifications over the client corpus using a canonical, article-grounded taxonomy with traceable data lineage and reviewable outputs.

## v1 Requirements

### Operations

- [x] **OPS-01**: Analyst can run named project entrypoints for audit, prepare, train, evaluate, predict, and analyze without editing notebook cells.
- [x] **OPS-02**: Analyst can keep notebooks as exploratory views while the script/module pipeline remains the source of truth.

### Corpus and Source Governance

- [x] **CORP-01**: Analyst can ingest Google, Scopus, Seed, and `Muestras` into normalized tables while preserving workbook, sheet, and source-corpus lineage.
- [x] **CORP-02**: Analyst can generate an overlap and duplicate report across corpora using title and DOI matching before training or full-corpus inference.
- [ ] **CORP-03**: Analyst can choose which corpora feed training, evaluation, and inference through config instead of notebook edits.

### Taxonomy and Label Governance

- [x] **TAXO-01**: Analyst can define a canonical theory taxonomy aligned to the six types in the Arbor article.
- [ ] **TAXO-02**: Analyst can map legacy spreadsheet labels from Seed and `Muestras` into the canonical taxonomy through versioned config files.
- [ ] **TAXO-03**: Analyst can detect and export inconsistent, blank, or unmapped labels for manual review before training.

### Theory Classification

- [x] **THEO-01**: Analyst can train and evaluate a baseline automatic classifier for the canonical theory taxonomy using the available labeled examples.
- [ ] **THEO-02**: Analyst can run batch theory classification over a chosen corpus and receive predicted canonical label, confidence, model version, run identifier, and lineage columns.
- [x] **THEO-03**: Analyst can choose between abstract-only and abstract-plus-keywords input variants through config so enrichment can be benchmarked explicitly.

### Evaluation

- [x] **EVAL-01**: Analyst can generate a theory metrics bundle with accuracy, macro F1, weighted F1, confusion matrix, and per-class performance for a labeled split.
- [ ] **EVAL-02**: Analyst can generate a methodology metrics bundle when reviewed methodology labels are available.
- [ ] **EVAL-03**: Analyst can export low-confidence and taxonomy-conflict cases using configurable thresholds and review rules.

### Methodology

- [ ] **METH-01**: Analyst can classify methodology as `NN`, `no empirico`, or `empirico`.
- [ ] **METH-02**: If methodology is `empirico`, analyst can classify the sub-type as `cualitativo` or `cuantitativo`.
- [ ] **METH-03**: Analyst can flag outliers or insufficient-evidence cases without forcing a false subtype.

### Analysis

- [ ] **ANLY-01**: Analyst can generate theme outputs that do not overwrite or blur the main theory and methodology outputs.
- [ ] **ANLY-02**: Analyst can generate correlation tables crossing canonical labels with keywords, authors, or other metadata for exploratory review.
- [ ] **ANLY-03**: Analyst can generate reference and author summaries associated with reviewed or predicted labels.

### Reporting

- [ ] **REPT-01**: Analyst can export client-ready result tables with simplified columns for theory classification, methodology, themes, and review status.
- [ ] **REPT-02**: Analyst can generate a milestone-ready report summarizing corpus audit, label mapping, training, evaluation, inference, and analytical outputs from a single run context.

## v2 Requirements

### Human Review

- **HREV-01**: Analyst can review and relabel low-confidence predictions in a structured feedback loop for future retraining.

### Taxonomy Expansion

- **TAXO-11**: Analyst can support hierarchical or multi-label theory classification if the client later needs families plus subtypes.

### Experiment Tracking

- **EXPT-01**: Analyst can compare experiments in a persistent registry or dashboard across multiple milestone iterations.

### Enrichment Features

- **ENRH-01**: Analyst can experiment with references, authors, and citation metadata as learned model features beyond the baseline abstract-plus-keywords contract.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Web app or API delivery | This milestone is about corpus governance and classification delivery, not serving infrastructure |
| Inventing a new theory taxonomy beyond the Arbor article and client files | The milestone should align to the provided conceptual source of truth |
| Automatically trusting unresolved spreadsheet label conflicts | `Seed` and `Muestras` require harmonization before training can be trusted |
| Real-time inference service | Batch and report-based workflows are sufficient for the immediate delivery need |
| Treating Google and Scopus as a single raw pool without provenance | The corpora play different roles and must remain traceable |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| OPS-01 | Phase 1 | Complete |
| OPS-02 | Phase 1 | Complete |
| CORP-01 | Phase 1 | Complete |
| CORP-02 | Phase 1 | Complete |
| TAXO-01 | Phase 1 | Complete |
| CORP-03 | Phase 2 | Pending |
| TAXO-02 | Phase 2 | Pending |
| TAXO-03 | Phase 2 | Pending |
| METH-01 | Phase 2 | Pending |
| METH-02 | Phase 2 | Pending |
| METH-03 | Phase 2 | Pending |
| THEO-01 | Phase 3 | Complete |
| THEO-03 | Phase 3 | Complete |
| EVAL-01 | Phase 3 | Complete |
| EVAL-02 | Phase 4 | Pending |
| ANLY-01 | Phase 4 | Pending |
| THEO-02 | Phase 5 | Pending |
| EVAL-03 | Phase 5 | Pending |
| ANLY-02 | Phase 5 | Pending |
| ANLY-03 | Phase 5 | Pending |
| REPT-01 | Phase 5 | Pending |
| REPT-02 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 22 total
- Mapped to phases: 22
- Unmapped: 0

---
*Requirements defined: 2026-04-02*
*Last updated: 2026-04-16 after completing Phase 3 baseline classifier execution*
