# Phase 1: Canonical Taxonomy and Corpus Contracts - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in `01-CONTEXT.md` — this log preserves the alternatives considered.

**Date:** 2026-04-03
**Phase:** 1 - Canonical Taxonomy and Corpus Contracts
**Areas discussed:** supervision source, taxonomy source, alias policy, corpus consolidation, deduplication identity

## Discussion Summary

### 1. Gold supervision source
- **Prompt:** Which source should count as true gold supervision?
- **Alternatives considered:** `Seed.xlsx` as gold; previous generated/labeled CSVs as gold; mixed gold from all labeled artifacts.
- **User decision:** `Seed/Seed.xlsx` is the true gold source because it was labeled by the expert user who read the articles.
- **Implication:** `seed_labeled.csv` and `seed_generated.csv` remain historical artifacts only.

### 2. Taxonomy source of truth
- **Prompt:** Should Arbor override legacy spreadsheet shorthand?
- **Alternatives considered:** preserve legacy labels as target; use Arbor canon as target; keep both equal.
- **User decision:** `Article/Artículo_Arbor.pdf` is the semantic source of truth.
- **Implication:** canonical cleaned labels must follow Arbor even if the raw label is written differently.

### 3. Handling legacy label conflicts and aliases
- **Prompt:** How should `RM` and `RC` be handled?
- **Alternatives considered:** keep them separate; merge them under Type 2; delay decision.
- **User decision:** merge `RM` and `RC` as the Type 2 family (`realismo moderado / critico`).
- **Follow-up clarification:** when the legacy label conflicts with Arbor numbering, the canonical cleaned dataset should be corrected to the Arbor-consistent label rather than preserving the raw mismatch as truth.

### 4. Google and Scopus corpus strategy
- **Prompt:** Keep duplicate source rows or unify them?
- **Alternatives considered:** keep one row per source; unify into one canonical row per article.
- **User decision:** keep one row per article only.
- **Implication:** no duplicate copies across Google and Scopus in the canonical article table.

### 5. Winner row when the same article exists twice
- **Prompt:** Which row survives after deduplication?
- **Alternatives considered:** keep both; prefer Google; prefer Scopus; keep the most complete row.
- **User decision:** keep the row with the highest amount of information.
- **Additional accepted recommendation:** if information completeness is tied, prefer Scopus.

### 6. Deduplication identity rule
- **Prompt:** What should define “same article”?
- **Alternatives considered:** title-only match; DOI-only match; DOI first then title+year fallback; fuzzy match auto-merge.
- **User decision:** use this rule set:
  - exact DOI match => same article
  - if no DOI, exact normalized title + same year => same article
  - similar but not exact titles, or title match with year mismatch => manual review, no auto-merge

## Notes

- The user wants strong data cleaning and preparation before any serious modeling.
- The user wants the project to stay aligned to GSD order, so the next step after context capture is planning, not another roadmap restructure.

---

*Log created: 2026-04-03*
