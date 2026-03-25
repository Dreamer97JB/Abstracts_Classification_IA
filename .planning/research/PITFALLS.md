# Pitfalls Research

**Domain:** academic abstract classification pipeline refactor
**Researched:** 2026-03-24
**Confidence:** HIGH

## Critical Pitfalls

### Pitfall 1: Refactoring structure without fixing data contracts

- **Why it happens:** It is tempting to move notebook code into scripts while keeping the same fragile CSV assumptions.
- **Why it matters:** The project looks cleaner on the surface but still cannot trust incoming labels, processed data, or downstream outputs.
- **How to avoid it:** Define schema and validation gates before training logic becomes the center of work.
- **Phase that should address it:** Phase 2

### Pitfall 2: Training on synthetic seeds as if they were gold data

- **Why it happens:** Synthetic examples are already available and feel like quick leverage.
- **Why it matters:** The current synthetic seed set is repetitive and can create misleadingly stable training behavior.
- **How to avoid it:** Keep synthetic seeds auxiliary and gate training quality around real labeled examples plus explicit validation.
- **Phase that should address it:** Phase 2 and Phase 3

### Pitfall 3: Mixing classifier, topic, and methodology outputs in one contract

- **Why it happens:** The notebook evolved by layering tasks into one DataFrame.
- **Why it matters:** Shared columns like `Confidence` become ambiguous and downstream analysis becomes unreliable.
- **How to avoid it:** Separate task-specific outputs and keep optional analysis modules isolated from the main classifier contract.
- **Phase that should address it:** Phase 4 and Phase 5

### Pitfall 4: Treating environment setup as finished but not reproducible

- **Why it happens:** Once a machine works, teams often stop documenting the setup path.
- **Why it matters:** The next machine, next session, or next collaborator loses the working GPU path.
- **How to avoid it:** Keep bootstrap and verification scripts inside the repo and use them as the supported path.
- **Phase that should address it:** Phase 1

### Pitfall 5: Optimizing optional analyses before the main classifier is measurable

- **Why it happens:** Topic charts and rich outputs are visible and satisfying.
- **Why it matters:** The milestone can drift into polishing unstable secondary outputs while the main classifier remains weakly governed.
- **How to avoid it:** Lock classifier audit, training, evaluation, and inference first; move optional analyses to the end of the roadmap.
- **Phase that should address it:** Phase 5

## Warning Signs

| Warning Sign | Meaning | Action |
|--------------|---------|--------|
| New scripts still require manual cell execution in the notebook | The notebook is still the source of truth | Stop and move the missing logic into package modules |
| A new run cannot explain which config produced an output CSV | Artifact lineage is still weak | Add run metadata and manifests before continuing |
| Topic or methodology work blocks the main classifier phase | Scope is drifting away from the core value | Re-sequence optional analysis to the final phase |
| New label files arrive and no validator rejects malformed rows | Data governance is incomplete | Treat validation as a blocker, not an enhancement |

## Prevention Strategy

- Put schema validation ahead of model code
- Save run metadata every time a model is trained or used for batch inference
- Keep score columns task-specific
- Make notebooks downstream consumers, not upstream orchestrators
- Preserve historical artifacts, but do not let them define the new contract

## Sources

- `.planning/codebase/CONCERNS.md`
- `reports/data_audit.md`
- `docs/guia_refactor_clasificador.md`

---
*Pitfalls research for: academic abstract classification pipeline refactor*
*Researched: 2026-03-24*
