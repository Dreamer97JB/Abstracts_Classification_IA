# Project Research Summary

**Project:** Abstracts Classification IA
**Domain:** academic abstract classification and taxonomy migration pipeline
**Researched:** 2026-03-24
**Confidence:** HIGH

## Executive Summary

This project already proved value as a notebook-based POC, but the current architecture is too coupled to hidden notebook state, ad hoc CSV chaining, and synthetic seed assumptions. The right next step is not "train a bigger model" in isolation; it is to establish a reproducible pipeline where data preparation, label validation, training, evaluation, and inference are explicit and scriptable.

The recommended approach is a small Python package with named script entrypoints and config-driven taxonomy files. WSL ROCm should be the default training environment because it is already validated on this machine with the AMD Radeon RX 9070. Optional analyses like topic modeling and methodology should remain in the project, but only as isolated modules that consume stable classifier outputs rather than define them.

The main risk is scope drift: it is easy to keep polishing exploratory outputs while the primary classifier remains weakly governed. The roadmap therefore starts with contracts and data governance, then moves into training, then evaluation/inference, and only then extracts optional analysis modules.

## Key Findings

### Recommended Stack

The validated stack for this milestone is Python on WSL Ubuntu 24.04 with PyTorch ROCm 7.2 for training, plus pandas/scikit-learn/transformers/sentence-transformers/SetFit for the core ML path. This gives the project a supported GPU path and keeps the repo aligned with the local machine that will do the work.

**Core technologies:**
- Python 3.12 in WSL: primary runtime for training and pipeline scripts - matches the validated ROCm path
- PyTorch 2.9.1 ROCm 7.2: training runtime - already working with the local AMD GPU
- Pandas and scikit-learn: data and metrics backbone - required for repeatable prep and evaluation
- transformers / sentence-transformers / SetFit: baseline and supervised model tooling - suited to the current and future classifier paths

### Expected Features

The milestone must deliver data preparation, label validation, repeatable training, evaluation, and batch inference as table stakes. The differentiators are config-driven taxonomy changes, low-confidence review outputs, and keeping optional analysis modules available without polluting the main classifier contract.

**Must have (table stakes):**
- Reproducible data preparation - users expect the same source input to produce the same normalized dataset
- Label validation - users need to trust real client labels before training
- Repeatable training and evaluation - users need defensible metrics and saved artifacts
- Batch inference with traceability - users need deliverable outputs tied to a model run

**Should have (competitive):**
- Config-driven taxonomy changes - reduces the cost of client taxonomy changes
- Low-confidence review exports - focuses manual review work
- Optional analysis modules - preserves exploratory value without harming the main pipeline

**Defer (v2+):**
- Human relabeling workflow
- Hierarchical or multi-label taxonomy support
- Persistent experiment registry/dashboard

### Architecture Approach

The target architecture is a script-first package with explicit modules for config, data prep, labels, training, evaluation, prediction, and optional analysis. The notebook stays in the repo but becomes an exploratory layer that reads outputs from the scripted pipeline rather than producing canonical milestone artifacts.

**Major components:**
1. Data and label contracts - normalize raw inputs and validate incoming labeled examples
2. Training and evaluation pipeline - produce saved model artifacts and metrics bundles
3. Inference and optional analysis outputs - generate stable classifier results plus isolated topic/methodology modules

### Critical Pitfalls

1. **Refactoring structure without fixing data contracts** - avoid by making schema validation a first-class phase
2. **Training on synthetic seeds as if they were gold data** - avoid by treating them as auxiliary only
3. **Mixing classifier and optional analysis outputs** - avoid by separating task-specific output contracts
4. **Losing environment reproducibility after setup works once** - avoid by keeping bootstrap and verification scripts in the repo
5. **Optimizing optional analyses before classifier measurement** - avoid by sequencing them last in the roadmap

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Project Skeleton and Run Contracts
**Rationale:** Establishes the foundation so later work does not fall back into notebook-only execution.
**Delivers:** Package skeleton, script entrypoints, environment run contracts.
**Addresses:** OPS-01, ENV-01
**Avoids:** Environment drift and structural refactor without operational contracts.

### Phase 2: Data and Label Governance
**Rationale:** Data and labels must become trustworthy before training can be meaningful.
**Delivers:** Normalized dataset flow and label validation.
**Addresses:** DATA-01, DATA-02, LABL-01, LABL-02
**Avoids:** Hidden data quality and schema problems.

### Phase 3: Baseline and Supervised Training Paths
**Rationale:** Once contracts exist, training can become reproducible instead of ad hoc.
**Delivers:** Baseline and supervised-ready train flows with artifacts.
**Uses:** PyTorch ROCm, transformers, sentence-transformers, SetFit
**Implements:** Training modules and artifact metadata.

### Phase 4: Evaluation and Batch Inference
**Rationale:** Quality must be measurable before outputs are trusted or delivered.
**Delivers:** Metrics bundle, batch inference outputs, low-confidence review exports.
**Uses:** scikit-learn metrics and scripted inference outputs.

### Phase 5: Optional Analysis Modules and Notebook Slimming
**Rationale:** Optional analyses should attach to a stable classifier pipeline, not define it.
**Delivers:** Separated topic/methodology modules, notebook slimming, consolidated report outputs.
**Avoids:** Shared-column ambiguity and scope drift.

### Phase Ordering Rationale

- Data and label governance precede training because labels are the critical future dependency.
- Evaluation and inference follow training because outputs only make sense when tied to saved artifacts.
- Optional analyses are last because they should consume a stable classifier contract, not compete with it.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3:** Final supervised training shape may change once the client taxonomy and label volume are known.
- **Phase 5:** Topic/methodology extraction details may need local experimentation after the main contract is stable.

Phases with standard patterns:
- **Phase 1:** Standard project-structure and command-contract work
- **Phase 2:** Standard data validation and dataset versioning patterns
- **Phase 4:** Standard metrics and batch inference patterns

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Versions are validated locally in the active WSL environment |
| Features | HIGH | Requirements follow directly from the repo state and user goals |
| Architecture | HIGH | The needed target shape is clear from the codebase map and concerns audit |
| Pitfalls | HIGH | Current repo fragility already exposes the main risks |

**Overall confidence:** HIGH

### Gaps to Address

- Real client labels and final taxonomy are not yet present, so supervised training must stay adaptable.
- Historical CSV artifacts still need a formal lineage strategy when the scripted pipeline starts writing new outputs.

## Sources

### Primary (HIGH confidence)
- Local validated environment and repo state - direct evidence from the current machine and repository
- `.planning/codebase/ARCHITECTURE.md` - current architecture
- `.planning/codebase/CONCERNS.md` - current risks and scaling limits
- `docs/guia_refactor_clasificador.md` - repo-specific refactor guidance

### Secondary (MEDIUM confidence)
- `docs/guia_amd_wsl_rocm.md` - environment guidance captured during setup
- `reports/data_audit.md` - data quality baseline

---
*Research completed: 2026-03-24*
*Ready for roadmap: yes*
