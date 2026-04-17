# Phase 3: Baseline Theory Classifier - Research

**Researched:** 2026-04-16
**Domain:** Small-data theory classification, governed text-variant assembly, reproducible train/evaluate artifacts, and fixed-split benchmarking
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Phase 3 must consume `reports/phase2_gold_supervision.csv` and `reports/phase2_split_assignments.csv` as the supervised truth and fixed split.
- `seed_labeled.csv` and `seed_generated.csv` remain non-canonical inputs.
- Phase 3 must deliver one operational supervised baseline; zero-shot may be logged only as an optional reference.
- Text variants must be explicit, config-selected options named `abstract_only` and `abstract_plus_keywords`.
- Keyword enrichment must remain governed and keyed by `record_id`; no manual spreadsheet edits are allowed.
- Missing-keyword rows must remain valid and must surface keyword-coverage statistics in outputs.
- Each run must persist a deterministic manifest plus reviewable evaluation artifacts.
- The evaluation bundle must include accuracy, macro F1, weighted F1, per-class metrics, confusion matrix, and row-level predictions.
- Label ordering must stay aligned to `configs/taxonomy.toml`.
- `train` and `evaluate` must stop being placeholders in this phase.

### the agent's Discretion
- Exact sentence-transformer model name.
- Exact linear classifier choice, as long as score semantics are documented.
- Exact file names inside the run directory.
- Optional zero-shot reference inclusion if it lands naturally on the same evaluation surface.

### Deferred Ideas (OUT OF SCOPE)
- Methodology modeling and methodology metrics.
- Full-corpus inference and client-delivery tables.
- Heavy experiment infrastructure such as persistent dashboards or registries.
</user_constraints>

<research_summary>
## Summary

Phase 3 should start with a governed, lightweight supervised baseline rather than an immediate jump to heavier fine-tuning. The current gold set is only `157` rows, split `109/24/24`, and the class balance is materially uneven. That makes a sentence-transformer embedding pipeline plus a class-aware linear classifier the safest first operational baseline: it is explainable, fast to rerun, and fits the repo's current dependency surface better than a bigger training stack.

The most important planning twist is that the current gold artifact does not itself contain keyword columns. The repo already has the missing ingredient, though: normalized source rows expose `author_keywords` and `index_keywords`, keyed by the same `record_id` lineage that the gold rows preserve. That means Phase 3 can benchmark `abstract_only` versus `abstract_plus_keywords` honestly without reopening or mutating raw spreadsheets.

**Primary recommendation:** implement one reusable train/evaluate surface around the Phase 2 gold split, use governed text-variant assembly keyed by `record_id`, persist every run under a deterministic directory, and keep comparison scope focused on the two agreed text variants.
</research_summary>

<current_data_profile>
## Current Gold-Set Profile

| Property | Value | Why It Matters |
|----------|-------|----------------|
| Total governed theory rows | `157` | Small enough that heavyweight baselines are riskier than simple, rerunnable ones |
| Train split size | `109` | Training surface is limited and must remain leakage-safe |
| Validation split size | `24` | Validation metrics will be noisy if the baseline is unstable |
| Test split size | `24` | The holdout must stay frozen for fair comparison |
| Source mix | `62 seed`, `95 muestras` | Variant coverage and keyword availability will differ by source |
| Largest class | `Tipo 5 - Constructivismo moderado (67)` | Majority-class collapse is a real risk |
| Smallest class | `Tipo 3 - Antirrealismo epistemologico (6)` | Per-class metrics are mandatory, not optional |

**Implication:** the first baseline should prioritize deterministic behavior, transparent metrics, and honest coverage reporting over architectural ambition.
</current_data_profile>

<standard_stack>
## Standard Stack

### Core
| Tool | Purpose | Why Standard Here |
|------|---------|-------------------|
| Python 3.11/3.12 in repo-local `.venv` | Runtime | Matches the repo contract and existing scripts |
| `pandas` | Artifact loading and flat-file outputs | Already central to the existing data pipeline |
| `scikit-learn 1.6.x` | Linear baseline classifier and metrics | Already present in `requirements/base.txt` |
| `sentence-transformers 4.1.x` | Text embedding model for the lightweight supervised baseline | Already present in the project's ML dependency sets |
| JSON and CSV artifacts | Run manifests and reviewable outputs | Fit the repo's artifact-first workflow |

### Supporting
| Tool | Purpose | When to Use |
|------|---------|-------------|
| `joblib` or equivalent sklearn-safe serialization | Persist fitted classifier artifacts | When the trained model needs to be reloaded by `evaluate` |
| `transformers` zero-shot pipeline | Optional reference baseline | Only if it reuses the same evaluation surface cheaply |
| `pytest` | Contract and CLI verification | Required for config, dataset, artifact, and benchmark coverage |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Sentence-transformer embeddings plus a linear classifier | Immediate SetFit or heavier fine-tuning | Higher complexity and more moving parts on a very small fixed split |
| Reviewable files under `reports/` | Notebook-only outputs or opaque pickle blobs | Much weaker traceability and harder regression review |
| Governed keyword join by `record_id` | Manual spreadsheet enrichment | Violates the raw-source and governed-output rules |
</standard_stack>

<architecture_patterns>
## Architecture Patterns

### Pattern 1: Immutable Phase 2 Inputs
**What:** Treat Phase 2 gold and split artifacts as immutable inputs for all Phase 3 runs.
**When to use:** Every training, evaluation, and comparison path.
**Why:** The Phase 2 split is already frozen and required for fair comparison.

### Pattern 2: Text Variants as a Data-Layer Transform
**What:** Build `abstract_only` and `abstract_plus_keywords` through one helper keyed by `record_id`, instead of sprinkling text assembly across commands.
**When to use:** Any baseline or benchmark that changes text inputs.
**Why:** Keeps keyword fallback rules and coverage accounting consistent.

### Pattern 3: Per-Run Artifact Directories
**What:** Write each run under a deterministic directory like `reports/phase3/<run_id>/`.
**When to use:** Every train/evaluate cycle.
**Why:** Run manifests, metrics, and row-level predictions need to stay diffable and reviewable.

### Pattern 4: Shared Evaluation Surface
**What:** Keep metrics generation and label-order handling in one reusable evaluator, regardless of model family.
**When to use:** Supervised baseline delivery now, optional reference baselines later.
**Why:** Avoids metric drift across future experiments.

### Recommended Project Additions
```text
configs/
  theory_baseline.toml
src/
  abstract_classifier/
    text_variants.py
    training.py
    evaluation.py
tests/
  test_theory_baseline_config.py
  test_theory_dataset_loader.py
  test_theory_train_artifacts.py
  test_theory_evaluate_metrics_bundle.py
  test_theory_text_variants.py
  test_theory_variant_benchmark.py
```
</architecture_patterns>

<dont_hand_roll>
## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Split selection | New random train/val/test logic | Reuse `reports/phase2_split_assignments.csv` directly | Prevents leakage and keeps comparisons fair |
| Keyword enrichment | Manual spreadsheet edits | Governed join from normalized source rows keyed by `record_id` | Preserves lineage and repeatability |
| Metrics reporting | Console prints or notebook tables only | Persisted JSON/CSV artifacts | Easier diffing, review, and regression checks |
| Confidence semantics | Undocumented classifier scores | A documented scoring path in the run manifest | Future review thresholds depend on score meaning |

**Key insight:** Phase 3 is not just "train a model." It is "make classifier training and evaluation rerunnable, reviewable, and comparable on the governed split."
</dont_hand_roll>

<common_pitfalls>
## Common Pitfalls

### Pitfall 1: Variant assembly drifts from the governed row contract
**What goes wrong:** `abstract_plus_keywords` gets built with ad hoc joins or hidden notebook logic.
**How to avoid:** Centralize text assembly around `record_id` and persist coverage summaries.

### Pitfall 2: Minority classes disappear behind headline accuracy
**What goes wrong:** The model looks acceptable overall while collapsing on smaller classes like Type 3 or Type 4.
**How to avoid:** Always emit per-class precision, recall, support, and confusion matrix outputs.

### Pitfall 3: Train/evaluate commands leak validation or test state into fitting
**What goes wrong:** Preprocessing or fitting steps accidentally use rows outside the train split.
**How to avoid:** Make the dataset loader split-aware and test it directly.

### Pitfall 4: Keyword-enriched runs are overinterpreted
**What goes wrong:** `abstract_plus_keywords` appears better or worse without anyone noticing that many rows lack keywords.
**How to avoid:** Persist keyword-coverage stats by source and split alongside the comparison outputs.
</common_pitfalls>

<code_examples>
## Code Examples

### Run Manifest Shape
```python
@dataclass(frozen=True)
class TheoryRunManifest:
    run_id: str
    text_variant: str
    model_family: str
    taxonomy_config_path: str
    gold_artifact_path: str
    split_artifact_path: str
    split_version: str
```

### Comparison Row Shape
```python
@dataclass(frozen=True)
class VariantComparisonRow:
    run_id: str
    text_variant: str
    split_name: str
    accuracy: float
    macro_f1: float
    weighted_f1: float
    keyword_coverage_rate: float
```
</code_examples>

<current_best_direction>
## Current Best Direction for This Repo

| Old Direction | Current Direction | Why It Matters |
|---------------|-------------------|----------------|
| Notebook-heavy classifier experiments | Scripted `train` and `evaluate` commands backed by manifests | Matches the repo's Phase 1 and Phase 2 migration path |
| Informal text preprocessing | Governed text-variant helpers keyed by lineage | Makes variant benchmarking reproducible |
| One-off score inspection | Full evaluation bundle persisted per run | Required by `EVAL-01` and future review workflows |

**Patterns to adopt now:**
- Embedding-based supervised baseline with a documented linear classifier.
- One shared evaluator for both normal scoring and variant comparison.
- Run directories with manifest, metrics, confusion matrix, predictions, and coverage summary.

**Patterns to avoid now:**
- Rebuilding or mutating Phase 2 outputs by hand.
- Mixing model-family comparison and input-variant comparison into one large, unstable benchmark matrix.
- Treating optional zero-shot reference work as a blocker for Phase 3 completion.
</current_best_direction>

<open_questions>
## Open Questions

1. **Exact sentence-transformer model**
   - What we know: the repo already points toward sentence-transformers as the safest first supervised family.
   - What is unclear: exact model id for the first operational baseline.
   - Recommendation: choose one model in config and keep it stable across both text variants.

2. **Classifier and score semantics**
   - What we know: the baseline should stay lightweight and explainable.
   - What is unclear: balanced logistic regression versus a calibrated linear SVM.
   - Recommendation: prefer the simplest option whose score semantics can be explained in the run manifest.

3. **Optional zero-shot reference**
   - What we know: the client guidance treats zero-shot as a useful benchmark.
   - What is unclear: whether it fits comfortably inside the same implementation pass.
   - Recommendation: allow it as optional if it drops cleanly onto the same evaluator, but do not make it the blocker for Phase 3 completion.
</open_questions>

<sources>
## Sources

### Primary (HIGH confidence)
- `.planning/phases/03-baseline-theory-classifier/03-CONTEXT.md` - locked Phase 3 decisions and scope
- `.planning/ROADMAP.md` - Phase 3 success criteria and plan inventory
- `.planning/REQUIREMENTS.md` - requirement mapping for `THEO-01`, `THEO-03`, and `EVAL-01`
- `reports/phase2_gold_supervision.csv` - governed label truth
- `reports/phase2_split_assignments.csv` - frozen split contract
- `configs/taxonomy.toml` - canonical label order
- `src/abstract_classifier/io/sources.py` - governed keyword and source-metadata surface
- `src/abstract_classifier/commands/train.py` - current training gap
- `src/abstract_classifier/commands/evaluate.py` - current evaluation gap

### Secondary (MEDIUM confidence)
- `docs/alcance_cliente/aplicacion_skill_ml_pipeline.md` - recommended baseline family and metrics bundle
- `docs/alcance_cliente/gold_set_v1_spec.md` - benchmark and abstention guidance
- `docs/guia_refactor_clasificador.md` - notebook-to-script migration guidance
- `AbstractsV2.ipynb` - evidence that zero-shot and SetFit were already explored experimentally
</sources>

<metadata>
## Metadata

**Research scope:**
- Small-data supervised baseline design
- Governed text-variant assembly
- Run-artifact persistence
- Fixed-split comparison workflow

**Confidence breakdown:**
- Phase 2 artifact reuse: HIGH
- Text-variant join strategy: HIGH
- Baseline family recommendation: HIGH
- Optional zero-shot fit into scope: MEDIUM

**Research date:** 2026-04-16
**Valid until:** 2026-05-16
</metadata>

---

*Phase: 03-baseline-theory-classifier*
*Research completed: 2026-04-16*
*Ready for planning: yes*
