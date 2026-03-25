# Abstracts Classification IA

## What This Is

Brownfield project for classifying academic abstracts from a source spreadsheet into philosophy-oriented categories and related analytical outputs. The current implementation proved the concept in notebooks, and this milestone turns that work into a reproducible pipeline that can absorb new client-provided labels without depending on one monolithic notebook.

## Core Value

Produce a reliable and repeatable abstract classification workflow that can be retrained for new taxonomies with auditable data, metrics, and outputs.

## Requirements

### Validated

- [x] Source spreadsheet ingestion and initial cleaning work end-to-end in the existing notebook and produce `abstracs_cleaned.csv`.
- [x] The current notebook can generate philosophy labels for the existing four-class taxonomy and persist the result to CSV artifacts.
- [x] The current notebook can generate topic, methodology, and HTML analysis outputs for exploratory review.
- [x] A GPU-capable WSL ROCm environment is now available for local training experiments on the current machine.

### Active

- [ ] Replace notebook-only execution with named scripts and modules for audit, prepare, train, evaluate, and predict.
- [ ] Introduce label schema validation and a training path designed for real client-provided examples.
- [ ] Make model runs reproducible with explicit metrics, artifact metadata, and batch inference outputs.
- [ ] Separate optional topic and methodology analysis from the main classifier pipeline.

### Out of Scope

- Shipping a web app or API in this milestone - the immediate need is a trustworthy research and delivery pipeline.
- Treating synthetic seeds as gold labels - they remain auxiliary bootstrapping material only.
- Finalizing the future client taxonomy before the client delivers official labels and examples.
- Optimizing topic modeling before the main classifier pipeline is reproducible and measurable.

## Context

- The repo is notebook-first and artifact-driven today; `AbstractsV2.ipynb` is the operational center of gravity.
- Historical outputs already exist in CSV and HTML form, and they should be preserved as reference artifacts rather than discarded.
- Current data concerns include duplicate synthetic seeds, inconsistent text encoding, weak topic stability, and ambiguous reuse of the `Confidence` column across tasks.
- The machine now has a validated WSL2 + Ubuntu 24.04 + ROCm path with AMD Radeon RX 9070 support for PyTorch workloads.
- The next business need is to support new categories using real labeled examples from the client, not to continue scaling the current notebook heuristics blindly.

## Constraints

- **Brownfield**: Existing notebook outputs must remain understandable and traceable while the new pipeline is introduced.
- **Label quality**: Real client labels are expected later, so the design must support relabeling and retraining without structural rewrites.
- **Execution environment**: GPU training should target WSL ROCm on Ubuntu 24.04; Windows remains a secondary CPU/support environment.
- **Reproducibility**: Every important run must be restorable from scripts, config, and saved artifacts, not notebook cell history.
- **User workflow**: The repo should remain usable by a non-expert operator with explicit scripts and clear docs.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Use WSL ROCm as the primary training environment | GPU path is validated there, while Windows GPU execution was not reliable for this repo | - Pending |
| Keep notebooks as exploratory surfaces, not the source of truth | The POC was successful in notebooks, but future delivery needs reproducible scripts | - Pending |
| Treat synthetic seeds as auxiliary only | Current synthetic seed diversity is too weak to justify using them as primary supervision | - Pending |
| Plan the classifier first, optional analyses second | Topic/methodology outputs are useful, but they should not block the main taxonomy pipeline | - Pending |

## Current Milestone: v1.0 Pipeline Reproducible y Refactor Base

**Goal:** Convert the notebook POC into a reproducible ML pipeline prepared for real client labels and GPU-backed retraining.

**Target features:**
- project skeleton with named scripts and reusable modules
- data and label contracts with validation before training
- reproducible baseline training, evaluation, and inference flows
- optional topic and methodology modules separated from the main classifier path

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
*Last updated: 2026-03-24 after starting milestone v1.0 Pipeline Reproducible y Refactor Base*
