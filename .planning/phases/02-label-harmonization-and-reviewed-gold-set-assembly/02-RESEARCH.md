# Phase 2: Label Harmonization and Reviewed Gold Set Assembly - Research

**Researched:** 2026-04-16
**Domain:** Config-driven supervised data assembly, canonical theory mapping, reproducible gold-set splits, and methodology review contracts
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Phase 2 supervised assembly uses only `Seed/Seed.xlsx::Clasificados` and `Database/Scopus_database.xlsx::Muestras`.
- `Seed` and `Muestras` must flow through one common canonical supervised-table contract.
- `Seed` remains the default initial gold source; `Muestras` remains auxiliary reviewed supervision gated row-by-row.
- Training, evaluation, and inference dataset routing must be config-driven rather than notebook-driven.
- The canonical theory target remains the six Arbor classes already encoded in `configs/taxonomy.toml`.
- `Tipo 2 RM` and `Tipo 2 RC` remain approved aliases of canonical Type 2.
- `Tipo 6 RF`, `Tipo 4 CM`, `No`, and blank theory labels must remain explicit review states rather than silent auto-remaps.
- All supervised outputs must preserve `label_original`, `label_canonica`, `canonical_id`, `mapping_status`, `mapping_notes`, and `review_required`.
- Phase 2 must produce a canonical candidate supervised table with explicit gold inclusion flags and deduplication keys.
- Same-article groups must follow the existing exact DOI or exact title-plus-year policy and must not cross train/validation/test boundaries.
- Methodology is a separate output with the hierarchy `NN` / `no_empirico` / `empirico -> cualitativo|cuantitativo`.
- The current labeled sheets lack explicit methodology columns, so methodology work must begin as schema plus review scaffolding rather than fabricated labels.

### the agent's Discretion
- Exact output serialization details beyond mandatory CSV artifacts.
- Exact deterministic threshold for a useful abstract.
- Exact split seed value and split-manifest filename.
- Exact review reason vocabulary, provided unresolved theory and methodology cases remain distinguishable.

### Deferred Ideas (OUT OF SCOPE)
- Training the baseline theory model belongs to Phase 3.
- Methodology model training/evaluation belongs to Phase 4.
- Theme generation and correlation reporting belong to downstream phases.
</user_constraints>

<research_summary>
## Summary

Phase 2 should extend the Phase 1 package rather than invent a parallel workflow. The existing repo already has the right primitives: versioned TOML contracts, importable workbook loaders, exact-match duplicate logic, and a real `prepare` command. The safest implementation path is to add one new supervision-focused contract layer and one methodology contract layer, then assemble flat reviewable outputs from those rules.

The key planning implication is that Phase 2 is not only "map labels." It is really four linked data-governance steps: config-driven source admission, config-driven theory normalization, governed candidate-table assembly, and reproducible split generation with review artifacts. Because the labeled sheets do not carry explicit methodology columns, methodology work in this phase should focus on explicit schema, nullable fields, and review queue generation instead of pretending a reviewed methodology gold set already exists.

**Primary recommendation:** keep everything flat, config-driven, and auditable: `configs/supervision.toml` for candidate-source and theory-mapping policy, `configs/methodology.toml` for methodology hierarchy, one canonical candidate supervised table, one gold-filtered table, one split manifest, and explicit review queues for unresolved theory and methodology rows.
</research_summary>

<standard_stack>
## Standard Stack

### Core
| Tool | Purpose | Why Standard Here |
|------|---------|-------------------|
| Python 3.11/3.12 | Runtime | Already active in the repo-local `.venv` and consistent with Phase 1 |
| `tomllib` + TOML | Governance contracts | Matches the existing `configs/` pattern from Phase 1 |
| `pandas` + `openpyxl` | Workbook ingestion and flat-table outputs | Already used in `taxonomy.py` and `io/sources.py` |
| `pathlib`, `dataclasses`, `hashlib` | File handling, contracts, and deterministic `abstract_hash` creation | Standard library and enough for Phase 2 |

### Supporting
| Tool | Purpose | When to Use |
|------|---------|-------------|
| `pytest` | Contract and CLI verification | Required for mapping, split, and methodology contract coverage |
| CSV outputs | Reviewable artifacts | Mandatory for analyst-facing supervised tables and review queues |
| Optional parquet mirrors | Faster downstream loading | Only if implementation stays secondary to CSV artifacts |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Flat files + TOML | Database-backed supervision workflow | Overkill for the current milestone and weakens reviewability |
| Manual spreadsheet edits | Notebook or Excel surgery | Violates the raw-source preservation rule |
| Generic split helper only | Custom grouped split artifact | Generic stratified split alone does not solve same-article leakage |
</standard_stack>

<architecture_patterns>
## Architecture Patterns

### Pattern 1: Supervision Policy Lives in Config
**What:** Move candidate-source selection, theory mapping statuses, unresolved labels, and routing policy into versioned TOML contracts.
**When to use:** Any rule that affects whether a row can enter candidate supervision or gold.
**Why:** `TAXO-02` and `CORP-03` explicitly require config-driven behavior.

### Pattern 2: One Candidate Table, Multiple Derived Views
**What:** Build one canonical candidate supervised table, then derive filtered gold tables, split manifests, and review queues from it.
**When to use:** Any analyst-facing supervised artifact.
**Why:** The candidate table preserves lineage and traceability; derived artifacts stay reproducible.

### Pattern 3: Exact-Rule Grouping Before Split
**What:** Reuse Phase 1 DOI/title-year logic to form same-article groups before any train/validation/test split.
**When to use:** Any output that assigns rows to split buckets.
**Why:** Stratification alone does not prevent leakage when duplicates exist across `Seed` and `Muestras`.

### Pattern 4: Methodology Contract Separate from Theory Contract
**What:** Store methodology hierarchy and review reasons in their own config/module and own output columns.
**When to use:** Methodology schema generation and review export work.
**Why:** The repo already has a known anti-pattern of reusing generic confidence columns across tasks; Phase 2 should prevent that from returning.

### Recommended Project Additions
```text
configs/
  supervision.toml
  methodology.toml
src/
  abstract_classifier/
    supervision.py
    methodology.py
    splits.py
tests/
  test_supervision_config_contract.py
  test_theory_mapping_pipeline.py
  test_supervised_table_contract.py
  test_gold_split_rules.py
  test_methodology_contract.py
  test_methodology_review_exports.py
```
</architecture_patterns>

<dont_hand_roll>
## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Source selection and mapping policy | Inline constants spread across modules | TOML config contracts | Easier to diff, review, and version |
| Review workflow | Spreadsheet-only manual process | Flat exported review queues | Keeps raw files untouched and audit trail explicit |
| Split generation | Plain random split without grouping | Group-aware split manifest | Prevents same-article leakage |
| Methodology labels | Heuristic auto-filled labels with no review state | Nullable schema + explicit review queue | Current sheets do not contain reviewed methodology truth |

**Key insight:** Phase 2 is still governance work. The correct output is not a clever classifier; it is a trustworthy supervised dataset surface that later phases can consume without reinterpreting project policy.
</dont_hand_roll>

<common_pitfalls>
## Common Pitfalls

### Pitfall 1: Hard-Coded Label Rules Survive Into Phase 2
**What goes wrong:** Mapping policy remains trapped in Python constants, so policy updates require code edits rather than config reviews.
**How to avoid:** Move theory mapping statuses and candidate-source roles into explicit TOML files and test-load them.

### Pitfall 2: Gold Inclusion Logic Becomes Implicit
**What goes wrong:** Rows disappear from training data with no `include_in_gold` or exclusion rationale.
**How to avoid:** Keep candidate-table rows even when excluded and record explicit inclusion flags and review reasons.

### Pitfall 3: Duplicate Groups Leak Across Splits
**What goes wrong:** The same article or same abstract lands in both train and test because split logic ignores DOI/title grouping.
**How to avoid:** Build group keys before split and test that grouped rows stay in the same partition.

### Pitfall 4: Methodology Is Forced From Thin Evidence
**What goes wrong:** Methodology fields are filled even though the current labeled sheets do not contain reviewed methodology truth.
**How to avoid:** Make methodology nullable/reviewable and export explicit review queues until reviewed labels exist.
</common_pitfalls>

<code_examples>
## Code Examples

### Candidate Supervised Row Contract
```python
@dataclass(frozen=True)
class CandidateSupervisedRow:
    record_id: str
    source_dataset: str
    source_sheet: str
    title: str
    abstract: str
    year: int | None
    doi: str
    label_original: str
    label_canonica: str | None
    canonical_id: str | None
    mapping_status: str
    mapping_notes: str
    review_required: bool
    include_in_gold: bool
    title_normalized: str
    doi_normalized: str
    abstract_hash: str
```

### Group-Aware Split Metadata
```python
@dataclass(frozen=True)
class SplitAssignment:
    record_id: str
    split: str
    split_version: str
    split_seed: int
    group_key: str
```

### Methodology Review Shape
```python
@dataclass(frozen=True)
class MethodologyReviewRow:
    record_id: str
    methodology_label: str | None
    methodology_branch: str | None
    methodology_subtype: str | None
    methodology_review_required: bool
    methodology_review_reason: str
```
</code_examples>

<sota_updates>
## Current Best Direction for This Repo

| Old Direction | Current Direction | Why It Matters |
|---------------|-------------------|----------------|
| Hard-coded theory mapping in Python only | Config-driven supervision policy plus taxonomy contract | Satisfies `TAXO-02` and reduces policy drift |
| Inventory-only prepare step | Prepare step that can emit candidate, gold, split, and review artifacts | Makes Phase 2 outputs operational |
| Methodology implied as later modeling detail | Methodology schema defined early, with separate review columns | Prevents polluted contracts and hidden assumptions |

**Patterns to adopt now:**
- Candidate-source policy and theory mapping in TOML
- Single canonical candidate supervised table
- Group-aware split artifacts with fixed seed and version
- Separate methodology review scaffolding

**Patterns to avoid now:**
- Editing labeled spreadsheets in place
- Treating `Muestras` as automatically gold because it is smaller
- Reusing one generic `Confidence` column across theory and methodology work
</sota_updates>

<open_questions>
## Open Questions

1. **Useful abstract threshold**
   - What we know: empty or too-thin abstracts must stay out of gold.
   - What's unclear: exact deterministic threshold.
   - Recommendation: choose a documented character or token threshold plus a manual override field.

2. **Split seed value**
   - What we know: the seed must be fixed and written to artifacts.
   - What's unclear: exact numeric value.
   - Recommendation: pick one seed in Phase 2 and keep it stable for all Phase 3 comparisons.

3. **Methodology population timing**
   - What we know: the schema must exist in Phase 2.
   - What's unclear: whether reviewed methodology labels will be manually appended during Phase 2 or first consumed in Phase 4.
   - Recommendation: build the review/export surface now and let later phases decide when the reviewed methodology table becomes training truth.
</open_questions>

<sources>
## Sources

### Primary (HIGH confidence)
- `.planning/phases/02-label-harmonization-and-reviewed-gold-set-assembly/02-CONTEXT.md` - locked Phase 2 decisions and boundary
- `.planning/ROADMAP.md` - Phase 2 goal, plans, and success criteria
- `.planning/REQUIREMENTS.md` - requirement mapping for Phase 2
- `docs/alcance_cliente/decision_taxonomia_canonica.md` - canonical theory mapping policy
- `docs/alcance_cliente/gold_set_v1_spec.md` - gold-set inclusion, exclusion, and split policy
- `requirements.md` - methodology hierarchy and examples
- `src/abstract_classifier/taxonomy.py` - current theory normalization surface
- `src/abstract_classifier/io/sources.py` - workbook normalization surface
- `src/abstract_classifier/overlap.py` - exact duplicate and review policy

### Secondary (MEDIUM confidence)
- `.planning/research/CLIENT_SCOPE_2026-04-02.md` - methodology and dataset-role framing
- `docs/alcance_cliente/aplicacion_skill_ml_pipeline.md` - recommended pipeline sequencing for this project
- `docs/guia_refactor_clasificador.md` - repo refactor guidance and contract separation lessons
</sources>

<metadata>
## Metadata

**Research scope:**
- Core technology: config-driven supervised data assembly
- Data governance: label mapping, review queues, split leakage control
- Contract design: theory vs methodology separation
- Validation: deterministic outputs and CLI-driven review artifacts

**Confidence breakdown:**
- Supervision config approach: HIGH
- Candidate/gold/split artifact pattern: HIGH
- Methodology scaffolding guidance: HIGH
- Exact threshold/seed choices: MEDIUM

**Research date:** 2026-04-16
**Valid until:** 2026-05-16
</metadata>

---

*Phase: 02-label-harmonization-and-reviewed-gold-set-assembly*
*Research completed: 2026-04-16*
*Ready for planning: yes*
