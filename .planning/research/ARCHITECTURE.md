# Architecture Research

**Domain:** academic abstract classification pipeline refactor
**Researched:** 2026-03-24
**Confidence:** HIGH

## Recommended Architecture Direction

The current architecture is notebook-centric and artifact-driven. For this milestone, the best target architecture is a small Python package with script entrypoints and explicit data contracts, while notebooks become exploratory clients of the scripted pipeline rather than the orchestration layer.

## Target Components

### Core Components

| Component | Responsibility | New or Modified | Notes |
|-----------|----------------|-----------------|-------|
| `src/abstract_classifier/config.py` | Load run, taxonomy, and path settings | New | Centralizes what is currently embedded in notebook cells |
| `src/abstract_classifier/data_prep.py` | Normalize source spreadsheet and write managed datasets | New | Replaces manual notebook cleaning |
| `src/abstract_classifier/labels.py` | Validate label schema, text completeness, and class diagnostics | New | Pre-training gate for real client labels |
| `src/abstract_classifier/train.py` | Baseline and supervised-ready training entrypoints | New | Saves artifact metadata with each run |
| `src/abstract_classifier/evaluation.py` | Metrics, confusion matrix, and review exports | New | Makes model quality auditable |
| `src/abstract_classifier/predict.py` | Batch inference on new abstracts | New | Writes explicit prediction contracts |
| `src/abstract_classifier/analysis.py` | Optional topic/methodology analysis | New | Kept outside the main classifier contract |

### Data Flow

```text
raw inputs
  -> audit
  -> prepare
  -> validated processed dataset
  -> train
  -> evaluate
  -> predict

optional:
processed dataset or predictions
  -> analysis modules
```

## Integration Points

| Integration Point | Why It Matters | Recommendation |
|-------------------|----------------|----------------|
| Existing CSV artifacts in repo root | They represent historical outputs and reference points | Preserve them as historical artifacts; do not treat them as the long-term contract |
| WSL ROCm environment | Training path depends on it for GPU work | Keep environment bootstrap script in `scripts/` and keep GPU-specific assumptions out of business logic |
| Jupyter notebooks | User still benefits from exploratory notebooks | Keep notebooks, but make them read scripted outputs rather than generate canonical outputs |

## Build Order

1. Create package structure and script entrypoints
2. Create data preparation and label validation contracts
3. Add training entrypoints and artifact metadata
4. Add evaluation and prediction output contracts
5. Extract optional analysis modules and slim notebook responsibilities

## What Changes vs Current State

- Data lineage moves from implicit CSV naming to explicit run-oriented contracts
- Environment management moves from notebook cells to bootstrap scripts and versioned requirements
- Main output semantics move from ambiguous shared columns to task-specific fields
- Optional analysis stops blocking or polluting the main classifier path

## Architectural Warnings

- Do not let the optional analysis module become a hidden dependency of the main classifier pipeline
- Do not bind taxonomy definitions to code constants in training modules
- Do not keep writing final operational artifacts only to the repo root without manifest or run metadata

## Sources

- `.planning/codebase/ARCHITECTURE.md`
- `.planning/codebase/CONCERNS.md`
- `docs/guia_refactor_clasificador.md`

---
*Architecture research for: academic abstract classification pipeline refactor*
*Researched: 2026-03-24*
