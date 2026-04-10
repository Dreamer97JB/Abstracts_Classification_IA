# Phase 1: Canonical Taxonomy and Corpus Contracts - Context

**Gathered:** 2026-04-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Lock the semantic source of truth and the dataset contracts before any training work starts, while also defining the script and config surface that will replace notebook-only execution for corpus audit and preparation. This phase does not implement training, evaluation, or the full gold-set assembly; it defines the canonical taxonomy, supervision source rules, row identity and deduplication policy, and the raw-to-canonical table contracts that downstream phases must use.

</domain>

<decisions>
## Implementation Decisions

### Canonical taxonomy source
- **D-01:** `Article/Artículo_Arbor.pdf` is the semantic source of truth for theory classification.
- **D-02:** Canonical classes must follow the six Arbor types even when legacy spreadsheet labels are written differently.
- **D-03:** Label correction happens in the cleaned canonical dataset layer; raw source files remain preserved for audit.

### Supervision source policy
- **D-04:** `Seed/Seed.xlsx` is the only initial gold supervision source because its labels were produced by the expert user who read the articles.
- **D-05:** `seed_labeled.csv` and `seed_generated.csv` are legacy exploratory artifacts from the previous iteration and are not canonical supervision.
- **D-06:** `Database/Scopus_database.xlsx` sheet `Muestras` can be used later as an auxiliary reviewed supervision source, but it is not initial gold by default.

### Legacy label mapping policy
- **D-07:** `RM` and `RC` are treated as aliases of the canonical Arbor Type 2: `realismo moderado / critico`.
- **D-08:** When a legacy label conflicts with Arbor type numbering, the canonical cleaned dataset must be corrected to the Arbor-consistent label rather than preserving the legacy mismatch as model truth.
- **D-09:** Canonical cleaned outputs must preserve both `label_original` and `label_canonica` for traceability.

### Corpus consolidation policy
- **D-10:** Google and Scopus full corpora must be cleaned and unified into a single canonical article table with one row per article.
- **D-11:** Duplicate rows across corpora are not allowed in the canonical article table.
- **D-12:** When the same article exists in both corpora, the surviving row is the one with greater information completeness.
- **D-13:** If completeness is effectively tied, the Scopus row wins because it usually carries richer metadata.

### Article identity and deduplication
- **D-14:** Exact `DOI` match means the records refer to the same article and must be merged.
- **D-15:** If `DOI` is missing, exact `title_normalized` plus the same year means the records refer to the same article and must be merged.
- **D-16:** Similar but non-exact titles, or title matches with year mismatch, must not be auto-merged; they go to manual review.

### Canonical table contract
- **D-17:** The canonical cleaned article table must preserve source lineage fields such as `source_dataset` and source-sheet provenance.
- **D-18:** The canonical supervision table must preserve mapping and review fields such as `label_original`, `label_canonica`, `mapping_status`, and review flags.

### the agent's Discretion
- Exact normalization mechanics for `title_normalized` and `doi_normalized`
- Exact completeness scoring formula, as long as it selects the richest row and uses Scopus as the tie-breaker
- Exact file organization and config layout for source manifests and canonical tables

</decisions>

<specifics>
## Specific Ideas

- The expert user considers `Seed/Seed.xlsx` the only true gold source because those classifications were created after reading the underlying articles.
- The user wants one consolidated row per article in the unified corpus, never duplicated rows by source.
- The user wants strong data cleaning before modeling: deduplication, removal of incomplete records, and explicit preparation contracts.
- The user wants the project to stay aligned to the Arbor article even when the spreadsheet shorthand is inconsistent.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Taxonomy and semantic truth
- `Article/Artículo_Arbor.pdf` - canonical six-type theory taxonomy and official type numbering
- `docs/alcance_cliente/decision_taxonomia_canonica.md` - approved decision to predict canonical Arbor labels rather than legacy labels

### Gold-set and supervision rules
- `docs/alcance_cliente/gold_set_v1_spec.md` - current supervision, inclusion/exclusion, split, and outlier policy
- `Seed/Seed.xlsx` - only initial gold supervision source

### Client constraints and scope
- `requirements.md` - methodology hierarchy and requested client-facing outputs
- `.planning/research/CLIENT_SCOPE_2026-04-02.md` - corpus audit, scope changes, and label inconsistency findings
- `.planning/PROJECT.md` - milestone goal and project-level constraints
- `.planning/REQUIREMENTS.md` - phase-level requirement mapping for taxonomy and corpus contracts
- `.planning/ROADMAP.md` - phase boundary and success criteria

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `AbstractsV2.ipynb`: existing notebook contains cleaning, classification, methodology, and export logic that can be mined during planning, even though it is no longer the source of truth.
- Root-level CSV and HTML artifacts: useful as historical references for output shapes and current exploratory workflow.

### Established Patterns
- The repo is currently notebook-first and root-file oriented.
- Validation is minimal today and most configuration is embedded inline in notebook cells.
- There is no established package, module, or automated test structure yet.

### Integration Points
- Existing root data files and the new `Database/` and `Seed/` workbooks are the main ingestion points.
- WSL ROCm is already validated and should remain the default training/runtime environment for downstream ML work.
- Phase 1 planning should assume that new scripts and config can coexist with the notebook while gradually replacing it as the operational entrypoint.

</code_context>

<deferred>
## Deferred Ideas

- Full gold-set assembly and inclusion/exclusion execution belong to Phase 2.
- Model selection, experiment comparison, and metric benchmarking belong to Phase 3.
- Methodology classification implementation belongs to Phase 4.
- Theme extraction, correlation outputs, and reference/author summaries belong to Phases 4 and 5.

</deferred>

---

*Phase: 01-canonical-taxonomy-and-corpus-contracts*
*Context gathered: 2026-04-03*
