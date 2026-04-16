---
phase: 02
slug: label-harmonization-and-reviewed-gold-set-assembly
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-16
---

# Phase 02 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest 8.x` |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `.\.venv\Scripts\python.exe -m pytest tests -q` |
| **Full suite command** | `.\.venv\Scripts\python.exe -m pytest tests -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `.\.venv\Scripts\python.exe -m pytest tests -q`
- **After every plan wave:** Run `.\.venv\Scripts\python.exe -m pytest tests -q`
- **Before `$gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 02-01 | 1 | TAXO-02 | unit | `.\.venv\Scripts\python.exe -m pytest tests/test_supervision_config_contract.py -q` | ❌ W0 | ⬜ pending |
| 02-01-02 | 02-01 | 1 | TAXO-02, TAXO-03 | unit | `.\.venv\Scripts\python.exe -m pytest tests/test_theory_mapping_pipeline.py -q` | ❌ W0 | ⬜ pending |
| 02-01-03 | 02-01 | 1 | CORP-03, TAXO-03 | smoke | `.\.venv\Scripts\python.exe -m abstract_classifier.cli prepare --help` | ✅ P1 | ⬜ pending |
| 02-02-01 | 02-02 | 2 | CORP-03 | unit | `.\.venv\Scripts\python.exe -m pytest tests/test_supervised_table_contract.py -q` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02-02 | 2 | CORP-03 | unit | `.\.venv\Scripts\python.exe -m pytest tests/test_gold_split_rules.py -q` | ❌ W0 | ⬜ pending |
| 02-02-03 | 02-02 | 2 | CORP-03, TAXO-03 | smoke | `.\.venv\Scripts\python.exe -m abstract_classifier.cli prepare --candidate-output reports/tmp_candidate.csv --gold-output reports/tmp_gold.csv --split-output reports/tmp_split.csv` | ❌ W0 | ⬜ pending |
| 02-03-01 | 02-03 | 3 | METH-01, METH-02, METH-03 | unit | `.\.venv\Scripts\python.exe -m pytest tests/test_methodology_contract.py -q` | ❌ W0 | ⬜ pending |
| 02-03-02 | 02-03 | 3 | METH-01, METH-02, METH-03 | unit | `.\.venv\Scripts\python.exe -m pytest tests/test_methodology_review_exports.py -q` | ❌ W0 | ⬜ pending |
| 02-03-03 | 02-03 | 3 | METH-01, METH-02, METH-03 | smoke | `.\.venv\Scripts\python.exe -m abstract_classifier.cli prepare --methodology-output reports/tmp_methodology.csv --methodology-review-output reports/tmp_methodology_review.csv` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_supervision_config_contract.py` - supervision policy config coverage
- [ ] `tests/test_theory_mapping_pipeline.py` - config-driven theory mapping and unresolved review cases
- [ ] `tests/test_supervised_table_contract.py` - canonical candidate/gold table contract coverage
- [ ] `tests/test_gold_split_rules.py` - same-article grouping and split leakage coverage
- [ ] `tests/test_methodology_contract.py` - methodology hierarchy and invalid-state validation
- [ ] `tests/test_methodology_review_exports.py` - methodology review queue and nullable output coverage

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Unresolved theory labels stay review-only | TAXO-03 | Requires editorial comparison to client documents | Compare generated theory review outputs against `docs/alcance_cliente/decision_taxonomia_canonica.md` and confirm `Tipo 6 RF`, `Tipo 4 CM`, `No`, and blanks are not auto-included in gold |
| Methodology hierarchy matches client intent | METH-01, METH-02, METH-03 | Client examples are prose, not machine tests | Compare `configs/methodology.toml` and generated review columns against `requirements.md` and `.planning/research/CLIENT_SCOPE_2026-04-02.md` |
| Candidate-source routing matches Phase 2 policy | CORP-03 | Business semantics must remain aligned to planning decisions | Inspect `configs/supervision.toml` and verify only `Seed` and `Muestras` participate in supervised assembly while Google and Scopus Base remain inference-only |

---

## Validation Sign-Off

- [ ] All tasks have `<acceptance_criteria>` with automated or manual verification hooks
- [ ] Sampling continuity: no 3 consecutive tasks without automated verification
- [ ] Wave 0 covers every new config, table, split, and methodology contract introduced in Phase 2
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter once Wave 0 lands

**Approval:** pending
