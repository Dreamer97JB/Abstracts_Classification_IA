# Abstracts Classification IA

## What This Is

Brownfield project for classifying academic abstracts from the client's Google Scholar and Scopus corpora into theory categories grounded in the Arbor article typology. The working target is no longer a generic future taxonomy: it is a concrete classification workflow that predicts theory type, methodology, and supporting analytical outputs from auditable source data.

## Core Value

Deliver defensible automatic classifications over the client corpus using a canonical, article-grounded taxonomy with traceable data lineage and reviewable outputs.

## Requirements

### Validated

- [x] Source spreadsheet ingestion and initial cleaning work end-to-end in the existing notebook and produce `abstracs_cleaned.csv`.
- [x] The current notebook can generate philosophy-oriented labels for the legacy exploratory taxonomy and persist the result to CSV artifacts.
- [x] The current notebook can generate topic, methodology, and HTML analysis outputs for exploratory review.
- [x] A GPU-capable WSL ROCm environment is now available for local training experiments on the current machine.
- [x] The repo now contains real client corpora plus labeled subsets in `Database/` and `Seed/`.
- [x] The Arbor article in `Article/` defines the six-type theory typology that should anchor semantic label meaning.
- [x] Phase 01 established `src/abstract_classifier/` as the operational CLI and script surface for `audit`, `prepare`, `train`, `evaluate`, `predict`, and `analyze`.
- [x] Phase 01 established governed source manifests and strict overlap auditing for Google, Scopus, Seed, and `Muestras`.
- [x] Phase 01 established the canonical Arbor taxonomy contract plus a review-oriented legacy label inventory.
- [x] Phase 02 assembled governed theory gold tables, methodology review outputs, and the fixed `phase2_v1` split from `Seed` and `Muestras`.
- [x] Phase 03 replaced the placeholder theory `train` and `evaluate` commands with a reproducible baseline classifier workflow plus explicit text-variant benchmarking.
- [x] Phase 04 replaced the placeholder `analyze` command with a run-bundle workflow that emits separate methodology and theme outputs plus optional methodology evaluation artifacts.

### Active

- [ ] Extend the governed theory path from labeled-split evaluation to full-corpus batch inference, confidence review exports, and client-ready outputs.
- [ ] Add correlation, author, and reference summaries on top of the new Phase 4 outputs without blurring the theory-classification contract.

### Out of Scope

- Shipping a web app or API in this milestone - the immediate need is a trustworthy research and delivery pipeline.
- Inventing a new theory taxonomy beyond the Arbor article and the client-provided materials.
- Treating inconsistent spreadsheet codes as authoritative without canonical remapping and review.
- Using Google and Scopus as if they were interchangeable corpora without preserving lineage and overlap decisions.
- Optimizing broad exploratory analyses before the main theory and methodology outputs are measurable.

## Context

- The repo was notebook-first and artifact-driven; Phase 01 introduced `src/abstract_classifier/` so the scripted pipeline is now the operational source of truth while notebooks stay exploratory.
- Historical outputs already exist in CSV and HTML form and should remain as reference artifacts while the scripted pipeline emerges.
- The newly added client package changes the project shape: Google Scholar contributes 6,769 rows, Scopus contributes 8,484 rows, and Scopus carries richer metadata through keywords and references.
- `Seed.xlsx` and Scopus `Muestras` provide labeled examples, but they do not yet form a clean gold standard because label codes and type numbering are inconsistent.
- The Arbor article explicitly defines six theory types: realismo fuerte, realismo moderado / critico, antirrealismo epistemologico, pragmatismo epistemologico, constructivismo moderado, and constructivismo fuerte / relativismo.
- The machine now has a validated WSL2 + Ubuntu 24.04 + ROCm path with AMD Radeon RX 9070 support for PyTorch workloads.
- The client also wants methodology, themes, and correlation-style outputs, so the milestone must separate core classification from secondary analysis.
- Phase 03 now provides the first script-driven theory baseline with persisted manifests, metrics, predictions, and `abstract_only` versus `abstract_plus_keywords` comparison artifacts under `reports/tmp_phase3/`.
- Phase 04 now provides a script-driven analysis bundle with methodology assignments, review queues, optional methodology metrics, and separate theme outputs under `reports/tmp_phase4/`.
- Detailed evidence from the new files is captured in `.planning/research/CLIENT_SCOPE_2026-04-02.md`.

## Constraints

- **Brownfield**: Existing notebook outputs must remain understandable and traceable while the new pipeline is introduced.
- **Taxonomy semantics**: Canonical theory labels must stay grounded in the Arbor article, not drift with spreadsheet shorthand.
- **Label quality**: `Seed` and `Muestras` contain useful supervision but require harmonization before they can be treated as trusted training data.
- **Execution environment**: GPU training should target WSL ROCm on Ubuntu 24.04; Windows remains a secondary CPU/support environment.
- **Reproducibility**: Every important run must be restorable from scripts, config, and saved artifacts, not notebook cell history.
- **Client readability**: Final outputs must be simpler than current exploratory artifacts and understandable by a non-technical reviewer.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Use WSL ROCm as the primary training environment | GPU path is validated there, while Windows GPU execution was not reliable for this repo | Pending - applies in training phases |
| Use the Arbor article as the semantic source of truth for theory labels | The client provided a concrete six-type typology, so taxonomy meaning should not float across spreadsheets | Validated in Phase 01 via `configs/taxonomy.toml` and `src/abstract_classifier/taxonomy.py` |
| Treat Scopus as the main operational corpus and Google as secondary historical support | Scopus has stronger metadata coverage through keywords and references and contains the `Muestras` subset directly | Operationalized in Phase 01 manifests and overlap tie-break rules |
| Treat `Seed` and `Muestras` as supervision sources that require canonical remapping first | The label codes are inconsistent and cannot be trusted raw as gold labels | Validated in Phase 01 taxonomy inventory and review-required mapping statuses |
| Model methodology separately with a hierarchy and explicit outlier handling | The client notes define methodology as a separate decision chain, not a side effect of theory labeling | Validated in Phase 04 via `configs/methodology_baseline.toml`, `src/abstract_classifier/methodology_pipeline.py`, and `analyze` |
| Keep themes and correlation outputs secondary to the theory classifier contract | The client wants them, but they should consume a stable classified corpus rather than define the main label logic | Partially validated in Phase 04 for themes; correlations remain Phase 05 |

## Current Milestone: v1.0 Taxonomia Arbor y Clasificacion Cliente

**Goal:** Turn the new client corpora, labeled subsets, and Arbor typology into a canonical classification pipeline that predicts theory type, methodology, and client-facing analytical outputs.

**Target features:**
- canonical theory taxonomy and legacy-label mapping grounded in the Arbor article
- governed corpus assembly across Google, Scopus, Seed, and `Muestras`
- baseline automatic theory classification plus methodology hierarchy outputs
- theme and correlation analyses over the classified corpus with simplified deliverables

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition**:
1. Requirements invalidated? -> Move to Out of Scope with reason
2. Requirements validated? -> Move to Validated with phase reference
3. New requirements emerged? -> Add to Active
4. Decisions to log? -> Add to Key Decisions
5. "What This Is" still accurate? -> Update if drifted

**After each milestone**:
1. Full review of all sections
2. Core Value check - still the right priority?
3. Audit Out of Scope - reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-17 after completing Phase 4 and advancing toward Phase 5*
