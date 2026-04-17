# Plan 03-02 Summary

## Outcome

Plan `03-02` is complete. The repo now supports the governed text variants `abstract_only` and `abstract_plus_keywords`, reports keyword coverage honestly by source and split, and can benchmark both variants from the CLI on the frozen Phase 2 split without notebook work.

## Implemented

- Added `src/abstract_classifier/text_variants.py` with:
  - governed keyword metadata loading from the supervision workbooks
  - exact variant names `abstract_only` and `abstract_plus_keywords`
  - fallback behavior for rows without keywords
  - keyword availability and enrichment summaries by source and split
- Extended `src/abstract_classifier/evaluation.py` so `evaluate --compare-variants ...`:
  - trains each requested variant on the same governed train split
  - evaluates on the same governed target split
  - writes one stable comparison row per variant to `variant_comparison.csv`
- Added coverage and comparison regression tests:
  - `tests/test_theory_text_variants.py`
  - `tests/test_theory_variant_benchmark.py`

## Benchmark Evidence

Comparison artifact: `reports/tmp_phase3/variant_compare/variant_comparison.csv`

| Variant | Accuracy | Macro F1 | Weighted F1 | Keyword Coverage Rate |
|---------|----------|----------|-------------|-----------------------|
| `abstract_only` | `0.375` | `0.1731` | `0.3216` | `0.0` |
| `abstract_plus_keywords` | `0.375` | `0.1731` | `0.3216` | `0.5` |

## Coverage Notes

- `seed` rows expose no keyword columns, so they remain abstract-only even in the enriched variant.
- `muestras` contributes the observed keyword enrichment.
- Across the full governed dataset, keyword availability is `68 / 157` rows (`43.31%`).
- On the fixed test split, keyword availability is `12 / 24` rows (`50%`), all from `muestras`.

## Verification

- `.\.venv\Scripts\python.exe -m pytest tests/test_theory_text_variants.py tests/test_theory_variant_benchmark.py -q`
- `.\.venv\Scripts\python.exe -m abstract_classifier.cli evaluate --config configs/theory_baseline.toml --compare-variants abstract_only abstract_plus_keywords --output-dir reports/tmp_phase3/variant_compare`
