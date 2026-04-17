# Phase 4: Methodology and Theme Pipeline - Research

**Researched:** 2026-04-17
**Domain:** Heuristic methodology classification, optional methodology evaluation, keyword-first theme extraction, and run-bundle artifact design
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Phase 4 must keep the theory contract untouched and produce separate methodology and theme outputs.
- The methodology hierarchy is fixed as `NN`, `no_empirico`, and `empirico -> cualitativo|cuantitativo`.
- Outliers and conflicting cues must be flagged instead of forced.
- Reviewed methodology labels do not currently exist in the repo, so evaluation must be optional rather than fabricated.
- `analyze` should become the operational entrypoint for this phase.
- Governed keyword metadata must continue to flow through `record_id`.

### the agent's Discretion
- Exact cue lists for heuristic methodology classification.
- Exact theme-fallback technique.
- Exact artifact names inside the Phase 4 run directory.

### Deferred Ideas (OUT OF SCOPE)
- Full-corpus inference.
- Correlation tables over authors/references/labels.
- Heavy topic-modeling stacks such as BERTopic in the operational path.
</user_constraints>

<research_summary>
## Summary

Phase 4 should not pretend the repo already has methodology training truth. The right move is to turn methodology into a governed inference-and-review workflow first: infer the hierarchy from explicit text cues, persist the evidence and review reasons, and make evaluation possible the moment reviewed labels arrive. That closes the operational gap without inventing fake gold.

For themes, the repo does not need a heavyweight topic-modeling dependency to satisfy the current phase goal. The strongest governed signal already comes from Scopus keywords, and the remaining rows can be covered by a deterministic TF-IDF fallback over title-plus-abstract text. This produces separate, audit-friendly theme outputs now while keeping BERTopic-style exploratory work in notebooks where it belongs.

**Primary recommendation:** implement one `analyze` run bundle that orchestrates two lightweight modules: methodology heuristics plus optional evaluation, and theme extraction plus summary outputs.
</research_summary>

<standard_stack>
## Standard Stack

### Core
| Tool | Purpose | Why Standard Here |
|------|---------|-------------------|
| Python 3.11 in repo-local `.venv` | Runtime | Matches the repo contract and existing scripts |
| `pandas` | Input/output artifact work | Already central to the project |
| `scikit-learn 1.6.x` | TF-IDF fallback and methodology metrics | Already present from Phase 3 |
| JSON and CSV artifacts | Run manifest and reviewable outputs | Matches the established artifact-first workflow |

### Supporting
| Tool | Purpose | When to Use |
|------|---------|-------------|
| `text_variants.load_governed_text_metadata` | Governed keyword lookup by `record_id` | Always for keyword-aware methodology/theme work |
| `validate_methodology_assignment` | Contract validation | Always before persisting methodology rows |
| `pytest` | Unit and CLI verification | Required for heuristic, metrics, and command coverage |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Heuristic methodology inference | Supervised classifier today | No reviewed methodology labels exist yet |
| Keyword-first plus TF-IDF fallback | Immediate BERTopic pipeline | Heavier dependency surface and weaker determinism for operational smoke paths |
| Separate methodology/theme output files | Writing columns back into the classified artifact | Violates the requirement to keep outputs separate and reviewable |
</standard_stack>

<architecture_patterns>
## Architecture Patterns

### Pattern 1: Heuristic-first methodology staging
**What:** Use config-driven cue matching to infer `NN`, `no_empirico`, and `empirico`, then refine empirical rows to `cualitativo` or `cuantitativo` only when evidence is clear.
**When to use:** Until reviewed methodology labels become available.
**Why:** Closes the operational gap honestly without pretending there is supervised truth already.

### Pattern 2: Optional evaluation surface
**What:** Merge a reviewed methodology artifact by `record_id` only when it is supplied, then write a metrics bundle with the same artifact discipline used in Phase 3.
**When to use:** Any time manually reviewed methodology labels are available.
**Why:** Satisfies `EVAL-02` without blocking current execution on missing gold.

### Pattern 3: Keyword-first theme extraction
**What:** Prefer governed `author_keywords` and `index_keywords` for theme assignment; only use TF-IDF fallback when keywords are absent.
**When to use:** Every Phase 4 theme run.
**Why:** The client explicitly highlighted Scopus metadata richness, and keywords are more semantically grounded than pure unsupervised clustering at this stage.

### Pattern 4: Combined run manifest with separated artifact families
**What:** Persist one run manifest plus separate methodology and theme artifacts under the same run directory.
**When to use:** Every `analyze` execution.
**Why:** Preserves traceability while keeping the output contracts distinct.

### Recommended Project Additions
```text
configs/
  methodology_baseline.toml
  theme_pipeline.toml
src/
  abstract_classifier/
    analysis.py
    methodology_pipeline.py
    theme_analysis.py
tests/
  test_methodology_pipeline.py
  test_theme_analysis.py
  test_analyze_command.py
```
</architecture_patterns>

<dont_hand_roll>
## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Methodology gold labels | Fake reviewed methodology columns in repo artifacts | Optional reviewed-label input surface | Keeps the current data reality honest |
| Theme enrichment | Notebook-only BERTopic outputs as the operational contract | Keyword-first extraction plus deterministic TF-IDF fallback | Lighter, faster, and easier to regression test |
| Artifact lineage | Console-only summaries | Persisted JSON/CSV files tied to a run manifest | Matches the repo's current execution standards |
</dont_hand_roll>

<common_pitfalls>
## Common Pitfalls

### Pitfall 1: Treating missing methodology gold as a blocker
**What goes wrong:** Phase 4 stalls because there is no reviewed methodology dataset yet.
**How to avoid:** Separate inference/review outputs from optional evaluation outputs.

### Pitfall 2: Forcing subtype predictions when cues conflict
**What goes wrong:** A row gets a false qualitative or quantitative subtype despite mixed evidence.
**How to avoid:** Emit `methodology_review_required = true` with an explicit conflicting or insufficient-evidence reason.

### Pitfall 3: Letting theme outputs overwrite the classified corpus
**What goes wrong:** Theme columns get written back into the input artifact and blur the main contracts.
**How to avoid:** Write a separate `theme_assignments.csv` and `theme_summary.csv` instead.

### Pitfall 4: Overengineering the first operational theme pipeline
**What goes wrong:** The repo absorbs a large topic-modeling stack before the basic output contract is stable.
**How to avoid:** Keep Phase 4 deterministic and lightweight; leave richer exploratory topic models to notebooks and Phase 5 follow-ups.
</common_pitfalls>

<current_best_direction>
## Current Best Direction for This Repo

| Old Direction | Current Direction | Why It Matters |
|---------------|-------------------|----------------|
| Placeholder `analyze` command | One operational Phase 4 analysis bundle | Closes the command-level gap in `OPS-01` without waiting for Phase 5 |
| Methodology scaffold only | Heuristic methodology output plus optional evaluation | Makes the methodology workflow usable now |
| Notebook-heavy topic work | Governed keyword-first theme outputs with TF-IDF fallback | Produces auditable, rerunnable artifacts |

**Patterns to adopt now:**
- Config-driven heuristic methodology inference.
- Optional metrics bundle keyed by external reviewed labels.
- Separate methodology and theme artifact families under one run manifest.

**Patterns to avoid now:**
- Pretending methodology is already a supervised modeling problem.
- Heavy unsupervised topic stacks in the operational CLI path.
- Writing analytical outputs back into the classified source artifact.
</current_best_direction>

<open_questions>
## Open Questions

1. **Exact heuristic vocabulary**
   - What we know: the client gave concrete qualitative and quantitative examples.
   - What is unclear: the exact first cue list.
   - Recommendation: keep the first cue list explicit in TOML so it can be edited without code changes.

2. **Default analyzed artifact**
   - What we know: Phase 5 owns full-corpus inference.
   - What is unclear: whether Phase 4 should default to the gold set or the broader candidate set.
   - Recommendation: default to `reports/phase2_gold_supervision.csv` and make the input artifact overridable.

3. **Theme fallback aggressiveness**
   - What we know: some rows lack keywords.
   - What is unclear: how many fallback themes should be emitted per row.
   - Recommendation: keep the fallback small and deterministic, such as top `3` TF-IDF terms/phrases per uncovered row.
</open_questions>

<sources>
## Sources

### Primary (HIGH confidence)
- `.planning/phases/04-methodology-and-theme-pipeline/04-CONTEXT.md` - locked Phase 4 decisions and scope
- `.planning/ROADMAP.md` - Phase 4 success criteria and plan inventory
- `.planning/REQUIREMENTS.md` - `METH-*`, `EVAL-02`, and `ANLY-01`
- `.planning/research/CLIENT_SCOPE_2026-04-02.md` - client methodology and theme scope
- `requirements.md` - methodology examples and output asks
- `reports/phase2_methodology.csv` - proof that reviewed methodology labels are not yet present
- `reports/phase2_gold_supervision.csv` - stable classified input surface
- `configs/methodology.toml` - methodology contract
- `src/abstract_classifier/methodology.py` - methodology assignment validator
- `src/abstract_classifier/text_variants.py` - governed keyword metadata loader

### Secondary (MEDIUM confidence)
- `docs/alcance_cliente/aplicacion_skill_ml_pipeline.md` - staged methodology and downstream analysis guidance
- `docs/guia_refactor_clasificador.md` - notebook separation guidance
- `AbstractsV2.ipynb` - evidence that BERTopic and notebook-driven downstream analyses exist but should not define the operational CLI path
</sources>

<metadata>
## Metadata

**Research scope:**
- Heuristic methodology inference
- Optional evaluation bundle design
- Theme extraction output contracts
- `analyze` command replacement

**Confidence breakdown:**
- Methodology staging strategy: HIGH
- Theme extraction direction: HIGH
- Default analyzed artifact choice: MEDIUM

**Research date:** 2026-04-17
**Valid until:** 2026-05-17
</metadata>

---

*Phase: 04-methodology-and-theme-pipeline*
*Research completed: 2026-04-17*
*Ready for planning: yes*
