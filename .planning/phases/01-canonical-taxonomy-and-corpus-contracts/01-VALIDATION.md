---
phase: 01
slug: canonical-taxonomy-and-corpus-contracts
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-03
---

# Phase 01 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest 8.x` |
| **Config file** | `pyproject.toml` (Wave 0 adds pytest options if missing) |
| **Quick run command** | `python -m pytest tests -q` |
| **Full suite command** | `python -m pytest tests -q` |
| **Estimated runtime** | ~20 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests -q`
- **After every plan wave:** Run `python -m pytest tests -q`
- **Before `$gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | OPS-01 | smoke | `python -m abstract_classifier.cli --help` | ❌ W0 | ⬜ pending |
| 01-01-02 | 01 | 1 | OPS-02 | unit | `python -m pytest tests/test_cli_smoke.py -q` | ❌ W0 | ⬜ pending |
| 01-02-01 | 02 | 2 | CORP-01 | unit | `python -m pytest tests/test_source_manifest_contract.py -q` | ❌ W0 | ⬜ pending |
| 01-02-02 | 02 | 2 | CORP-02 | unit | `python -m pytest tests/test_overlap_rules.py -q` | ❌ W0 | ⬜ pending |
| 01-03-01 | 03 | 2 | TAXO-01 | unit | `python -m pytest tests/test_taxonomy_contract.py -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/conftest.py` - shared fixtures for workbook rows and config loading
- [ ] `tests/test_cli_smoke.py` - CLI entrypoint smoke tests
- [ ] `tests/test_source_manifest_contract.py` - source manifest schema coverage
- [ ] `tests/test_overlap_rules.py` - DOI/title-year overlap rules
- [ ] `tests/test_taxonomy_contract.py` - canonical taxonomy and alias mapping checks
- [ ] `pytest` installed in the repo-local environment

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Canonical class wording and ordering match the Arbor article | TAXO-01 | Semantic truth comes from a PDF and needs editorial confirmation | Open `Article/Artículo_Arbor.pdf`, inspect the taxonomy table, and confirm all six labels and order in `configs/taxonomy.toml` |
| Source roles match the client decisions (`Seed` gold, `Muestras` auxiliary, Google/Scopus corpus) | CORP-01 | Business semantics are policy-level, not only structural | Inspect `configs/sources.toml` and compare roles against `01-CONTEXT.md` decisions D-04 through D-06 |

---

## Validation Sign-Off

- [ ] All tasks have `<acceptance_criteria>` with automated or manual verification hooks
- [ ] Sampling continuity: no 3 consecutive tasks without automated verification
- [ ] Wave 0 covers all missing test references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter once Wave 0 lands

**Approval:** pending
