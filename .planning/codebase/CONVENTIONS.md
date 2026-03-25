# Coding Conventions

**Analysis Date:** 2026-03-24

## Naming Patterns

**Files:**
- Use notebook-first naming at the repository root for primary workflows: `AbstractsV2.ipynb`.
- Keep legacy or experimental work under `old/`: `old/Christian_Escobar_Abstract_Classification_fix2.ipynb`.
- Export derived datasets as flat CSV files in the repository root using descriptive snake_case names: `abstracs_cleaned.csv`, `abstracts_reclasificados_top15.csv`, `abstracts_con_metodologia_optimizado.csv`.
- Export visual outputs as standalone HTML files in the repository root: `temas_interactivos.html`, `top_15_temas_bar.html`.

**Functions:**
- Use `snake_case` for helper functions defined inside notebooks: `safe_split`, `predict_batch_voting`, `map_fn`, `zs_predict_all`, `classify_batch`, `extract_authors`.
- Keep most functions cell-local and task-specific instead of reusable modules. Future code should preserve `snake_case` if new helpers are added.

**Variables:**
- Use `snake_case` for most dataframe and pipeline variables: `df_raw`, `df_seed`, `df_no_duplicates`, `count_by_year`, `topic_centroids`.
- Use uppercase names for notebook constants and model configuration knobs: `LABELS`, `VERBALIZERS`, `TEMPLATE`, `BATCH_ZS`, `BATCH_DS`, `ALPHA`, `DEVICE`, `MODEL_CKPT`.
- Reuse short dataframe aliases (`df`, `out`, `ds`) across unrelated stages. New code should avoid overloading `df` when a stage boundary matters.

**Types:**
- No typed function signatures, dataclasses, pydantic models, or schema classes are present in `AbstractsV2.ipynb` or `old/Christian_Escobar_Abstract_Classification_fix2.ipynb`.
- Label mappings are represented as plain dictionaries: `id2label`, `label2id`, `topic_labels`, `relevance_scientific`.

## Code Style

**Formatting:**
- No formatter configuration is detected. `.prettierrc`, `black`, `ruff`, `pyproject.toml`, `requirements.txt`, `environment.yml`, `pytest.ini`, `jest.config.*`, and `vitest.config.*` are not present at the repository root.
- Preserve the current notebook style: section banners made of repeated `#` characters, short explanatory comments above blocks, and compact imperative cells.
- Keep line wrapping manual inside notebooks. Existing cells use both short statements and long multi-line calls.

**Linting:**
- No linter configuration is detected.
- Use pandas, Hugging Face, and visualization code directly in notebooks without an enforced lint rule set.

## Import Organization

**Order:**
1. Standard library imports: `os`, `random`, `platform`, `sys`.
2. Numerical and dataframe libraries: `numpy`, `pandas`, `torch`, `nltk`.
3. ML and NLP libraries: `datasets`, `transformers`, `setfit`, `BERTopic`, `sentence_transformers`, `sklearn`.
4. Plotting libraries near the visualization stage: `matplotlib.pyplot`, `seaborn`, `plotly.express`.

**Path Aliases:**
- Not detected. All imports are package imports, and all data paths are relative strings or Colab paths like `./abstracs_cleaned.csv` and `/content/drive/My Drive/...`.

## Error Handling

**Patterns:**
- Handle missing NLTK resources with `try/except LookupError` and download on demand in `AbstractsV2.ipynb`.
- Use `assert` for simple dataframe contract checks instead of formal validation: `assert df["Topic_Label"].isna().sum() == 0` in `AbstractsV2.ipynb`; `assert "Abstract" in df.columns` and `assert "Classification" in df.columns` in `old/Christian_Escobar_Abstract_Classification_fix2.ipynb`.
- Use broad `try/except Exception` only in legacy inference code, returning fallback labels such as `"Error"` or `"Desconocido"` in `old/Christian_Escobar_Abstract_Classification_fix2.ipynb`.
- Prefer lightweight sanitation over strict rejection: `fillna`, `dropna(subset=["Abstract"])`, `astype(str)`, and `pd.to_numeric(..., errors="coerce").fillna(...)`.

## Logging

**Framework:** `print`

**Patterns:**
- Report progress and outputs with inline `print(...)` statements, often with status emojis or human-readable messages.
- Surface simple descriptive metrics in-place: confidence mean, standard deviation, percentiles, grouped counts, and value counts in `AbstractsV2.ipynb`.
- Do not rely on structured logging, log levels, or persisted run metadata.

## Comments

**When to Comment:**
- Add brief stage comments above notebook sections, especially before preprocessing, model setup, batch inference, and export blocks.
- Use numbered comments inside longer cells to describe sequential steps over a dataframe.
- Keep comments bilingual where already present. Existing notebooks mix Spanish prose with English API names.

**JSDoc/TSDoc:**
- Not applicable.
- Use short Python docstrings only for selected helper functions such as `setfit_predict_all`, `zs_predict_all`, and `classify_research_type`.

## Function Design

**Size:**
- Notebook functions are typically small wrappers around library calls, but some orchestration cells combine configuration, model loading, training, inference, and export in one place. New code should keep helpers narrow and isolate stage-specific logic per cell.

**Parameters:**
- Prefer explicit defaults for batch sizes and thresholds inside helper functions: `setfit_predict_all(texts, batch=128)`, `classify_batch(..., batch_size=32)`.
- Pass raw dataframe columns or `Dataset` batches directly rather than defining custom objects.

**Return Values:**
- Return plain Python dicts or lists from batch functions used with `Dataset.map`: `{"Methodology": ..., "Confidence": ...}`, `{"Authors": ...}`.
- Return NumPy arrays for score matrices in scoring helpers.

## Module Design

**Exports:**
- No Python modules or package exports are present. Reuse currently happens by rerunning notebook cells and saving intermediate CSV artifacts.

**Barrel Files:**
- Not applicable.

## Notebook Workflow Conventions

**Execution model:**
- Treat `AbstractsV2.ipynb` as the active workflow and `old/Christian_Escobar_Abstract_Classification_fix2.ipynb` as a legacy reference, not as parallel sources of truth.
- Keep heavy ML stages separate by exported CSV boundaries:
  - `googleScholarPeriodAbs.xlsx` -> `abstracs_cleaned.csv`
  - `abstracs_cleaned.csv` + `seed_generated.csv` -> `classified_articles_setfit.csv`
  - `classified_articles_setfit.csv` -> `abstracts_reclasificados_top15.csv`
  - `abstracts_clasificados_filosóficos.csv` -> `abstracts_con_metodologia_optimizado.csv`

**Dependency management:**
- Current notebooks install dependencies inline with `pip install`, `%pip install`, and `!pip install`.
- Use one installation cell per environment setup block if new notebook work is added, and pin versions when reproducibility matters. Existing cells mix unpinned installs (`pip install seaborn`) with partial pinning (`transformers==4.28.1` in the legacy notebook).
- Avoid adding more uninstall/reinstall churn like `!pip uninstall -y torch torchvision torchaudio` or force reinstalls unless a compatibility issue is documented in the same cell.

**Data handling:**
- Keep labeled seed data in CSV files with explicit columns. Current labeled assets are:
  - `seed_generated.csv` -> `text,label_text,label`
  - `seed_labeled.csv` -> `text,label_text,label`
  - `abstracts_clasificados_subtemas_aprobados.csv` -> reviewed topic labels
- Preserve column-oriented enrichment. Each stage appends columns instead of rewriting schemas from scratch.
- Convert `Year` and `Citations_counts` to numeric and coerce invalid values before downstream analysis.

**Validation expectations for new work:**
- Add explicit schema checks before model stages for required columns and allowed label ranges because current validation is minimal.
- Record data cardinality before and after `dropna` and `drop_duplicates` when modifying preprocessing logic.
- Keep deterministic seeds in any training or randomized clustering stage. Current reproducibility signals are limited to `seed=42` in SetFit training and `random_state=42` in some legacy split and UMAP steps.

## Reproducibility Notes

**Environment coupling:**
- `AbstractsV2.ipynb` metadata indicates a GPU notebook targeting Python `3.11.11` with a kernel named `nlp-gpu`.
- `old/Christian_Escobar_Abstract_Classification_fix2.ipynb` metadata indicates Google Colab with GPU and Python 3.
- File paths alternate between local relative paths and Google Drive paths. New work should pick one execution environment per notebook.

**Observed constraints:**
- No lockfile, environment manifest, or reproducible install script exists.
- Notebook outputs contain embedded widget state and prior execution artifacts, which means execution order matters.
- Several installs are version-unpinned, so reruns can drift over time.

---

*Convention analysis: 2026-03-24*
