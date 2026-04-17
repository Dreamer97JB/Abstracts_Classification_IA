# Phase 3: Baseline Theory Classifier - Context

**Gathered:** 2026-04-16
**Status:** Ready for planning
**Mode:** Non-interactive discuss pass using roadmap, requirements, Phase 2 outputs, and client docs

<domain>
## Phase Boundary

Build the first reproducible theory classifier over the canonical Arbor taxonomy using the governed Phase 2 gold set and fixed split, then benchmark the agreed text-input variants with explicit persisted evaluation outputs. This phase replaces the placeholder `train` and `evaluate` commands with operational paths. It does not train methodology models, and it does not run full-corpus inference or client-delivery reporting yet.

</domain>

<decisions>
## Implementation Decisions

### Supervised truth and split reuse
- **D-01:** Phase 3 must consume `reports/phase2_gold_supervision.csv` and `reports/phase2_split_assignments.csv` as the supervised truth and held-out split contract.
- **D-02:** The split contract from Phase 2 stays frozen for comparison work: `split_version = phase2_v1`, `split_seed = 20260416`, and current split sizes remain `train = 109`, `val = 24`, `test = 24`.
- **D-03:** Legacy notebook seed files such as `seed_labeled.csv` and `seed_generated.csv` remain non-canonical and cannot replace the Phase 2 governed tables.

### Baseline delivery shape
- **D-04:** Phase 3 must deliver one operational supervised baseline that trains only on the governed train split and evaluates on the governed validation/test splits.
- **D-05:** A zero-shot reference run is optional, but it cannot replace the supervised baseline as the completion condition for Phase 3.
- **D-06:** Because the current gold set is small and imbalanced (`157` rows total; class counts `67/39/26/10/9/6` across the six theory classes), the first operational baseline should favor a lightweight, interpretable small-data approach over a heavyweight end-to-end fine-tune.

### Text variants and governed enrichment
- **D-07:** Text-input variants must be explicit, config-selected options named `abstract_only` and `abstract_plus_keywords`.
- **D-08:** `reports/phase2_gold_supervision.csv` does not currently expose keyword columns, so the `abstract_plus_keywords` variant must be assembled by joining governed gold rows back to normalized source metadata keyed by `record_id`, or by an equivalent governed metadata path.
- **D-09:** If a row has no keywords available, `abstract_plus_keywords` must remain valid by falling back to the abstract text while also recording keyword-coverage statistics for the run.
- **D-10:** Variant selection must be possible without notebook edits; it belongs in config and CLI flags.

### Artifact persistence and evaluation contract
- **D-11:** Each training/evaluation run must write to a deterministic per-run directory under `reports/`, with a run manifest that captures `run_id`, config snapshot, code/model metadata, input artifact paths, and split version.
- **D-12:** The evaluation bundle must include accuracy, macro F1, weighted F1, per-class precision/recall/support, confusion matrix, and row-level predictions for the labeled split being scored.
- **D-13:** Label ordering in metrics and confusion-matrix outputs must remain aligned to `configs/taxonomy.toml`.
- **D-14:** Persisted outputs must remain reviewable flat files rather than notebook-only tables or transient console logs.
- **D-15:** Per-row prediction outputs must preserve enough metadata to support later manual error analysis and future low-confidence review exports.

### Command and scope discipline
- **D-16:** `src/abstract_classifier/commands/train.py` and `src/abstract_classifier/commands/evaluate.py` must stop using the placeholder handler in this phase.
- **D-17:** `predict` and `analyze` remain out of scope for Phase 3 unless thin internal helpers are needed for evaluation or variant comparison.
- **D-18:** Methodology columns from Phase 2 remain part of the dataset contract, but methodology modeling itself stays out of scope here.

### the agent's Discretion
- Exact sentence-transformer model name for the first supervised baseline.
- Exact linear classifier choice, provided the score semantics are documented and future review thresholds remain feasible.
- Exact file names inside the run directory, as long as the manifest, overall metrics, per-class metrics, confusion matrix, and prediction outputs are deterministic and easy to diff.
- Exact format of the optional comparison summary, as long as both agreed text variants are directly comparable on the same split.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and carry-forward decisions
- `.planning/ROADMAP.md` - Phase 3 goal, success criteria, and plan inventory.
- `.planning/REQUIREMENTS.md` - requirement ids that Phase 3 must close (`THEO-01`, `THEO-03`, `EVAL-01`).
- `.planning/STATE.md` - current project position and next action.
- `.planning/phases/02-label-harmonization-and-reviewed-gold-set-assembly/02-CONTEXT.md` - Phase 2 policy decisions that Phase 3 must preserve.
- `.planning/phases/02-label-harmonization-and-reviewed-gold-set-assembly/02-RESEARCH.md` - Phase 2 architecture patterns and anti-patterns that remain relevant.
- `.planning/phases/02-label-harmonization-and-reviewed-gold-set-assembly/02-VALIDATION.md` - existing validation cadence and style.

### Client constraints and classifier guidance
- `docs/alcance_cliente/gold_set_v1_spec.md` - held-out split, baseline-comparison, and abstention guidance.
- `docs/alcance_cliente/aplicacion_skill_ml_pipeline.md` - recommended baseline ordering, metrics bundle, and input-variant comparison.
- `docs/guia_refactor_clasificador.md` - notebook-to-script migration guidance and classifier separation lessons.
- `docs/alcance_cliente/decision_taxonomia_canonica.md` - canonical label meaning and class semantics.
- `Article/Artículo_Arbor.pdf` - semantic source of truth for the theory classes.

### Existing code and data contracts
- `configs/taxonomy.toml` - canonical label order and machine identifiers.
- `configs/sources.toml` - governed source manifest and dataset roles.
- `src/abstract_classifier/io/sources.py` - normalized source loader that already exposes `author_keywords` and `index_keywords`.
- `src/abstract_classifier/contracts/sources.py` - normalized row contract used by existing data surfaces.
- `src/abstract_classifier/supervision.py` - Phase 2 supervised-table builder and governed label outputs.
- `src/abstract_classifier/commands/train.py` - current placeholder training entrypoint to replace.
- `src/abstract_classifier/commands/evaluate.py` - current placeholder evaluation entrypoint to replace.
- `reports/phase2_candidate_supervision.csv` - candidate rows with label and lineage context.
- `reports/phase2_gold_supervision.csv` - governed trainable/evaluable label surface.
- `reports/phase2_split_assignments.csv` - fixed split contract to reuse unchanged.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/abstract_classifier/io/sources.py` already normalizes workbook rows and exposes `author_keywords` and `index_keywords`, which makes governed enrichment possible for the `abstract_plus_keywords` variant.
- `src/abstract_classifier/supervision.py` already produces the canonical Phase 2 label table keyed by `record_id`.
- `configs/taxonomy.toml` already defines the exact six-label order needed for metrics and confusion matrices.
- `reports/phase2_gold_supervision.csv` and `reports/phase2_split_assignments.csv` already encode the supervised truth and fixed split that Phase 3 needs.

### Current Gaps
- `src/abstract_classifier/commands/train.py` and `src/abstract_classifier/commands/evaluate.py` still point at the generic placeholder handler.
- No current module persists training manifests, model artifacts, or evaluation bundles.
- No current helper assembles governed text variants from the Phase 2 gold surface plus normalized source metadata.

### Dataset Realities That Affect Planning
- The governed theory gold set currently has `157` rows.
- The source mix is `62` rows from `seed` and `95` rows from `muestras`.
- The fixed split is `109` train, `24` validation, and `24` test rows.
- The class distribution is materially imbalanced, so the baseline and metrics contract must make minority-class behavior visible.

</code_context>

<specifics>
## Specific Ideas

- Add a versioned baseline config such as `configs/theory_baseline.toml` to capture input artifacts, variant defaults, and model settings.
- Persist per-run outputs under a path like `reports/phase3/<run_id>/` with at least `run_manifest.json`, `metrics_overall.json`, `metrics_per_class.csv`, `confusion_matrix.csv`, and `predictions.csv`.
- Include keyword-coverage summaries in the run manifest or a dedicated artifact so `abstract_plus_keywords` results can be interpreted honestly when `seed` rows have no keyword fields.
- Keep the first operational baseline small, deterministic, and script-driven before adding richer experiment families later.

</specifics>

<deferred>
## Deferred Ideas

- Methodology model training and methodology metrics remain Phase 4 work.
- Full-corpus prediction, review exports, and client-ready tables remain Phase 5 work.
- Persistent experiment dashboards or registries remain v2 work unless a minimal comparison manifest is needed now.

</deferred>

---

*Phase: 03-baseline-theory-classifier*
*Context gathered: 2026-04-16*
