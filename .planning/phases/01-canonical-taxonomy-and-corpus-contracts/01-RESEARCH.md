# Phase 1: Canonical Taxonomy and Corpus Contracts - Research

**Researched:** 2026-04-03
**Domain:** Python data pipeline refactor for governed corpus ingestion, taxonomy contracts, and CLI workflow
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- `Article/Artículo_Arbor.pdf` is the semantic source of truth for theory classification.
- Canonical classes must follow the six Arbor types even when legacy spreadsheet labels are written differently.
- Label correction happens in the cleaned canonical dataset layer; raw source files remain preserved for audit.
- `Seed/Seed.xlsx` is the only initial gold supervision source because its labels were produced by the expert user who read the articles.
- `seed_labeled.csv` and `seed_generated.csv` are legacy exploratory artifacts from the previous iteration and are not canonical supervision.
- `Database/Scopus_database.xlsx` sheet `Muestras` can be used later as an auxiliary reviewed supervision source, but it is not initial gold by default.
- `RM` and `RC` are treated as aliases of the canonical Arbor Type 2: `realismo moderado / critico`.
- When a legacy label conflicts with Arbor type numbering, the canonical cleaned dataset must be corrected to the Arbor-consistent label rather than preserving the legacy mismatch as model truth.
- Canonical cleaned outputs must preserve both `label_original` and `label_canonica` for traceability.
- Google and Scopus full corpora must be cleaned and unified into a single canonical article table with one row per article.
- Duplicate rows across corpora are not allowed in the canonical article table.
- When the same article exists in both corpora, the surviving row is the one with greater information completeness.
- If completeness is effectively tied, the Scopus row wins because it usually carries richer metadata.
- Exact `DOI` match means the records refer to the same article and must be merged.
- If `DOI` is missing, exact `title_normalized` plus the same year means the records refer to the same article and must be merged.
- Similar but non-exact titles, or title matches with year mismatch, must not be auto-merged; they go to manual review.
- The canonical cleaned article table must preserve source lineage fields such as `source_dataset` and source-sheet provenance.
- The canonical supervision table must preserve mapping and review fields such as `label_original`, `label_canonica`, `mapping_status`, and review flags.

### the agent's Discretion
- Exact normalization mechanics for `title_normalized` and `doi_normalized`
- Exact completeness scoring formula, as long as it selects the richest row and uses Scopus as the tie-breaker
- Exact file organization and config layout for source manifests and canonical tables

### Deferred Ideas (OUT OF SCOPE)
- Full gold-set assembly and inclusion/exclusion execution belong to Phase 2.
- Model selection, experiment comparison, and metric benchmarking belong to Phase 3.
- Methodology classification implementation belongs to Phase 4.
- Theme extraction, correlation outputs, and reference/author summaries belong to Phases 4 and 5.
</user_constraints>

<research_summary>
## Summary

Research focused on the safest way to move this repo from notebook-first exploration to a reproducible corpus-governance pipeline without over-engineering Phase 1. The repo already contains a working `argparse` audit script, a minimal `pyproject.toml`, validated WSL/ROCm guidance, and planning artifacts that now define the client scope more clearly than the legacy CSV outputs.

For this phase, the standard approach should stay deliberately simple: keep Python packaging minimal, use a `src/` package, expose named CLI entrypoints through `argparse`, express source and taxonomy contracts as versioned TOML files, and implement exact-match overlap rules before any fuzzy deduplication. This gives downstream phases a stable operational surface while honoring the user decision that notebooks remain exploratory only.

**Primary recommendation:** Build Phase 1 around `src/abstract_classifier/` + TOML configs + exact-match audit utilities + pytest smoke/contract tests; defer fuzzy matching, model code, and notebook replacement beyond wrappers.
</research_summary>

<standard_stack>
## Standard Stack

### Core
| Tool | Purpose | Why Standard Here |
|------|---------|-------------------|
| Python 3.11/3.12 | Runtime | Already declared in `pyproject.toml` and stable for data tooling |
| `argparse` | CLI entrypoints | Already used in `scripts/data_audit.py`; no extra dependency needed |
| `tomllib` + TOML | Config parsing | Native in Python 3.11+, matches the existing `pyproject.toml`, and is strict enough for contracts |
| `pathlib` + dataclasses | File and contract modeling | Clear, standard-library friendly, and enough for Phase 1 |

### Supporting
| Tool | Purpose | When to Use |
|------|---------|-------------|
| `pandas` + `openpyxl` | Workbook and sheet ingestion | XLSX loading, column normalization, overlap-audit inputs |
| `pytest` | Smoke and contract testing | CLI smoke, manifest loading, exact dedup rule coverage |
| CSV outputs first, parquet optional | Review and canonical artifacts | CSV for review tables; parquet only if canonical tables become large later |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `argparse` | Typer/Click | Better UX later, but unnecessary dependency for Phase 1 |
| TOML | YAML | YAML is flexible but adds a dependency and looser structure |
| Exact-match overlap only | Fuzzy title matching now | Fuzzy matching increases false merges before a review workflow exists |
</standard_stack>

<architecture_patterns>
## Architecture Patterns

### Recommended Project Structure
```text
configs/
  sources.toml
  taxonomy.toml
src/
  abstract_classifier/
    __init__.py
    cli.py
    commands/
    contracts/
    io/
    normalization.py
    overlap.py
    taxonomy.py
tests/
reports/
```

### Pattern 1: Thin CLI, Pure Functions Beneath
**What:** Keep argument parsing in `cli.py` and put real work in importable modules.
**When to use:** All named entrypoints (`audit`, `prepare`, `train`, `evaluate`, `predict`, `analyze`).
**Example:**
```python
from argparse import ArgumentParser

def build_parser() -> ArgumentParser:
    parser = ArgumentParser(prog="abstract-classifier")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("audit")
    subparsers.add_parser("prepare")
    return parser
```

### Pattern 2: Config-First Corpus Governance
**What:** Put source paths, workbook sheets, source roles, and overlap rules in versioned TOML files.
**When to use:** Any rule that should survive across runs and should not be embedded in notebook cells.
**Example:**
```python
import tomllib
from pathlib import Path

config = tomllib.loads(Path("configs/sources.toml").read_text(encoding="utf-8"))
seed_sheet = config["sources"]["seed"]["sheet"]
```

### Pattern 3: Exact-Match Audit Before Merge
**What:** Generate overlap candidates with exact normalized keys first, then send edge cases to manual review.
**When to use:** Cross-corpus deduplication for Google and Scopus.
**Example:**
```python
def choose_merge_key(row: dict[str, str]) -> tuple[str, str]:
    doi = row.get("doi_normalized", "")
    if doi:
        return ("doi", doi)
    return ("title_year", f"{row['title_normalized']}::{row['year']}")
```

### Anti-Patterns to Avoid
- **Notebook orchestration:** do not hide operational rules in notebook cells once a script/config surface exists.
- **Implicit label correction:** never overwrite raw spreadsheet labels without preserving `label_original`.
- **Fuzzy dedup in Phase 1:** do not auto-merge similar titles before manual review infrastructure exists.
</architecture_patterns>

<dont_hand_roll>
## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CLI framework | Custom command dispatcher | `argparse` | Already proven in repo; enough for named entrypoints |
| Config parsing | Ad-hoc string parsing | `tomllib` | Native, strict, versionable |
| XLSX ingestion | Manual cell loops everywhere | `pandas`/`openpyxl` loader layer | Cleaner sheet selection and column normalization |
| Dedup identity in Phase 1 | Heuristic fuzzy matcher | Exact DOI and exact title+year rules | User already locked the merge policy |

**Key insight:** Phase 1 is about governed contracts, not clever heuristics. Every extra abstraction or fuzzy rule now increases audit risk later.
</dont_hand_roll>

<common_pitfalls>
## Common Pitfalls

### Pitfall 1: Silent Taxonomy Drift
**What goes wrong:** Legacy spreadsheet shorthand leaks back into model truth.
**Why it happens:** Mapping logic lives inline and no canonical config owns the six Arbor classes.
**How to avoid:** Put canonical class IDs and alias rules in `configs/taxonomy.toml` and validate them in tests.
**Warning signs:** Mixed labels like `Tipo 6 RF` reaching train-ready tables without `mapping_status`.

### Pitfall 2: False Merges Across Corpora
**What goes wrong:** Different papers collapse into one record because title matching is too loose.
**Why it happens:** Fuzzy matching is introduced before a review queue exists.
**How to avoid:** Keep auto-merge exact only: DOI, or exact normalized title + same year.
**Warning signs:** Merge reports with cross-year collisions or title similarity scores instead of explicit keys.

### Pitfall 3: Notebook/Script Dual Truth
**What goes wrong:** The notebook and the script diverge, and nobody knows which output is authoritative.
**Why it happens:** Logic is copied instead of wrapped and shared.
**How to avoid:** Move reusable logic under `src/abstract_classifier/`; keep legacy scripts as thin wrappers if needed.
**Warning signs:** Same business rule implemented once in a notebook cell and once in a standalone script.
</common_pitfalls>

<code_examples>
## Code Examples

### Canonical Taxonomy Loader
```python
from dataclasses import dataclass
import tomllib
from pathlib import Path

@dataclass(frozen=True)
class TaxonomyConfig:
    canonical_labels: list[str]
    aliases: dict[str, str]

def load_taxonomy(path: Path) -> TaxonomyConfig:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return TaxonomyConfig(
        canonical_labels=data["taxonomy"]["canonical_labels"],
        aliases=data["taxonomy"]["aliases"],
    )
```

### Source Manifest Record
```python
from dataclasses import dataclass

@dataclass(frozen=True)
class SourceSpec:
    source_dataset: str
    path: str
    sheet: str | None
    role: str
```

### Exact Overlap Classification
```python
def classify_overlap(left: dict[str, str], right: dict[str, str]) -> str:
    if left.get("doi_normalized") and left["doi_normalized"] == right.get("doi_normalized"):
        return "merge_doi"
    if (
        left.get("title_normalized") == right.get("title_normalized")
        and left.get("year") == right.get("year")
    ):
        return "merge_title_year"
    return "manual_review"
```
</code_examples>

<sota_updates>
## Current Best Direction for This Repo

| Old Direction | Current Direction | Why It Matters |
|---------------|-------------------|----------------|
| Notebook-first execution | Script/module pipeline with notebooks as exploratory views | Gives reproducibility and clearer audit trails |
| Legacy CSVs as pseudo-gold | `Seed/Seed.xlsx` + canonical config as supervised truth | Aligns training with expert labels and Arbor |
| Free-form spreadsheet shorthand | Versioned taxonomy/source contracts | Prevents silent drift between runs |

**New patterns to adopt now:**
- Config-driven source manifests with lineage fields
- Exact-match overlap audits before training
- Minimal CLI smoke tests for every named entrypoint

**Outdated patterns to retire:**
- Treating `seed_generated.csv` as trustworthy gold
- Embedding merge and label rules only inside notebooks
- Reusing the same output column semantics across different tasks
</sota_updates>

<open_questions>
## Open Questions

1. **Canonical storage format after audit**
   - What we know: CSV review outputs are necessary.
   - What's unclear: whether Phase 1 should also emit parquet canonical tables immediately.
   - Recommendation: make CSV mandatory; keep parquet optional behind the same contract.

2. **Completeness scoring formula**
   - What we know: richer row wins and Scopus is the tie-breaker.
   - What's unclear: exact weights for abstract, DOI, keywords, references, and year.
   - Recommendation: implement an explicit field-presence score and record it in the overlap report.

3. **When `Muestras` becomes supervised input**
   - What we know: not initial gold by default.
   - What's unclear: whether its reviewed subset will be admitted at the start or middle of Phase 2.
   - Recommendation: treat it as an auxiliary reviewed queue only until Phase 2 mapping rules are automated.
</open_questions>

<sources>
## Sources

### Primary (HIGH confidence)
- `.planning/phases/01-canonical-taxonomy-and-corpus-contracts/01-CONTEXT.md` - locked decisions and phase boundary
- `.planning/ROADMAP.md` - phase goal, required plans, success criteria
- `.planning/REQUIREMENTS.md` - requirement mapping for Phase 1
- `docs/guia_refactor_clasificador.md` - current repo risks and recommended target structure
- `scripts/data_audit.py` - existing operational script and current CLI style
- `README.md` - bootstrap and script surface currently exposed to analysts

### Secondary (MEDIUM confidence)
- `docs/alcance_cliente/decision_taxonomia_canonica.md` - canonical-label rationale
- `docs/alcance_cliente/gold_set_v1_spec.md` - downstream gold-set expectations to preserve while Phase 1 builds contracts
</sources>

<metadata>
## Metadata

**Research scope:**
- Core technology: Python package/CLI structure for data governance
- Ecosystem: config loading, workbook ingestion, audit contracts
- Patterns: thin CLI, config-first governance, exact-match overlap
- Pitfalls: taxonomy drift, false merges, notebook/script divergence

**Confidence breakdown:**
- Standard stack: HIGH - grounded in repo state and stable Python primitives
- Architecture: HIGH - driven by locked phase requirements
- Pitfalls: HIGH - directly evidenced by current repo and client scope notes
- Code examples: MEDIUM - recommended patterns, to be validated during implementation

**Research date:** 2026-04-03
**Valid until:** 2026-05-03
</metadata>

---

*Phase: 01-canonical-taxonomy-and-corpus-contracts*
*Research completed: 2026-04-03*
*Ready for planning: yes*
