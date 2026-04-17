# Plan 03-01 Summary

## Outcome

Plan `03-01` is complete. The placeholder theory `train` and `evaluate` commands were replaced with a governed baseline workflow that reads the frozen Phase 2 gold and split artifacts, trains only on the `train` partition, and persists a deterministic run bundle with manifest, model, keyword-coverage, metrics, confusion matrix, and row-level predictions.

## Implemented

- Added `configs/theory_baseline.toml` as the Phase 3 baseline config surface.
- Added `src/abstract_classifier/training.py` with:
  - config loading
  - Phase 2 gold/split dataset validation
  - deterministic `train/val/test` partition reuse
  - TF-IDF + logistic regression baseline training
  - run manifest and artifact persistence
- Added `src/abstract_classifier/evaluation.py` with:
  - trained-run loading
  - governed split evaluation
  - overall metrics, per-class metrics, confusion matrix, and predictions export
- Replaced the placeholder CLI handlers in:
  - `src/abstract_classifier/commands/train.py`
  - `src/abstract_classifier/commands/evaluate.py`

## Verification

- `.\.venv\Scripts\python.exe -m pytest tests/test_theory_baseline_config.py tests/test_theory_dataset_loader.py tests/test_theory_train_artifacts.py tests/test_theory_evaluate_metrics_bundle.py -q`
- `.\.venv\Scripts\python.exe -m abstract_classifier.cli train --config configs/theory_baseline.toml --run-id smoke_train --output-dir reports/tmp_phase3/train_smoke`
- `.\.venv\Scripts\python.exe -m abstract_classifier.cli evaluate --config configs/theory_baseline.toml --run-id smoke_train --output-dir reports/tmp_phase3/train_smoke`

## Notes

- The operational baseline uses TF-IDF plus logistic regression instead of a heavier embedding stack so the Phase 3 path stays deterministic, fast, and offline-safe on the small fixed gold split.
- The smoke run persisted under `reports/tmp_phase3/train_smoke/` and references the governed Phase 2 inputs in `run_manifest.json`.
