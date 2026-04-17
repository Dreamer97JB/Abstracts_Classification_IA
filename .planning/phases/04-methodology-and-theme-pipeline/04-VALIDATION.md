---
phase: 04
slug: methodology-and-theme-pipeline
status: passed
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-17
updated: 2026-04-17
---

# Phase 04 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest 8.x` |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `.\.venv\Scripts\python.exe -m pytest tests -q` |
| **Full suite command** | `.\.venv\Scripts\python.exe -m pytest tests -q` |
| **Estimated runtime** | ~60-120 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.\.venv\Scripts\python.exe -m pytest tests -q`
- **After every plan wave:** Run `.\.venv\Scripts\python.exe -m pytest tests -q`
- **Before final verification:** Full suite must be green
- **Max feedback latency:** 2 minutes

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 04-01 | 1 | METH-01, METH-02, METH-03 | unit | `.\.venv\Scripts\python.exe -m pytest tests/test_methodology_pipeline.py -q` | yes | green |
| 04-01-02 | 04-01 | 1 | EVAL-02 | unit | `.\.venv\Scripts\python.exe -m pytest tests/test_methodology_pipeline.py -q` | yes | green |
| 04-01-03 | 04-01 | 1 | METH-01, METH-02, METH-03, EVAL-02 | smoke | `.\.venv\Scripts\python.exe -m abstract_classifier.cli analyze --run-id smoke_phase4 --output-dir reports/tmp_phase4/analyze_smoke --input-artifact reports/phase2_gold_supervision.csv` | yes | green |
| 04-02-01 | 04-02 | 2 | ANLY-01 | unit | `.\.venv\Scripts\python.exe -m pytest tests/test_theme_analysis.py -q` | yes | green |
| 04-02-02 | 04-02 | 2 | ANLY-01 | unit | `.\.venv\Scripts\python.exe -m pytest tests/test_analyze_command.py -q` | yes | green |
| 04-02-03 | 04-02 | 2 | ANLY-01 | smoke | `.\.venv\Scripts\python.exe -m abstract_classifier.cli analyze --run-id smoke_phase4 --output-dir reports/tmp_phase4/analyze_smoke --input-artifact reports/phase2_gold_supervision.csv` | yes | green |

*Status: pending, green, red, flaky*

---

## Wave 0 Requirements

- [x] `tests/test_methodology_pipeline.py` - heuristic methodology hierarchy, conflict handling, and optional evaluation coverage
- [x] `tests/test_theme_analysis.py` - keyword-first themes and TF-IDF fallback coverage
- [x] `tests/test_analyze_command.py` - run-bundle manifest plus separate methodology/theme artifact persistence

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Methodology outputs remain separate from theory outputs | METH-01, ANLY-01 | Contract separation is easier to confirm by inspecting emitted files | Open the Phase 4 run directory and confirm methodology/theme outputs are separate files, not in-place mutations of the input artifact |
| Evaluation is skipped honestly when no reviewed labels are supplied | EVAL-02 | Needs semantic inspection of the run summary | Open the run manifest or methodology summary and confirm evaluation status is `skipped` rather than fake metrics |
| Keyword-first theme extraction falls back only when governed keywords are absent | ANLY-01 | Requires business-context inspection | Compare theme assignments for `muestras` and `seed` rows in the smoke output and confirm keyword-backed rows are not needlessly replaced by TF-IDF themes |

---

## Validation Sign-Off

- [x] All tasks have `<acceptance_criteria>` with automated or manual verification hooks
- [x] Sampling continuity: no 3 consecutive tasks without automated verification
- [x] Wave 0 covers methodology inference, optional evaluation, theme extraction, and CLI run-bundle persistence
- [x] No watch-mode flags
- [x] Feedback latency < 2 minutes
- [x] `nyquist_compliant: true` set in frontmatter once Wave 0 lands

**Approval:** passed
