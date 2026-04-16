# Phase 2: Label Harmonization and Reviewed Gold Set Assembly - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in `02-CONTEXT.md`; this log preserves the alternatives considered.

**Date:** 2026-04-16
**Phase:** 02-label-harmonization-and-reviewed-gold-set-assembly
**Mode:** Non-interactive defaults from canonical project docs
**Areas discussed:** supervised source policy, theory mapping conflict handling, gold-set contract and leakage control, methodology schema and review handling

---

## Supervised Source Policy

| Option | Description | Selected |
|--------|-------------|----------|
| `Seed` only | Treat only `Seed/Seed.xlsx` as the candidate supervised table and ignore `Muestras` until a later phase. | |
| Unified candidate table with source-specific inclusion policy | Build one canonical candidate table from `Seed` and `Muestras`, but keep `Seed` as default gold and gate `Muestras` row-by-row with `include_in_gold`. | ✓ |
| Trust both sources equally by default | Admit `Seed` and `Muestras` into gold without source-specific policy or gating. | |

**Chosen outcome:** Unified candidate table with source-specific inclusion policy.

**Notes:** This matches `.planning/phases/01-canonical-taxonomy-and-corpus-contracts/01-CONTEXT.md`, `docs/alcance_cliente/gold_set_v1_spec.md`, and `.planning/research/CLIENT_SCOPE_2026-04-02.md`. The source choice was derived from existing project decisions rather than a new interactive prompt.

---

## Theory Mapping Conflict Handling

| Option | Description | Selected |
|--------|-------------|----------|
| Auto-remap unresolved conflicts | Force `Tipo 6 RF`, `Tipo 4 CM`, `No`, and blanks into the nearest canonical class. | |
| Keep unresolved conflicts as explicit review cases | Preserve approved direct/alias mappings, but export unresolved and missing labels as `revision_manual` or `sin_etiqueta`. | ✓ |
| Drop unresolved rows silently | Exclude unresolved labels from outputs without a first-class review artifact. | |

**Chosen outcome:** Keep unresolved conflicts as explicit review cases.

**Notes:** This follows `docs/alcance_cliente/decision_taxonomia_canonica.md`, the Phase 1 taxonomy inventory contract, and the requirement to preserve `label_original` plus `label_canonica`.

---

## Gold-Set Contract and Leakage Control

| Option | Description | Selected |
|--------|-------------|----------|
| Gold-only output | Emit only trainable rows and discard review/exclusion evidence. | |
| One candidate table plus explicit review and split artifacts | Preserve all candidate rows, include review flags and gold inclusion flags, and generate separate split/leakage artifacts. | ✓ |
| Separate spreadsheet workflow by source | Keep `Seed` and `Muestras` in independent spreadsheets and deduplicate manually outside the package. | |

**Chosen outcome:** One candidate table plus explicit review and split artifacts.

**Notes:** The selected path is grounded in `docs/alcance_cliente/gold_set_v1_spec.md`, Phase 1 overlap rules, and the repo-wide preference for governed package outputs over spreadsheet surgery.

---

## Methodology Schema and Review Handling

| Option | Description | Selected |
|--------|-------------|----------|
| Delay methodology entirely to Phase 4 | Ignore methodology in Phase 2 even though the roadmap requires schema and review handling now. | |
| Define methodology schema and review scaffolding now, model it later | Encode the hierarchy and review states in Phase 2 outputs without pretending the current sheets already contain reviewed methodology labels. | ✓ |
| Infer methodology heuristically without review state | Populate methodology fields automatically from current abstracts and skip explicit review queues. | |

**Chosen outcome:** Define methodology schema and review scaffolding now, model it later.

**Notes:** The labeled workbooks currently lack an explicit methodology column, but `requirements.md`, `.planning/research/CLIENT_SCOPE_2026-04-02.md`, and `docs/alcance_cliente/aplicacion_skill_ml_pipeline.md` make the hierarchy mandatory for Phase 2 outputs.

---

## the agent's Discretion

- Exact deterministic threshold for abstract usefulness.
- Exact split seed value and manifest filename.
- Exact review-reason vocabulary for theory and methodology queues.
- Optional parquet mirrors, provided CSV review artifacts are still emitted.

## Deferred Ideas

- Baseline theory model comparison remains Phase 3 work.
- Methodology model training/evaluation remains downstream after the schema and review contract exist.
- Themes, correlations, and reference/author analysis remain outside Phase 2.
