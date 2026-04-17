# Plan 04-01 Summary

## Outcome

Plan `04-01` is complete. The repo now has a governed methodology-classification workflow that infers the agreed hierarchy from text evidence, persists reviewable methodology artifacts, and can emit a real methodology metrics bundle whenever reviewed labels are supplied.

## Implemented

- Added `configs/methodology_baseline.toml` as the Phase 4 methodology config surface.
- Added `src/abstract_classifier/methodology_pipeline.py` with:
  - config loading
  - input-artifact validation
  - keyword-aware methodology inference
  - contract-validated assignments for `NN`, `no_empirico`, and `empirico`
  - explicit review handling for insufficient or conflicting evidence
  - optional evaluation artifacts keyed by reviewed methodology labels
- Added `src/abstract_classifier/analysis.py` to orchestrate the analysis run bundle.
- Replaced the placeholder CLI handler in `src/abstract_classifier/commands/analyze.py`.

## Smoke Evidence

Methodology smoke output: `reports/tmp_phase4/analyze_smoke/methodology_summary.json`

- analyzed rows: `157`
- inferred labels:
  - `NN`: `57`
  - `no_empirico`: `41`
  - `empirico`: `52`
  - `unassigned`: `7`
- review queue size: `26`
- review reasons:
  - `insufficient_evidence`: `14`
  - `conflicting_cues`: `12`
- methodology evaluation status: `skipped` because no reviewed methodology artifact was supplied

## Verification

- `.\.venv\Scripts\python.exe -m pytest tests/test_methodology_pipeline.py -q`
- `.\.venv\Scripts\python.exe -m abstract_classifier.cli analyze --run-id smoke_phase4 --output-dir reports/tmp_phase4/analyze_smoke --input-artifact reports/phase2_gold_supervision.csv`

## Notes

- Phase 4 keeps methodology honest by separating inference from evaluation instead of pretending the repo already contains reviewed methodology gold labels.
- The optional evaluation path is tested with synthetic reviewed labels at the unit-test layer so the metrics contract is ready when real reviewed labels arrive.
