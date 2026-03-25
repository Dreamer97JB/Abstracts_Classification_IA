# Requirements: Abstracts Classification IA

**Defined:** 2026-03-24
**Core Value:** Produce a reliable and repeatable abstract classification workflow that can be retrained for new taxonomies with auditable data, metrics, and outputs.

## v1 Requirements

### Operations

- [ ] **OPS-01**: Analyst can run named project entrypoints for audit, prepare, train, evaluate, and predict without editing notebook cells.
- [ ] **OPS-02**: Analyst can keep notebooks as exploratory views while the script/module pipeline remains the source of truth.

### Environment

- [ ] **ENV-01**: Analyst can bootstrap the supported WSL ROCm environment from repo scripts and verify GPU readiness with one documented command path.

### Data

- [ ] **DATA-01**: Analyst can run a reproducible audit on source, seed, and generated artifacts and receive a Markdown report with data quality findings.
- [ ] **DATA-02**: Analyst can prepare a normalized dataset from the source spreadsheet into versioned processed files without manual notebook edits.

### Labels

- [ ] **LABL-01**: Analyst can declare taxonomy, text fields, and split settings in config files without changing training code.
- [ ] **LABL-02**: Analyst can validate labeled examples for schema, missing text, duplicates, class balance, and obvious leakage before training.

### Training

- [ ] **TRN-01**: Analyst can run a reproducible baseline training flow for zero-shot and/or SetFit with saved config and artifact metadata.
- [ ] **TRN-02**: Analyst can run a supervised training flow that is ready to consume real client-provided labels when enough labeled data exists.

### Inference

- [ ] **INFR-01**: Analyst can run batch inference on new abstracts and receive explicit output columns for predicted label, score, model version, and run identifier.

### Evaluation

- [ ] **EVAL-01**: Analyst can generate a metrics bundle with accuracy, macro F1, weighted F1, confusion matrix, and per-class performance for a labeled split.
- [ ] **EVAL-02**: Analyst can generate a low-confidence review output using configurable score thresholds.

### Analysis

- [ ] **ANLY-01**: Analyst can run topic and methodology analysis as optional modules that do not overwrite or blur the main classifier outputs.

### Reporting

- [ ] **REPT-01**: Analyst can generate a milestone-ready report summarizing audit, train, evaluate, and inference outputs from a single run context.

## v2 Requirements

### Human Review

- **HREV-01**: Analyst can review and relabel low-confidence predictions in a structured feedback loop for future retraining.

### Taxonomy Expansion

- **TAXO-01**: Analyst can support hierarchical or multi-label classification when the client taxonomy requires it.

### Experiment Tracking

- **EXPT-01**: Analyst can compare experiments in a persistent registry or dashboard across multiple milestone iterations.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Web app or API delivery | This milestone is about pipeline reliability, not serving infrastructure |
| Automatic final taxonomy creation without client input | The client has not yet delivered the official categories and examples |
| Training exclusively on synthetic seeds | Synthetic seeds are too repetitive to serve as trusted supervision |
| Real-time inference service | Batch and report-based workflows are sufficient for the immediate delivery need |
| Topic-model optimization before classifier stabilization | The main classifier must become reproducible and measurable first |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| OPS-01 | Phase 1 | Pending |
| ENV-01 | Phase 1 | Pending |
| DATA-01 | Phase 2 | Pending |
| DATA-02 | Phase 2 | Pending |
| LABL-01 | Phase 2 | Pending |
| LABL-02 | Phase 2 | Pending |
| TRN-01 | Phase 3 | Pending |
| TRN-02 | Phase 3 | Pending |
| INFR-01 | Phase 4 | Pending |
| EVAL-01 | Phase 4 | Pending |
| EVAL-02 | Phase 4 | Pending |
| OPS-02 | Phase 5 | Pending |
| ANLY-01 | Phase 5 | Pending |
| REPT-01 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 14 total
- Mapped to phases: 14
- Unmapped: 0

---
*Requirements defined: 2026-03-24*
*Last updated: 2026-03-24 after initial milestone definition*
