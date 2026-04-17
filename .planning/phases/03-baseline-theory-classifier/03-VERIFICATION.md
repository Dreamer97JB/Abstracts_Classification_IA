---
phase: 03
slug: baseline-theory-classifier
status: passed
verified_on: 2026-04-16
requirements_verified:
  - THEO-01
  - THEO-03
  - EVAL-01
---

# Phase 03 Verification

## Verdict

Phase 3 passed. The repo now has an operational, reproducible baseline theory-classification path with persisted run artifacts, explicit text-variant benchmarking, and a reviewable evaluation bundle aligned to the canonical taxonomy contract.

## Automated Evidence

- `.\.venv\Scripts\python.exe -m pytest tests -q` -> `49 passed`
- `.\.venv\Scripts\python.exe -m abstract_classifier.cli train --config configs/theory_baseline.toml --run-id smoke_train --output-dir reports/tmp_phase3/train_smoke` -> passed
- `.\.venv\Scripts\python.exe -m abstract_classifier.cli evaluate --config configs/theory_baseline.toml --run-id smoke_train --output-dir reports/tmp_phase3/train_smoke` -> passed
- `.\.venv\Scripts\python.exe -m abstract_classifier.cli evaluate --config configs/theory_baseline.toml --compare-variants abstract_only abstract_plus_keywords --output-dir reports/tmp_phase3/variant_compare` -> passed

## Requirement Coverage

### THEO-01

Verified by:

- `src/abstract_classifier/training.py`
- `src/abstract_classifier/commands/train.py`
- `src/abstract_classifier/evaluation.py`
- `src/abstract_classifier/commands/evaluate.py`
- `tests/test_theory_train_artifacts.py`
- `tests/test_theory_evaluate_metrics_bundle.py`

Observed behavior:

- `train` consumes `reports/phase2_gold_supervision.csv` and `reports/phase2_split_assignments.csv`
- training fits only on the governed `train` split
- each run persists `run_manifest.json`, `model.joblib`, and supporting artifact paths

### THEO-03

Verified by:

- `src/abstract_classifier/text_variants.py`
- `src/abstract_classifier/evaluation.py`
- `tests/test_theory_text_variants.py`
- `tests/test_theory_variant_benchmark.py`

Observed behavior:

- the exact variants `abstract_only` and `abstract_plus_keywords` are available from config and CLI
- missing-keyword rows remain valid
- keyword coverage is reported by source and split

### EVAL-01

Verified by:

- `src/abstract_classifier/evaluation.py`
- `tests/test_theory_evaluate_metrics_bundle.py`
- `reports/tmp_phase3/train_smoke/metrics_overall.json`
- `reports/tmp_phase3/train_smoke/confusion_matrix.csv`

Observed behavior:

- evaluation writes accuracy, macro F1, weighted F1, per-class metrics, confusion matrix, and row-level predictions
- confusion-matrix order matches the canonical taxonomy ids from `configs/taxonomy.toml`

## Manual Checks Performed

- Inspected `reports/tmp_phase3/train_smoke/run_manifest.json` and confirmed it references the governed Phase 2 gold and split artifacts.
- Inspected `reports/tmp_phase3/train_smoke/metrics_overall.json` and confirmed canonical label order plus score semantics.
- Inspected `reports/tmp_phase3/variant_compare/variant_comparison.csv` and confirmed both agreed variants are benchmarked on the same `phase2_v1` split.
- Inspected keyword coverage and confirmed `seed` remains fallback-only while `muestras` provides the observed enrichment.

## Residual Risks

- The governed theory gold set is still small and imbalanced, so metric stability is limited.
- The first comparison showed no improvement from keyword enrichment on the fixed test split, so later phases should treat richer feature work as an experiment rather than an assumption.
