# Phase 4: Methodology and Theme Pipeline - Context

**Gathered:** 2026-04-17
**Status:** Ready for planning and execution
**Mode:** Non-interactive discuss pass using roadmap, requirements, Phase 2/3 outputs, and client notes

<domain>
## Phase Boundary

Add the first operational methodology-classification workflow and the first governed theme-analysis workflow without changing the canonical theory contract. This phase should replace the placeholder `analyze` command with a run-bundle surface that writes methodology outputs, optional methodology evaluation artifacts when reviewed labels exist, and separate theme outputs tied to the same run context.

</domain>

<decisions>
## Implementation Decisions

### Methodology reality and delivery shape
- **D-01:** The current repo still has no reviewed methodology gold labels in `reports/phase2_methodology.csv`; every row is currently review scaffolding with `missing_source_columns`.
- **D-02:** Because reviewed methodology truth is not yet present, Phase 4 should deliver a governed heuristic methodology classifier now and an optional evaluation path that activates only when a reviewed methodology artifact is supplied.
- **D-03:** The methodology hierarchy remains exactly `NN`, `no_empirico`, and `empirico`, with `empirico` optionally refined into `cualitativo` or `cuantitativo`.
- **D-04:** Outliers, conflicting cues, and insufficient subtype evidence must be flagged explicitly rather than forced into a false subtype.

### Run-bundle contract
- **D-05:** The operational entrypoint for Phase 4 should be `analyze`, because `predict` remains reserved for Phase 5 full-corpus inference.
- **D-06:** `analyze` must write a deterministic run directory with a manifest that records the input artifact, config files, run id, text variant, and the produced methodology/theme artifacts.
- **D-07:** Methodology outputs must be flat files separate from theory outputs; they can carry copied theory context columns, but they must not overwrite the source artifact in place.
- **D-08:** Theme outputs must also remain separate flat files and must never mutate or replace theory/methodology columns in the input artifact.

### Governed input and enrichment
- **D-09:** Phase 4 should default to the governed Phase 2 gold artifact as its analyzed corpus because Phase 5 is the point where full-corpus inference expands beyond the labeled split.
- **D-10:** Keyword enrichment and keyword-derived themes must stay governed and keyed by `record_id`, reusing the existing source metadata loaders.
- **D-11:** Theme extraction should prefer governed author/index keywords when available and fall back to a lightweight text-only extractor when keywords are missing.

### Evaluation scope
- **D-12:** The methodology evaluation bundle must be optional and should produce overall metrics, per-class metrics, confusion matrices, and row-level predictions only when reviewed methodology labels are supplied.
- **D-13:** In the absence of reviewed labels, the methodology run summary must state that evaluation was skipped rather than inventing metrics.

### the agent's Discretion
- Exact heuristic cue vocabulary, as long as it remains config-driven and auditable.
- Exact theme extraction fallback, as long as it stays lightweight, deterministic, and notebook-free.
- Exact artifact filenames inside the run directory, as long as they remain stable and reviewable.

</decisions>

<canonical_refs>
## Canonical References

### Scope and carry-forward decisions
- `.planning/ROADMAP.md` - Phase 4 goal, success criteria, and plan inventory.
- `.planning/REQUIREMENTS.md` - requirement ids that Phase 4 must close (`EVAL-02`, `METH-01`, `METH-02`, `METH-03`, `ANLY-01`).
- `.planning/STATE.md` - current project position and next action.
- `.planning/PROJECT.md` - active project framing after Phase 3.
- `.planning/phases/02-label-harmonization-and-reviewed-gold-set-assembly/02-CONTEXT.md` - methodology hierarchy and review-scaffolding rules.
- `.planning/phases/03-baseline-theory-classifier/03-CONTEXT.md` - run-bundle and governed-metadata patterns to reuse.

### Client constraints and analytical guidance
- `.planning/research/CLIENT_SCOPE_2026-04-02.md` - client methodology hierarchy, theme expectations, and metadata-rich corpus notes.
- `requirements.md` - client-authored methodology examples and analytical asks.
- `docs/alcance_cliente/aplicacion_skill_ml_pipeline.md` - methodology staging guidance and downstream-analysis expectations.
- `docs/guia_refactor_clasificador.md` - keep notebooks exploratory and separate theory/methodology/theme outputs.
- `Article/Artículo_Arbor.pdf` - semantic source of truth for the theory families that remain untouched in this phase.

### Existing code and data contracts
- `configs/methodology.toml` - governed methodology branch/subtype contract and review-reason vocabulary.
- `configs/supervision.toml` - governed Phase 2 sources and split defaults.
- `reports/phase2_gold_supervision.csv` - default classified input artifact for Phase 4 execution.
- `reports/phase2_methodology.csv` - current methodology scaffold output showing the lack of reviewed labels.
- `src/abstract_classifier/methodology.py` - methodology contract loader and assignment validator.
- `src/abstract_classifier/text_variants.py` - governed keyword metadata and text-variant helpers.
- `src/abstract_classifier/io/sources.py` - normalized source loader exposing keywords and references.
- `src/abstract_classifier/commands/analyze.py` - current placeholder entrypoint to replace.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Phase 3 already established the preferred artifact pattern: config-driven execution, deterministic run directories, JSON manifests, and reviewable CSV outputs.
- `load_governed_text_metadata` already joins keyword metadata by `record_id`, which is exactly what Phase 4 needs for both methodology heuristics and theme extraction.
- `validate_methodology_assignment` already enforces the methodology contract and can protect the new heuristic flow from invalid label/subtype states.

### Current Gaps
- `analyze` is still a placeholder.
- No module exists yet for heuristic methodology inference or optional methodology evaluation.
- No governed theme extraction module exists yet outside the legacy notebooks.

### Dataset Realities That Affect Planning
- The current governed methodology table contains no reviewed labels and therefore cannot support honest supervised training yet.
- The current Phase 2 gold set is still the safest Phase 4 execution surface because it already preserves theory lineage and split provenance.
- `muestras` rows often have governed keywords while many `seed` rows do not, so both methodology and theme outputs must handle mixed metadata coverage honestly.

</code_context>

<specifics>
## Specific Ideas

- Add a versioned methodology-analysis config that stores heuristic cue lists, the default input artifact, and the default text variant.
- Add a versioned theme-analysis config that stores keyword-first fallback behavior plus a deterministic TF-IDF fallback for rows without keywords.
- Replace the placeholder `analyze` command with one operational workflow that can:
  - classify methodology heuristically,
  - optionally evaluate against reviewed methodology labels,
  - extract themes into separate outputs,
  - persist one combined manifest for the run.
- Persist smoke outputs under `reports/tmp_phase4/` so later execution agents can rerun the same regression path.

</specifics>

<deferred>
## Deferred Ideas

- Full-corpus prediction and client-ready simplified deliverables remain Phase 5.
- Correlation tables crossing theory labels with authors, references, or keywords remain Phase 5.
- Supervised methodology training remains deferred until reviewed methodology labels exist.

</deferred>

---

*Phase: 04-methodology-and-theme-pipeline*
*Context gathered: 2026-04-17*
