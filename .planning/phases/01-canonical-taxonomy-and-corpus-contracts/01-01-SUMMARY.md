---
phase: 01-canonical-taxonomy-and-corpus-contracts
plan: 01-01
subsystem: cli
tags: [python, argparse, setuptools, pytest]
requires: []
provides:
  - src-based operational package for abstract classification workflows
  - named CLI entrypoints for audit, prepare, train, evaluate, predict, and analyze
  - shared audit command surface with legacy script compatibility
  - Wave 0 smoke tests for the CLI help surface and audit report generation
affects: [phase-01-02, phase-01-03, ops]
tech-stack:
  added: [setuptools-src-layout, pytest]
  patterns: [thin-cli-router, compatibility-wrapper, subprocess-smoke-tests]
key-files:
  created:
    - src/abstract_classifier/cli.py
    - src/abstract_classifier/commands/audit.py
    - tests/conftest.py
    - tests/test_cli_smoke.py
  modified:
    - pyproject.toml
    - README.md
    - scripts/data_audit.py
key-decisions:
  - "Use a single argparse router under src/abstract_classifier/cli.py and keep the package as the operational source of truth."
  - "Keep scripts/data_audit.py as a thin compatibility wrapper that delegates to the package audit handler."
  - "Expose future workflow commands as non-failing placeholders so analysts can discover the full command surface before later phases implement them."
patterns-established:
  - "Thin CLI parser -> command modules in src/abstract_classifier/commands"
  - "Legacy scripts delegate to package logic instead of duplicating business rules"
requirements-completed: [OPS-01, OPS-02]
duration: 7min
completed: 2026-04-16
---

# Phase 1 Plan 01-01: Package Skeleton, Config Surface, and CLI Entrypoints Summary

**Src-based abstract_classifier CLI with named command routing, shared audit logic, and Wave 0 smoke tests**

## Performance

- **Duration:** 7 min
- **Started:** 2026-04-16T01:28:08Z
- **Completed:** 2026-04-16T01:35:18Z
- **Tasks:** 3
- **Files modified:** 15

## Accomplishments

- Added `src/abstract_classifier/` as the operational package with a top-level `argparse` router for all required commands.
- Moved the existing audit implementation behind `src/abstract_classifier/commands/audit.py` and kept `scripts/data_audit.py` as a compatibility wrapper.
- Added package metadata, CLI smoke tests, and README guidance that points analysts to the package-based workflow instead of notebook execution.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create the package skeleton and command router** - `d013103` (feat)
2. **Task 2: Move the current audit logic behind the package surface** - `c1651f7` (fix)
3. **Task 3: Add Wave 0 test scaffolding and package metadata** - `2c99d32` (chore)

## Files Created/Modified

- `src/abstract_classifier/cli.py` - Registers the top-level command router and dispatches handlers.
- `src/abstract_classifier/commands/audit.py` - Hosts the reusable audit implementation and package command entrypoint.
- `src/abstract_classifier/commands/_placeholder.py` - Provides consistent non-failing placeholder handlers for future commands.
- `scripts/data_audit.py` - Delegates the legacy script entrypoint to the package audit command.
- `pyproject.toml` - Declares the src layout, console script, pytest config, and dev extra for verification.
- `README.md` - Documents the package-based audit workflow and positions notebooks as exploratory only.
- `tests/conftest.py` - Provides shared CLI subprocess fixtures with `src/` on `PYTHONPATH`.
- `tests/test_cli_smoke.py` - Verifies help output and package audit report generation.

## Decisions Made

- Used a single CLI module with subparser registration to keep command discovery explicit and testable.
- Centralized the audit business logic in the package instead of copying it between the CLI and compatibility script.
- Kept placeholder handlers non-fatal so the required command surface exists now without blocking later plan implementations.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added src-layout package discovery during Task 01-01-01**
- **Found during:** Task 1 (Create the package skeleton and command router)
- **Issue:** `python -m abstract_classifier.cli` could not be imported from an editable install without explicit setuptools package discovery for `src/`.
- **Fix:** Added `tool.setuptools` package discovery to `pyproject.toml`.
- **Files modified:** `pyproject.toml`
- **Verification:** `.\.venv\Scripts\python.exe -m pip install -e .`; `.\.venv\Scripts\python.exe -m abstract_classifier.cli --help`
- **Committed in:** `d013103`

**2. [Rule 3 - Blocking] Added pytest dev metadata and installed pytest in the repo-local environment**
- **Found during:** Task 3 (Add Wave 0 test scaffolding and package metadata)
- **Issue:** Wave 0 verification could not run because the repo-local `.venv` did not include `pytest`.
- **Fix:** Declared a `dev` extra with `pytest>=8,<9` in `pyproject.toml` and installed `-e .[dev]` in the repo-local `.venv`.
- **Files modified:** `pyproject.toml`
- **Verification:** `.\.venv\Scripts\python.exe -m pytest tests -q`
- **Committed in:** `2c99d32`

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan:** Both fixes were required to make the new CLI importable and verifiable. No scope creep beyond the plan.

## Issues Encountered

- The existing `README.md` text had encoding noise, so it was rewritten in ASCII-safe wording while preserving the intended guidance.
- A parallel read of the compatibility audit report raced the file write; rerunning the file check serially confirmed the wrapper output.

## User Setup Required

None - no external service configuration required.

## Known Stubs

- `src/abstract_classifier/commands/prepare.py:6` - Intentional placeholder handler until plan 01-02 implements corpus preparation.
- `src/abstract_classifier/commands/train.py:6` - Intentional placeholder handler until Phase 3 implements model training.
- `src/abstract_classifier/commands/evaluate.py:6` - Intentional placeholder handler until Phase 3 adds evaluation flows.
- `src/abstract_classifier/commands/predict.py:6` - Intentional placeholder handler until Phase 5 adds batch inference.
- `src/abstract_classifier/commands/analyze.py:6` - Intentional placeholder handler until Phase 4 adds downstream analysis workflows.

## Next Phase Readiness

- Phase 01-02 can add source manifests and overlap logic directly under the established package and test surface.
- The audit command is already operational and reusable, so future data-governance plans can extend it instead of adding new standalone scripts.
- The remaining command entrypoints are intentionally stubbed and ready to receive real implementations in later plans.

## Self-Check: PASSED

- Summary artifact exists.
- Key created files exist.
- Task commits `d013103`, `c1651f7`, and `2c99d32` exist in git history.

---
*Phase: 01-canonical-taxonomy-and-corpus-contracts*
*Completed: 2026-04-16*
