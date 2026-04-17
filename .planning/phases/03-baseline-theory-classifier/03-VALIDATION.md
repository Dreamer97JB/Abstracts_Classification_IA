---
phase: 03
slug: baseline-theory-classifier
status: passed
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-16
updated: 2026-04-16
---

# Phase 03 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest 8.x` |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `.\.venv\Scripts\python.exe -m pytest tests -q` |
| **Full suite command** | `.\.venv\Scripts\python.exe -m pytest tests -q` |
| **Estimated runtime** | ~60-120 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.\.venv\Scripts\python.exe -m pytest tests -q`
- **After every plan wave:** Run `.\.venv\Scripts\python.exe -m pytest tests -q`
- **Before `$gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 2 minutes

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 03-01 | 1 | THEO-01 | unit | `.\.venv\Scripts\python.exe -m pytest tests/test_theory_baseline_config.py tests/test_theory_dataset_loader.py -q` | yes | green |
| 03-01-02 | 03-01 | 1 | THEO-01 | smoke | `.\.venv\Scripts\python.exe -m abstract_classifier.cli train --config configs/theory_baseline.toml --run-id smoke_train --output-dir reports/tmp_phase3/train_smoke` | yes | green |
| 03-01-03 | 03-01 | 1 | EVAL-01 | unit | `.\.venv\Scripts\python.exe -m pytest tests/test_theory_train_artifacts.py tests/test_theory_evaluate_metrics_bundle.py -q` | yes | green |
| 03-02-01 | 03-02 | 2 | THEO-03 | unit | `.\.venv\Scripts\python.exe -m pytest tests/test_theory_text_variants.py -q` | yes | green |
| 03-02-02 | 03-02 | 2 | THEO-03, EVAL-01 | unit | `.\.venv\Scripts\python.exe -m pytest tests/test_theory_variant_benchmark.py -q` | yes | green |
| 03-02-03 | 03-02 | 2 | THEO-03, EVAL-01 | smoke | `.\.venv\Scripts\python.exe -m abstract_classifier.cli evaluate --config configs/theory_baseline.toml --compare-variants abstract_only abstract_plus_keywords --output-dir reports/tmp_phase3/variant_compare` | yes | green |

*Status: pending, green, red, flaky*

---

## Wave 0 Requirements

- [x] `tests/test_theory_baseline_config.py` - baseline config contract and required artifact paths
- [x] `tests/test_theory_dataset_loader.py` - Phase 2 gold/split loading, split reuse, and taxonomy-order checks
- [x] `tests/test_theory_train_artifacts.py` - training manifest, label map, and model-artifact persistence
- [x] `tests/test_theory_evaluate_metrics_bundle.py` - overall metrics, per-class metrics, confusion matrix, and prediction outputs
- [x] `tests/test_theory_text_variants.py` - governed `abstract_only` and `abstract_plus_keywords` assembly behavior
- [x] `tests/test_theory_variant_benchmark.py` - side-by-side comparison artifact shape and fixed-split reuse

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Keyword fallback is honest for `seed` rows | THEO-03 | Coverage interpretation depends on business context, not just code shape | Inspect the persisted coverage summary and confirm rows without keywords remain valid while keyword availability is reported by source/split |
| Confusion-matrix label order matches the canonical taxonomy | EVAL-01 | Human review is needed to confirm the output order is semantically correct | Compare evaluation outputs against `configs/taxonomy.toml` and `docs/alcance_cliente/decision_taxonomia_canonica.md` |
| Run manifest points to the governed Phase 2 inputs | THEO-01, EVAL-01 | Artifact lineage must remain operationally trustworthy | Open the run manifest and confirm it references `reports/phase2_gold_supervision.csv`, `reports/phase2_split_assignments.csv`, and the expected `split_version` |

---

## Validation Sign-Off

- [x] All tasks have `<acceptance_criteria>` with automated or manual verification hooks
- [x] Sampling continuity: no 3 consecutive tasks without automated verification
- [x] Wave 0 covers config, dataset loading, train artifacts, metrics bundle, text variants, and comparison outputs
- [x] No watch-mode flags
- [x] Feedback latency < 2 minutes
- [x] `nyquist_compliant: true` set in frontmatter once Wave 0 lands

**Approval:** passed
