# Roadmap: Abstracts Classification IA

## Overview

This milestone turns the newly delivered client corpora, labeled subsets, and Arbor typology into a canonical classification pipeline. The work begins by locking the source-of-truth taxonomy and corpus contracts, then harmonizes legacy labels, then builds a baseline theory classifier, then adds methodology and theme outputs, and finally produces full-corpus inference plus client-facing analytical deliverables.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [x] **Phase 1: Canonical Taxonomy and Corpus Contracts** - Establish script entrypoints, source manifests, overlap rules, and the canonical theory taxonomy.
- [x] **Phase 2: Label Harmonization and Reviewed Gold Set Assembly** - Reconcile Seed and `Muestras`, define methodology labels, and produce governed training/evaluation tables.
- [ ] **Phase 3: Baseline Theory Classifier** - Implement the first canonical theory classification path with explicit benchmarks and metrics.
- [ ] **Phase 4: Methodology and Theme Pipeline** - Add methodology classification and optional theme outputs without polluting the theory contract.
- [ ] **Phase 5: Full-Corpus Inference and Client Deliverables** - Run inference over the selected corpora and generate review, correlation, and delivery-ready outputs.

## Phase Details

### Phase 1: Canonical Taxonomy and Corpus Contracts
**Goal**: Lock the semantic source of truth and the dataset contracts before any training work starts, while also establishing the script surface that replaces notebook-only execution.
**Depends on**: Nothing (first phase)
**Requirements**: [OPS-01, OPS-02, CORP-01, CORP-02, TAXO-01]
**Success Criteria** (what must be TRUE):
  1. Analyst can identify and run named project entrypoints for audit, prepare, train, evaluate, predict, and analyze.
  2. Google, Scopus, Seed, and `Muestras` are represented through explicit source manifests with lineage fields and overlap rules.
  3. The repo contains a canonical theory taxonomy config aligned to the Arbor article rather than spreadsheet shorthand alone.
**Plans**: 3 plans

Plans:
- [x] 01-01: Create package skeleton, config surface, and script entrypoints for the new classification workflow
- [x] 01-02: Implement source manifests and overlap audit for Google, Scopus, Seed, and `Muestras`
- [x] 01-03: Define canonical theory taxonomy config from the Arbor article and inventory legacy label aliases

### Phase 2: Label Harmonization and Reviewed Gold Set Assembly
**Goal**: Convert the legacy labeled spreadsheets into a governed supervised dataset with explicit canonical mappings, methodology rules, and review queues.
**Depends on**: Phase 1
**Requirements**: [CORP-03, TAXO-02, TAXO-03, METH-01, METH-02, METH-03]
**Success Criteria** (what must be TRUE):
  1. Analyst can transform Seed and `Muestras` into reviewed canonical-label tables without manual spreadsheet surgery.
  2. Analyst can surface inconsistent, blank, or unmapped theory labels for manual review instead of silently accepting them.
  3. Methodology labels follow the agreed hierarchy and outlier rules in generated artifacts and validation checks.
**Plans**: 3 plans

Plans:
- [x] 02-01: Implement legacy-to-canonical label mapping and validation utilities
- [x] 02-02: Assemble reviewed theory training/evaluation tables with split and leakage rules
- [x] 02-03: Define methodology schema, outlier handling, and review exports

### Phase 3: Baseline Theory Classifier
**Goal**: Build the first reproducible classifier for the canonical theory taxonomy and benchmark the agreed text-input variants.
**Depends on**: Phase 2
**Requirements**: [THEO-01, THEO-03, EVAL-01]
**Success Criteria** (what must be TRUE):
  1. Analyst can launch a baseline theory-classification run and recover config, artifact path, and model metadata for that run.
  2. Analyst can compare abstract-only versus abstract-plus-keywords inputs with explicit recorded results.
  3. Theory outputs include per-class metrics and a confusion matrix over the reviewed labeled split.
**Plans**: 2 plans

Plans:
- [ ] 03-01: Implement canonical theory training and evaluation flow with artifact persistence
- [ ] 03-02: Benchmark agreed input variants and persist comparable experiment outputs

### Phase 4: Methodology and Theme Pipeline
**Goal**: Add the secondary analytical outputs the client asked for while keeping them structurally separate from the theory label contract.
**Depends on**: Phase 3
**Requirements**: [EVAL-02, ANLY-01]
**Success Criteria** (what must be TRUE):
  1. Analyst can classify methodology according to the agreed hierarchy and evaluate it when reviewed labels exist.
  2. Theme outputs are generated as separate modules and do not overwrite theory or methodology columns.
  3. The repo has explicit output contracts for methodology and themes that remain traceable to a run context.
**Plans**: 2 plans

Plans:
- [ ] 04-01: Implement methodology classification and evaluation flow
- [ ] 04-02: Implement theme extraction module and its output contracts

### Phase 5: Full-Corpus Inference and Client Deliverables
**Goal**: Classify the chosen corpora at scale and produce the simplified deliverables, review queues, and correlations the client expects.
**Depends on**: Phase 4
**Requirements**: [THEO-02, EVAL-03, ANLY-02, ANLY-03, REPT-01, REPT-02]
**Success Criteria** (what must be TRUE):
  1. Analyst can run batch inference over the selected corpora and receive theory predictions with confidence, lineage, and run identifiers.
  2. Analyst can export low-confidence and taxonomy-conflict review tables for manual correction.
  3. Analyst can generate simplified client outputs plus correlation and reference/author summaries tied to the classified corpus.
**Plans**: 2 plans

Plans:
- [ ] 05-01: Implement full-corpus inference plus low-confidence and conflict review exports
- [ ] 05-02: Generate simplified deliverables, correlations, and reference/author summaries

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Canonical Taxonomy and Corpus Contracts | 3/3 | Complete | 2026-04-16 |
| 2. Label Harmonization and Reviewed Gold Set Assembly | 3/3 | Complete | 2026-04-16 |
| 3. Baseline Theory Classifier | 0/2 | Not started | - |
| 4. Methodology and Theme Pipeline | 0/2 | Not started | - |
| 5. Full-Corpus Inference and Client Deliverables | 0/2 | Not started | - |

---
*Roadmap updated: 2026-04-16 for milestone v1.0 Taxonomia Arbor y Clasificacion Cliente*
