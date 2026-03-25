# Roadmap: Abstracts Classification IA

## Overview

This milestone turns an end-to-end notebook proof of concept into a reproducible classifier pipeline. The work starts by establishing stable run contracts and project structure, then formalizes data and label handling, then adds repeatable training, evaluation, inference, and optional analysis modules in a sequence that reduces ambiguity and keeps the main classifier path primary.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [ ] **Phase 1: Project Skeleton and Run Contracts** - Establish reusable package structure, scripts, and environment entrypoints.
- [ ] **Phase 2: Data and Label Governance** - Normalize source data and validate label inputs before any training flow runs.
- [ ] **Phase 3: Baseline and Supervised Training Paths** - Implement reproducible baseline and supervised-ready training entrypoints with artifact metadata.
- [ ] **Phase 4: Evaluation and Batch Inference** - Generate metrics bundles and batch predictions with explicit run traceability.
- [ ] **Phase 5: Optional Analysis Modules and Notebook Slimming** - Separate topic/methodology analysis from the main classifier pipeline and keep notebooks exploratory only.

## Phase Details

### Phase 1: Project Skeleton and Run Contracts
**Goal**: Establish the project structure, command surface, and environment entrypoints that replace notebook-only execution as the operational source of truth.
**Depends on**: Nothing (first phase)
**Requirements**: [OPS-01, ENV-01]
**Success Criteria** (what must be TRUE):
  1. Analyst can identify and run named project entrypoints for audit, prepare, train, evaluate, and predict.
  2. The supported WSL ROCm bootstrap and verification path is documented and runnable from the repo.
  3. The repo contains a package-oriented structure that future phases can extend without reintroducing notebook coupling.
**Plans**: 2 plans

Plans:
- [ ] 01-01: Create package skeleton, config surface, and script entrypoints
- [ ] 01-02: Align environment docs and command conventions with the new run contracts

### Phase 2: Data and Label Governance
**Goal**: Make raw, interim, and processed data preparation repeatable while enforcing label and schema validation before training.
**Depends on**: Phase 1
**Requirements**: [DATA-01, DATA-02, LABL-01, LABL-02]
**Success Criteria** (what must be TRUE):
  1. Analyst can transform the source spreadsheet into normalized processed artifacts via scripts, not notebook cells.
  2. Analyst can run validation against incoming labeled examples and receive actionable failures for duplicates, missing text, and schema issues.
  3. Taxonomy and split settings live in files that can be changed without editing training code.
**Plans**: 3 plans

Plans:
- [ ] 02-01: Implement dataset ingestion and normalization flow
- [ ] 02-02: Implement label schema and validation utilities
- [ ] 02-03: Persist processed datasets and manifests for downstream phases

### Phase 3: Baseline and Supervised Training Paths
**Goal**: Introduce reproducible training entrypoints for baseline and supervised classifier paths with saved config and artifact metadata.
**Depends on**: Phase 2
**Requirements**: [TRN-01, TRN-02]
**Success Criteria** (what must be TRUE):
  1. Analyst can launch a baseline training run and recover the config, artifact path, and model metadata for that run.
  2. Analyst can launch a supervised-ready training path that accepts real client labels when available.
  3. Training outputs are stored with enough metadata to compare runs later without notebook forensics.
**Plans**: 2 plans

Plans:
- [ ] 03-01: Implement baseline training flow and artifact persistence
- [ ] 03-02: Implement supervised-ready training flow for real labeled data

### Phase 4: Evaluation and Batch Inference
**Goal**: Make model quality and prediction outputs measurable through repeatable metrics and explicit batch inference artifacts.
**Depends on**: Phase 3
**Requirements**: [INFR-01, EVAL-01, EVAL-02]
**Success Criteria** (what must be TRUE):
  1. Analyst can evaluate a trained run and obtain accuracy, macro F1, weighted F1, confusion matrix, and per-class metrics.
  2. Analyst can run batch inference and receive output columns for label, score, model version, and run identifier.
  3. Analyst can generate a low-confidence review output using a configurable threshold.
**Plans**: 2 plans

Plans:
- [ ] 04-01: Implement metrics and evaluation reporting flow
- [ ] 04-02: Implement batch inference and low-confidence review exports

### Phase 5: Optional Analysis Modules and Notebook Slimming
**Goal**: Separate optional analysis modules from the main classifier path and keep notebooks as exploratory clients of the scripted pipeline.
**Depends on**: Phase 4
**Requirements**: [OPS-02, ANLY-01, REPT-01]
**Success Criteria** (what must be TRUE):
  1. Topic and methodology analysis run as separate modules without overwriting main classifier columns or scores.
  2. The notebook can consume scripted outputs for exploration while the scripts remain the source of truth.
  3. Analyst can produce a milestone-ready report that summarizes audit, training, evaluation, and inference context.
**Plans**: 2 plans

Plans:
- [ ] 05-01: Extract optional analysis modules and clean output contracts
- [ ] 05-02: Slim notebook usage and generate consolidated milestone report

## Progress

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Project Skeleton and Run Contracts | 0/2 | Not started | - |
| 2. Data and Label Governance | 0/3 | Not started | - |
| 3. Baseline and Supervised Training Paths | 0/2 | Not started | - |
| 4. Evaluation and Batch Inference | 0/2 | Not started | - |
| 5. Optional Analysis Modules and Notebook Slimming | 0/2 | Not started | - |

---
*Roadmap created: 2026-03-24 for milestone v1.0 Pipeline Reproducible y Refactor Base*
