---
phase: 01-canonical-taxonomy-and-corpus-contracts
plan: 01-03
subsystem: taxonomy
tags: [python, pandas, toml, pytest, taxonomy]
requires: [01-01]
provides:
  - canonical Arbor taxonomy contract in repo config
  - explicit legacy-label normalization with direct, alias, and review-required states
  - prepare-side taxonomy inventory report for Seed and Muestras
affects: [phase-02, supervised-labeling, prepare-command]
tech-stack:
  added: [tomllib, pandas]
  patterns: [config-first-taxonomy-contract, explicit-label-normalization, markdown-inventory-report]
key-files:
  created:
    - configs/taxonomy.toml
    - src/abstract_classifier/taxonomy.py
    - reports/taxonomy_inventory.md
  modified:
    - src/abstract_classifier/commands/prepare.py
    - tests/test_taxonomy_contract.py
key-decisions:
  - "Keep the six Arbor classes in fixed TOML order and load them as the project-level label contract."
  - "Map legacy RM and RC labels to canonical Type 2 through approved alias policy while preserving label_original."
  - "Treat blank, No, and unresolved legacy labels as review-required cases instead of silently assigning a canonical class."
patterns-established:
  - "Canonical taxonomy lives in config; normalization logic reads config instead of hard-coding labels inline."
  - "Prepare command emits a Markdown inventory that separates direct mappings, alias mappings, and review-required rows."
requirements-completed: [TAXO-01]
duration: 4min
completed: 2026-04-16
---

# Phase 1 Plan 01-03: Canonical theory taxonomy config and legacy label alias inventory Summary

**Canonical Arbor taxonomy contract, explicit alias normalization, and prepare-side taxonomy inventory report**

## Performance

- **Duration:** 4 min
- **Completed:** 2026-04-16T01:50:18Z
- **Tasks:** 3
- **Files modified:** 5

## Accomplishments

- Added `configs/taxonomy.toml` with the six canonical Arbor theory classes in fixed Type 1 through Type 6 order.
- Implemented `src/abstract_classifier/taxonomy.py` to load the config, preserve `label_original`, assign `label_canonica`, and emit `mapping_status`, `mapping_notes`, and `review_required`.
- Replaced the `prepare` placeholder with a real taxonomy inventory workflow and generated `reports/taxonomy_inventory.md` from `Seed/Seed.xlsx` and `Database/Scopus_database.xlsx::Muestras`.
- Added contract coverage in `tests/test_taxonomy_contract.py` for taxonomy order, direct mappings, approved Type 2 aliases, review-required cases, and the CLI inventory path.

## Task Commits

Each task was committed atomically:

1. **Task 1: Encode the Arbor taxonomy as the canonical label contract** - `a3b95e8` (feat)
2. **Task 2: Implement alias mapping and canonical-label normalization helpers** - `306779e` (feat)
3. **Task 3: Expose a taxonomy inventory/report path for Phase 2 input** - `a6ca385` (feat)

## Files Created/Modified

- `configs/taxonomy.toml` - Defines the fixed canonical Arbor class identifiers and labels.
- `src/abstract_classifier/taxonomy.py` - Loads taxonomy config, normalizes legacy labels, and builds the report inventory from supervised sources.
- `src/abstract_classifier/commands/prepare.py` - Emits the taxonomy inventory Markdown report from the CLI.
- `tests/test_taxonomy_contract.py` - Verifies taxonomy contract loading, normalization policy, and the prepare-side report command.
- `reports/taxonomy_inventory.md` - Current inventory artifact separating direct, alias, and review-required cases.

## Decisions Made

- Used the Arbor article as the fixed semantic source and encoded the canonical taxonomy in TOML rather than notebook logic.
- Preserved `label_original` exactly while normalizing into canonical labels and review fields.
- Treated `Tipo 2 RM` and `Tipo 2 RC` as approved aliases for canonical Type 2 and left `Tipo 6 RF`, `Tipo 4 CM`, `No`, and blanks as non-success review cases.
- Included `Muestras` in the inventory workflow for Phase 2 visibility while keeping `Seed` as the only initial gold source.

## Deviations from Plan

### Execution-specific adjustments

**1. Parallel-wave planning files were left untouched**
- **Reason:** The user explicitly requested that shared planning artifacts such as `.planning/STATE.md`, `.planning/ROADMAP.md`, and `.planning/REQUIREMENTS.md` not be modified in this parallel workspace.
- **Impact:** The summary artifact was created, but shared progress/state files were intentionally not updated here.

## Verification

- `.\.venv\Scripts\python.exe -m pytest tests/test_taxonomy_contract.py -q`
- `.\.venv\Scripts\python.exe -m pytest tests -q`
- `.\.venv\Scripts\python.exe -m abstract_classifier.cli prepare --inventory-output reports/taxonomy_inventory.md`

## Validation Notes

- `pytest` passed for the dedicated taxonomy contract tests and for the full current test suite.
- `ruff`, `mypy`, and `bandit` were not installed in the repo-local environment, so static-analysis validation was limited to the available test suite and command execution checks.

## Next Phase Readiness

- Phase 2 can consume `reports/taxonomy_inventory.md` to separate approved canonical training rows from manual-review rows.
- The taxonomy contract is now versioned and reusable from importable code rather than notebook cells.
- The prepare command has a real supervised-label inventory path that can be extended later into broader canonical table assembly.

## Self-Check: PASSED

- Summary artifact exists.
- Report artifact exists at `reports/taxonomy_inventory.md`.
- Task commits `a3b95e8`, `306779e`, and `a6ca385` exist in git history.

---
*Phase: 01-canonical-taxonomy-and-corpus-contracts*
*Completed: 2026-04-16*
