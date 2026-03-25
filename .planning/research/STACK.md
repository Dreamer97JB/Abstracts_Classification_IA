# Stack Research

**Domain:** academic abstract classification and notebook-to-pipeline ML refactor
**Researched:** 2026-03-24
**Confidence:** HIGH

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.12 in WSL / 3.11 in Windows support | Primary language for data prep, training, evaluation, and inference | Matches the validated ROCm path in WSL while keeping a stable CPU support path on Windows |
| PyTorch ROCm | 2.9.1 + ROCm 7.2 | GPU-backed training runtime in WSL | Already validated locally against AMD Radeon RX 9070 and fits the future supervised training path |
| Pandas | 2.2.3 | Tabular data loading and transformation | The current repo is CSV/XLSX heavy and pandas remains the simplest bridge from notebook work to scripts |
| scikit-learn | 1.6.1 | Splits, metrics, baseline utilities, preprocessing helpers | Required for reproducible evaluation and baseline model utilities |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| transformers | 4.51.3 | Zero-shot models and future supervised transformer training | Use for baseline zero-shot and encoder-based supervised paths |
| sentence-transformers | 4.1.0 | Embedding-based modeling | Use for SetFit and optional similarity-based analysis |
| setfit | 1.1.3 | Few-shot baseline classifier | Use when labeled data is still limited but real examples exist |
| bertopic | 0.17.4 | Optional topic modeling | Use only after the main classifier path is stable and separated |
| hdbscan / umap-learn | 0.8.41 / 0.5.11 | Topic clustering dependencies | Use only in the optional analysis module |
| openpyxl | 3.1.5 | XLSX ingestion | Needed for the original source spreadsheet |
| pyyaml | 6.0.3 | Human-readable config files | Use for taxonomy, split, and run configs |
| jupyterlab / ipykernel | 4.5.6 / 6.31.0 | Exploratory notebook support | Use as a consumer of scripted outputs, not as the source of truth |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| WSL2 + Ubuntu 24.04 | Primary ML execution environment | Preferred path for GPU training on this machine |
| bash scripts in `scripts/` | Bootstrap and verification | Keep environment setup reproducible and inspectable |
| Markdown reports in `reports/` and `.planning/` | Audit and planning traceability | Prefer plain files over hidden notebook state |

## Installation

```bash
# WSL ROCm environment
bash scripts/bootstrap_wsl_rocm.sh

# Health check
bash scripts/verify_wsl_rocm.sh
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| WSL ROCm training | Windows-only training | Only for light CPU-side audits or when GPU training is not required |
| Scripted pipeline + notebooks for exploration | Notebook-only orchestration | Only during very early ad hoc exploration, not for milestone delivery |
| YAML/config-driven label schema | Hard-coded labels in notebook cells | Only for quick experiments that will not be reused |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Installing packages inside operational notebook runs | Breaks reproducibility and changes runtime behavior mid-experiment | Versioned requirements and bootstrap scripts |
| Treating synthetic seeds as primary supervision | Current synthetic seed diversity is too weak and too repetitive | Real client labels plus explicit validation |
| Reusing one shared `Confidence` field across tasks | Blurs meaning between stance, methodology, and topic confidence | Explicit task-specific score columns |

## Stack Patterns by Variant

**If the task is data audit or schema validation:**
- Use CPU-safe scripts first
- Because these steps should not depend on GPU availability

**If the task is training or large-batch embeddings:**
- Use WSL ROCm environment
- Because the GPU path is validated there and not in the Windows environment

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| Python 3.12 | PyTorch 2.9.1 ROCm 7.2 wheels | This is the validated WSL path used on this machine |
| transformers 4.51.3 | sentence-transformers 4.1.0 | Already installed together in the validated environment |
| bertopic 0.17.4 | hdbscan 0.8.41 / umap-learn 0.5.11 | Validated in the WSL environment |

## Sources

- Local validated environment in WSL - versions and GPU path confirmed on 2026-03-24
- `docs/guia_amd_wsl_rocm.md` - repo-specific AMD/WSL guidance
- `.planning/codebase/ARCHITECTURE.md` - current repo architecture and execution constraints
- `.planning/codebase/CONCERNS.md` - known fragility and dependency risks

---
*Stack research for: academic abstract classification and notebook-to-pipeline ML refactor*
*Researched: 2026-03-24*
