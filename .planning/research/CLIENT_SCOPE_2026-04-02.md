# Client Scope Review - 2026-04-02

## Reviewed Inputs

- `Database/Google_Scholar_database.xlsx`
- `Database/Scopus_database.xlsx`
- `Seed/Seed.xlsx`
- `Article/Articulo_Arbor.pdf`
- `requirements.md`

## Evidence Snapshot

### Corpus sizes

- Google Scholar base: 6,769 rows, 6,476 non-null abstracts, 6,401 unique titles
- Scopus base: 8,484 rows, 8,484 non-null abstracts, 8,446 unique titles
- Scopus `Muestras`: 99 labeled rows
- Seed file: 75 rows

### Overlap observations

- Seed titles found in Google: 74 / 74 comparable titles
- Seed titles found in Scopus base: 28 / 74 comparable titles
- `Muestras` titles found in Scopus base: 99 / 99
- Google vs Scopus title overlap: 801

### Metadata richness

Scopus is the strongest operational corpus for downstream analysis:

- `Author Keywords`: 5,703 / 8,484 rows
- `Index Keywords`: 2,491 / 8,484 rows
- `References`: 7,834 / 8,484 rows

This materially improves options for enrichment, correlation analysis, and review workflows.

## Official Theory Taxonomy From The Article

The Arbor article should now be treated as the semantic source of truth for the theory classifier.

### Six official theory types

1. Realismo fuerte
2. Realismo moderado / critico
3. Antirrealismo epistemologico
4. Pragmatismo epistemologico
5. Constructivismo moderado
6. Constructivismo fuerte / relativismo

### Analytical dimensions defined by the article

- Ontologia
- Agencia
- Epistemologia
- Criterios de verdad
- Metodologia

## What Changed In Scope

The active milestone was previously framed as a generic reproducible pipeline that would wait for official client labels later. The newly added files change that assumption.

### The milestone is no longer waiting for the real problem definition

- We now have two real corpora, not just a notebook source file.
- We now have two labeled subsets (`Seed` and `Muestras`) that can seed supervised work.
- We now have a target article that defines the intended theory typology.
- We now have explicit client notes for methodology and analytical outputs.

### The project is now three linked classification problems

1. Theory classification aligned to the article's six-type typology
2. Methodology classification with hierarchical rules
3. Theme and correlation outputs for client analysis

### The corpus strategy changed

- Scopus should be the primary inference corpus because it has abstracts plus keywords and references.
- Google should remain available as a historical and supplementary corpus.
- Seed and `Muestras` should be treated as supervision sources, not as interchangeable production corpora.

## Client Methodology Requirements

The client notes in `requirements.md` define a stricter methodology workflow than the previous roadmap captured.

### Required methodology logic

- If the abstract gives no methodological signal, output `NN`
- If the paper is theoretical only, stop at `no empirico`
- If the paper is empirical, classify it as:
  - `cualitativo`, or
  - `cuantitativo`
- Outliers can exist and should be flagged rather than forced

### Client-facing outputs requested

- Clasificacion
- Temas
- Metodologia
- Correlation-style analysis across labels and topics/authors
- Potential reference or author analyses by label

## Critical Label Inconsistencies

The labeled spreadsheets should not be treated as a clean gold standard yet. They contain signals, but also conflicts that must be normalized before training.

### Confirmed issues

- `Seed` and `Muestras` do not use exactly the same coding convention
- `Seed` contains `Tipo 6 RF`
- `Muestras` contains `Tipo 6 CF - R`
- The article explicitly defines Type 6 as `Constructivismo fuerte / relativismo`
- `Seed` contains both `Tipo 2 RM` and `Tipo 2 RC`
- The article groups that family as `Realismo moderado / critico`
- `Seed` also contains `No` and blank labels that need a policy

### Implication

The first modeling task is not "train classifier immediately." The first modeling task is:

- define the canonical label set
- map legacy spreadsheet labels into it
- surface unresolved rows for manual review

## Recommended Canonical Scope For The Active Milestone

### Primary goal

Deliver a defensible automatic classifier that predicts the article-aligned theory label over the client corpus with traceable data lineage and reviewable outputs.

### Secondary goal

Add methodology classification with the hierarchy:

- `NN`
- `no empirico`
- `empirico -> cualitativo`
- `empirico -> cuantitativo`

### Tertiary goal

Generate client-usable theme and correlation outputs without mixing them into the theory label contract.

## Recommended Dataset Roles

| Dataset | Role |
|---------|------|
| Google Scholar base | Historical corpus, supplemental inference source, overlap reference |
| Scopus base | Primary operational corpus for inference and metadata-driven analysis |
| Seed | Legacy labeled set, likely closer to Google-origin items, requires canonical remapping |
| Scopus `Muestras` | Labeled Scopus subset, strongest direct supervision for the Scopus corpus |
| Arbor article | Semantic source of truth for canonical theory labels |

## Discussion Starters For The Next GSD Step

These are the gray areas worth discussing before planning Phase 1 in detail.

1. Should the canonical model predict the article's six labels directly, or should it preserve legacy spreadsheet labels and map them later?
2. Should `RM` and `RC` remain separate for the client workflow, or be merged under the article's `realismo moderado / critico` family?
3. How should `No`, blank, and low-evidence cases be represented in the canonical training set?
4. Should keywords be allowed as baseline model input from day one, or reserved for a comparative experiment after abstract-only baseline?
5. Are themes expected to be supervised labels or exploratory outputs derived after theory and methodology classification?

## Recommendation

Do not continue with the old "pipeline refactor first, taxonomy later" framing. The new milestone should start with:

1. canonical taxonomy and corpus contracts
2. label harmonization across `Seed` and `Muestras`
3. baseline theory classifier
4. methodology classifier
5. full-corpus inference plus analytical outputs

---
*Created: 2026-04-02 after reviewing new client files added in GitHub diff*
