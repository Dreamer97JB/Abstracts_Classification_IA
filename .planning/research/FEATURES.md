# Feature Research

**Domain:** academic abstract classification and taxonomy migration pipeline
**Researched:** 2026-03-24
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Reproducible data preparation | Without this, every run becomes manual notebook archaeology | MEDIUM | Must normalize source spreadsheet and seed inputs into managed artifacts |
| Label schema validation | New client labels will arrive and must be trusted before training | MEDIUM | Required to catch missing text, duplicate rows, bad labels, and split leakage |
| Repeatable training and evaluation | A classifier without saved config and metrics cannot be defended to a client | HIGH | Needs saved artifacts and metrics bundles, not just CSV outputs |
| Batch inference with traceability | Delivery needs clean outputs that can be tied back to a model run | MEDIUM | Output columns must explicitly identify label, score, model version, and run id |

### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Config-driven taxonomy changes | Lets the project adapt when the client changes categories | MEDIUM | Reduces refactor cost when taxonomy evolves |
| Low-confidence review outputs | Makes human review targeted instead of manually checking everything | MEDIUM | Valuable once real client labels start arriving |
| Optional analysis modules | Preserves topic/methodology exploration without contaminating the main classifier | MEDIUM | Helps keep delivery scope clean while retaining exploratory value |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Training mainly from synthetic paraphrases | Feels like a fast way to scale examples | Current synthetic seeds are repetitive and can create misleadingly stable training behavior | Use synthetic examples only as auxiliary support around real labels |
| One notebook that does everything | Feels convenient during early exploration | Hides lineage, mixes responsibilities, and is hard to rerun safely | Use scripts/modules plus notebooks as exploratory consumers |
| Forcing topic outputs into the main classifier contract | Feels like getting more value from one pipeline | Topic quality is currently unstable and should not block the main taxonomy classifier | Keep topic/methodology analysis optional and isolated |

## Feature Dependencies

```text
Project entrypoints
    `--requires--> normalized data pipeline
                         `--requires--> label schema validation

Baseline training
    `--requires--> normalized data pipeline
    `--requires--> label schema validation

Batch inference --enhances--> baseline and supervised training

Optional analysis modules --conflicts--> overwriting main classifier score columns
```

### Dependency Notes

- **Training requires normalized data and validated labels:** otherwise model quality cannot be interpreted.
- **Inference depends on training artifacts:** prediction outputs are only useful when tied to a saved model and config.
- **Optional analysis conflicts with shared output contracts:** separate columns and modules are necessary to avoid mixing task meanings.

## MVP Definition

### Launch With (v1)

- [ ] Named scripts and reusable modules for core pipeline stages - this is the structural prerequisite for everything else
- [ ] Data and label contracts with validation - needed before trusting real client labels
- [ ] Reproducible training, evaluation, and batch inference - needed to defend quality and deliver outputs cleanly

### Add After Validation (v1.x)

- [ ] Low-confidence review loop - add once the first real labeled iteration is running
- [ ] Optional topic and methodology modules - add after the main classifier contract is stable

### Future Consideration (v2+)

- [ ] Human relabeling workflow - defer until the first milestone proves the pipeline shape
- [ ] Hierarchical or multi-label taxonomy support - defer until the client taxonomy actually demands it
- [ ] Experiment registry/dashboard - useful later, but not required for the first serious refactor

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Reproducible data preparation | HIGH | MEDIUM | P1 |
| Label schema validation | HIGH | MEDIUM | P1 |
| Repeatable training and evaluation | HIGH | HIGH | P1 |
| Batch inference with traceability | HIGH | MEDIUM | P1 |
| Low-confidence review exports | MEDIUM | MEDIUM | P2 |
| Optional topic/methodology modules | MEDIUM | MEDIUM | P2 |
| Hierarchical taxonomy support | MEDIUM | HIGH | P3 |

## Competitor Feature Analysis

| Feature | Notebook-only POC | Scripted ML pipeline norm | Our Approach |
|---------|-------------------|---------------------------|--------------|
| Data preparation | Manual reruns and intermediate CSVs | Named prepare step with managed outputs | Move to explicit prepare/audit flow |
| Training | Hidden inside cells | CLI/script with saved artifacts and config | Build reproducible train entrypoints |
| Evaluation | Manual inspection | Metrics bundle and reports | Add formal evaluation artifacts |
| Optional analyses | Mixed into the main flow | Separated modules or jobs | Keep them optional and isolated |

## Sources

- `.planning/codebase/ARCHITECTURE.md`
- `.planning/codebase/CONCERNS.md`
- `docs/guia_refactor_clasificador.md`
- Existing repo artifacts and validated WSL environment

---
*Feature research for: academic abstract classification and taxonomy migration pipeline*
*Researched: 2026-03-24*
