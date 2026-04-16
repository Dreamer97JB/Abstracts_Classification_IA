# Phase 2: Label Harmonization and Reviewed Gold Set Assembly - Context

**Gathered:** 2026-04-16
**Status:** Ready for planning
**Mode:** Non-interactive discuss pass using existing project decisions and client specs

<domain>
## Phase Boundary

Convert the legacy labeled spreadsheets into a governed supervised dataset with explicit canonical theory mappings, gold-set inclusion rules, duplicate/leakage controls, and methodology review contracts. This phase prepares trustworthy supervised tables and review queues; it does not train the baseline classifier yet, and it does not run full-corpus inference or theme analysis.

</domain>

<decisions>
## Implementation Decisions

### Supervised source admission and dataset roles
- **D-01:** Phase 2 supervised assembly works only from `Seed/Seed.xlsx::Clasificados` and `Database/Scopus_database.xlsx::Muestras`; Google corpus and Scopus Base remain outside the gold-set workflow in this phase.
- **D-02:** `Seed` and `Muestras` must flow through one common canonical supervised-table contract rather than separate ad hoc spreadsheets.
- **D-03:** `Seed` remains the default initial gold source by policy, while `Muestras` remains auxiliary reviewed supervision that can enter `gold set v1` only through explicit row-level inclusion flags.
- **D-04:** Training, evaluation, and inference source-routing choices must be represented in versioned config files rather than notebook edits.

### Theory mapping and review policy
- **D-05:** The canonical theory target remains the six Arbor classes already encoded in `configs/taxonomy.toml`, and machine-target identifiers must stay aligned to those config IDs.
- **D-06:** Approved legacy merges remain locked: `Tipo 2 RM` and `Tipo 2 RC` both map to canonical Type 2 (`tipo_2_realismo_moderado_critico`).
- **D-07:** `Tipo 6 RF` and `Tipo 4 CM` stay `revision_manual` during Phase 2 and must not be auto-remapped into a canonical class.
- **D-08:** `No` and blank theory labels stay `sin_etiqueta` and must never be silently promoted into supervised theory labels.
- **D-09:** All supervised outputs must preserve `label_original`, `label_canonica`, `canonical_id`, `mapping_status`, `mapping_notes`, and `review_required`.
- **D-10:** Unresolved or inconsistent theory rows must be exported as review artifacts, not hidden inside logs or dropped without trace.

### Gold-set contract and leakage policy
- **D-11:** Phase 2 must produce a canonical candidate supervised table with at least `record_id`, `source_dataset`, `source_sheet`, `title`, `abstract`, `year`, `doi`, `label_original`, `label_canonica`, `canonical_id`, `mapping_status`, `mapping_notes`, `review_required`, and `include_in_gold`.
- **D-12:** Candidate supervised rows must also carry `title_normalized`, `doi_normalized`, and `abstract_hash` so deduplication and split leakage checks are explicit and reproducible.
- **D-13:** Same-article detection must reuse the Phase 1 exact-match policy: exact normalized DOI, or exact normalized title plus same year; ambiguous overlaps remain review cases.
- **D-14:** `gold set v1` may include only rows with a useful abstract, a resolvable canonical theory label, no semantic conflict, no unresolved duplicate conflict, and `review_required = false`.
- **D-15:** Split generation must be reproducible with a fixed recorded seed and split version, and same-article groups must never be split across train/validation/test.

### Methodology schema and outlier policy
- **D-16:** Methodology remains a separate supervised output from theory and must not overwrite or blur the theory contract.
- **D-17:** The primary methodology decision chain is fixed as `NN`, `no_empirico`, or `empirico`.
- **D-18:** Only rows classified as `empirico` may receive the secondary subtype `cualitativo` or `cuantitativo`.
- **D-19:** If the abstract lacks enough methodological signal, or the cues conflict with the hierarchy, the row must be flagged for review/outlier handling instead of forced into a false subtype.
- **D-20:** The current `Seed` and `Muestras` sheets do not expose explicit methodology columns, so Phase 2 should define the schema and review outputs now while leaving actual reviewed methodology population explicit, nullable, and traceable.

### the agent's Discretion
- Exact output serialization details, as long as reviewable CSV artifacts are always produced and parquet remains optional.
- Exact deterministic threshold for a "useful abstract", as long as the rule is documented and testable.
- Exact split seed value and split-manifest filename, as long as both are stored in generated artifacts.
- Exact review reason vocabulary, as long as unresolved theory and methodology cases are distinguishable in outputs.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope and carry-forward decisions
- `.planning/ROADMAP.md` - phase goal, success criteria, and plan inventory for Phase 2.
- `.planning/REQUIREMENTS.md` - requirement IDs that Phase 2 must close (`CORP-03`, `TAXO-02`, `TAXO-03`, `METH-01`, `METH-02`, `METH-03`).
- `.planning/PROJECT.md` - milestone-level constraints and current active work framing.
- `.planning/STATE.md` - current progress, blockers, and session continuity.
- `.planning/phases/01-canonical-taxonomy-and-corpus-contracts/01-CONTEXT.md` - locked Phase 1 corpus and taxonomy decisions that Phase 2 must preserve.
- `.planning/phases/01-canonical-taxonomy-and-corpus-contracts/01-RESEARCH.md` - recommended repo patterns and anti-patterns to preserve while extending the package.
- `.planning/phases/01-canonical-taxonomy-and-corpus-contracts/01-VALIDATION.md` - Phase 1 validation style and test cadence to keep consistent.

### Client taxonomy and gold-set policy
- `docs/alcance_cliente/decision_taxonomia_canonica.md` - approved canonical theory mapping policy and unresolved legacy-label cases.
- `docs/alcance_cliente/gold_set_v1_spec.md` - required gold-set columns, inclusion/exclusion rules, and split/leakage guidance.
- `.planning/research/CLIENT_SCOPE_2026-04-02.md` - corpus roles, methodology hierarchy, and confirmed label inconsistencies.
- `requirements.md` - client-authored methodology hierarchy, qualitative/quantitative examples, and outlier allowance.
- `docs/alcance_cliente/aplicacion_skill_ml_pipeline.md` - working pipeline guidance for canonical supervision, gold-set assembly, split policy, and separate methodology handling.
- `docs/guia_refactor_clasificador.md` - refactor guidance about keeping notebooks exploratory and separating theory/methodology contracts.

### Existing package contracts and Phase 2 inputs
- `configs/sources.toml` - governed source manifest and dataset roles from Phase 1.
- `configs/taxonomy.toml` - canonical Arbor theory class contract already active in the package.
- `src/abstract_classifier/taxonomy.py` - current theory normalization and taxonomy inventory implementation that Phase 2 must generalize into config-driven supervision outputs.
- `src/abstract_classifier/commands/prepare.py` - current CLI entrypoint that already emits taxonomy inventory and will likely host the next supervised-output surface.
- `src/abstract_classifier/contracts/sources.py` - normalized source row contract and lineage fields.
- `src/abstract_classifier/io/sources.py` - workbook loading, column normalization, and normalized title/DOI generation.
- `src/abstract_classifier/overlap.py` - exact duplicate rules, completeness scoring, and review routing already established in Phase 1.
- `reports/taxonomy_inventory.md` - current direct/alias/review inventory across `Seed` and `Muestras`, which is the immediate Phase 2 input surface.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/abstract_classifier/taxonomy.py`: already normalizes theory labels, preserves traceability fields, and loads both `Seed` and `Muestras`.
- `src/abstract_classifier/io/sources.py`: already knows how to normalize workbook rows into lineage-preserving records with `title_normalized` and `doi_normalized`.
- `src/abstract_classifier/overlap.py`: already encodes exact DOI and exact title-plus-year duplicate rules, completeness scoring, and manual-review routing.
- `src/abstract_classifier/commands/prepare.py`: already exposes a non-placeholder CLI path for preparation artifacts, so Phase 2 can extend rather than invent a second preparation surface.
- `configs/sources.toml` and `configs/taxonomy.toml`: already establish the repo pattern of versioned TOML contracts for data governance.

### Established Patterns
- The repo now prefers config-first contracts plus importable package code under `src/abstract_classifier/`.
- Raw workbooks are preserved; corrections belong in derived canonical outputs only.
- Reviewable artifacts are emitted as flat files rather than hidden in notebooks or databases.
- Exact-match governance comes before any fuzzy interpretation.

### Integration Points
- `Seed/Seed.xlsx::Clasificados` columns currently include `Title`, `Authors`, `Citations_counts`, `Year`, `Journal`, `Abstract`, and `Clasificación`.
- `Database/Scopus_database.xlsx::Muestras` currently includes `Author full names`, `Title`, `Year`, `DOI`, `Abstract`, `Author Keywords`, `Index Keywords`, `Clasificación`, and `Autores`.
- Neither labeled sheet currently exposes an explicit methodology column, so methodology work in Phase 2 must start from schema/review scaffolding rather than imported labels.

</code_context>

<specifics>
## Specific Ideas

- Use one canonical supervised candidate table for both `Seed` and `Muestras`, but keep source-specific inclusion decisions visible through `source_dataset` and `include_in_gold`.
- Keep `canonical_id` as the machine-stable field while preserving `label_canonica` as the human-readable theory label.
- Treat methodology as a distinct set of columns and review outputs instead of reusing theory-specific fields or generic `Confidence` columns.

</specifics>

<deferred>
## Deferred Ideas

- Baseline theory model benchmarking remains Phase 3 work.
- Methodology model training/evaluation remains Phase 4 work even though Phase 2 defines the methodology schema and review queues.
- Theme generation, correlation analysis, and reference/author reporting remain downstream phases after the supervised data contract is stable.

</deferred>

---

*Phase: 02-label-harmonization-and-reviewed-gold-set-assembly*
*Context gathered: 2026-04-16*
