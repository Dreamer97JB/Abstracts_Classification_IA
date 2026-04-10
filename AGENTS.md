# Agent Instructions

## Package Manager
- Use the repo-local `.venv`
- Bootstrap Windows env: `powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap_env.ps1 -Gpu`
- Install base deps in the active env: `python -m pip install -r requirements\base.txt`

## File-Scoped Commands
| Task | Command |
|------|---------|
| Data audit | `python .\scripts\data_audit.py --output reports/data_audit.md` |
| Host ML stack check | `powershell -ExecutionPolicy Bypass -File .\scripts\check_host_ml_stack.ps1` |
| WSL ROCm bootstrap | `bash ./scripts/bootstrap_wsl_rocm.sh` |
| WSL ROCm verify | `bash ./scripts/verify_wsl_rocm.sh` |

## Commit Attribution
AI commits MUST include:
```text
Co-Authored-By: Codex <noreply@openai.com>
```

## Canonical References
- `.planning/phases/01-canonical-taxonomy-and-corpus-contracts/01-CONTEXT.md` - active Phase 1 source of truth
- `.planning/ROADMAP.md` - phase order and plan inventory
- `.planning/REQUIREMENTS.md` - requirement-to-phase mapping
- `docs/alcance_cliente/decision_taxonomia_canonica.md` - canonical labeling decision
- `docs/alcance_cliente/gold_set_v1_spec.md` - downstream gold-set policy draft; align conflicts to Phase 1 context

## Key Conventions
- Treat `Article/Artículo_Arbor.pdf` as the semantic truth for theory classes
- Treat `Seed/Seed.xlsx` as the only initial gold supervision source
- Keep notebooks exploratory; scripts/modules are the operational source of truth
- Preserve raw sources; corrections happen in cleaned canonical outputs, never in-place on the raw files
- Preserve both `label_original` and `label_canonica`
- Unify Google and Scopus into one canonical article table with one surviving row per article
- Auto-merge only on exact `doi_normalized`, or exact `title_normalized + year`; ambiguous matches go to manual review
- Use richer-row-wins dedup, with Scopus as the tie-breaker
- Do not treat `seed_labeled.csv` or `seed_generated.csv` as canonical gold
