# Phase 3: Baseline Theory Classifier - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in `03-CONTEXT.md`; this log preserves the alternatives considered.

**Date:** 2026-04-16
**Phase:** 03-baseline-theory-classifier
**Mode:** Non-interactive defaults from canonical project docs and Phase 2 outputs
**Areas discussed:** baseline delivery shape, input-variant assembly, evaluation contract, and comparison scope

---

## Baseline Delivery Shape

| Option | Description | Selected |
|--------|-------------|----------|
| Zero-shot only | Treat the phase as a prompt-only benchmark and skip supervised training. | |
| Lightweight supervised baseline with reusable evaluation surface | Train one governed supervised baseline from the Phase 2 gold split, while keeping the evaluation surface reusable for future baselines. | x |
| Full model zoo | Implement zero-shot, sentence-transformers, SetFit, and fine-tuning in the same phase. | |

**Chosen outcome:** Lightweight supervised baseline with reusable evaluation surface.

**Notes:** The client docs recommend zero-shot as a benchmark, not the only delivery path. Phase 3 therefore centers on a supervised baseline that consumes the governed Phase 2 gold set and fixed split, while leaving room for optional reference runs later.

---

## Input Variant Assembly

| Option | Description | Selected |
|--------|-------------|----------|
| Use Phase 2 gold rows as-is | Train only on the `abstract` field because the current gold artifact does not expose keywords. | |
| Join governed gold rows back to normalized source metadata | Keep Phase 2 gold and split as the label truth, but derive `abstract_plus_keywords` text by reusing normalized source rows keyed by `record_id`. | x |
| Rebuild Phase 2 artifacts before Phase 3 | Expand the supervision pipeline first and only then plan the classifier. | |

**Chosen outcome:** Join governed gold rows back to normalized source metadata.

**Notes:** `reports/phase2_gold_supervision.csv` is the supervised truth, but `src/abstract_classifier/io/sources.py` already exposes `author_keywords` and `index_keywords`. That makes variant enrichment possible without reopening raw spreadsheets for manual work.

---

## Evaluation Contract

| Option | Description | Selected |
|--------|-------------|----------|
| Accuracy only | Persist one scalar score and keep the rest in notebooks. | |
| Full metrics bundle plus row-level predictions | Persist overall metrics, per-class metrics, confusion matrix, and prediction-level outputs tied to a run id. | x |
| Notebook-only diagnostics | Leave evaluation informal and exploratory until a later milestone. | |

**Chosen outcome:** Full metrics bundle plus row-level predictions.

**Notes:** `EVAL-01` requires accuracy, macro F1, weighted F1, confusion matrix, and per-class performance. The persisted outputs also need to support later manual error review.

---

## Benchmark Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Compare models and text variants together | Fold model-family comparison and text-variant comparison into one large benchmark matrix. | |
| Focus comparison on the agreed text variants over the fixed split | Keep Phase 3 comparison centered on `abstract_only` vs `abstract_plus_keywords`, with any zero-shot reference treated as optional if it reuses the same evaluation surface. | x |
| Defer comparison work entirely | Deliver one trained model only and postpone all benchmarking. | |

**Chosen outcome:** Focus comparison on the agreed text variants over the fixed split.

**Notes:** This matches the roadmap success criteria and keeps the implementation size aligned to Phase 3 rather than drifting into later experiment-tracking work.

---

## the agent's Discretion

- Exact sentence-transformer model name for the first supervised baseline.
- Exact linear classifier choice, as long as score semantics are documented and future review thresholds remain possible.
- Exact run-directory naming under `reports/`, as long as each run is deterministic and traceable.
- Optional zero-shot reference inclusion if it lands naturally on top of the same evaluation bundle.

## Deferred Ideas

- Methodology training and evaluation remain Phase 4 work.
- Full-corpus inference, confidence review exports, and client-ready delivery tables remain Phase 5 work.
- Persistent experiment dashboards or registries remain v2 work unless a minimal comparison manifest is needed for Phase 3.
