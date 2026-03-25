# External Integrations

**Analysis Date:** 2026-03-24

## APIs & External Services

**Model Hosting / ML Hub:**
- Hugging Face Hub - Source of all pretrained models referenced by notebook code.
  - SDK/Client: `transformers`, `sentence-transformers`, `setfit`
  - Auth: Not detected in repo; notebooks use public model identifiers without tokens.
  - References:
    - `AbstractsV2.ipynb`: `facebook/bart-large-mnli`, `sentence-transformers/paraphrase-mpnet-base-v2`, `dbmdz/bert-large-cased-finetuned-conll03-english`
    - `old/Christian_Escobar_Abstract_Classification_fix2.ipynb`: `xlm-roberta-base`, `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, `microsoft/deberta-v3-large`

**Notebook Platform / Storage:**
- Google Colab + Google Drive - Used only by the legacy workflow in `old/Christian_Escobar_Abstract_Classification_fix2.ipynb` for mounting notebook storage and persisting outputs under `/content/drive/My Drive/...`.
  - SDK/Client: `google.colab`
  - Auth: Interactive Google account OAuth handled by Colab session, not stored in repo.

**Data Acquisition Source:**
- Google Scholar export snapshot - Represented locally by `googleScholarPeriodAbs.xlsx`.
  - SDK/Client: Not detected in code as an API client.
  - Auth: Not detected.
  - Evidence: Workbook sheet `gschoolar_resultsPeriod_abs`, query table metadata in `xl/connections.xml`, and columns `Title`, `Authors`, `Citations_counts`, `sumj`, `Year`, `Journal`, `Abstract`, `period`, `IsEnglish`, `SearchCriteria`.

## Data Storage

**Databases:**
- None
  - Connection: Not applicable
  - Client: Not applicable

**File Storage:**
- Local filesystem only in the current repo workflow:
  - `googleScholarPeriodAbs.xlsx`
  - `abstracs_cleaned.csv`
  - `seed_labeled.csv`
  - `seed_generated.csv`
  - `abstracts_reclasificados_top15.csv`
  - `abstracts_clasificados_subtemas_aprobados.csv`
  - `abstracts_clasificados_filosóficos.csv`
  - `abstracts_con_metodologia_optimizado.csv`
  - `temas_interactivos.html`
  - `top_15_temas_bar.html`
- Google Drive only in the legacy Colab flow:
  - `/content/drive/My Drive/classified_abstracts.csv`
  - `/content/drive/My Drive/xlm_roberta_optimized`
  - `/content/drive/My Drive/abstracts_with_bertopic_and_classification.csv`

**Caching:**
- Model cache is implicit in Hugging Face/PyTorch tooling, but no explicit cache directory or cache service is configured in repo files.

## Authentication & Identity

**Auth Provider:**
- Google account session via Colab - Only for `old/Christian_Escobar_Abstract_Classification_fix2.ipynb`.
  - Implementation: `drive.mount('/content/drive')` interactive mount.
- No application-level authentication system is present.

## Monitoring & Observability

**Error Tracking:**
- None

**Logs:**
- Notebook print statements only, for example confidence summaries and output file confirmations in `AbstractsV2.ipynb`.

## CI/CD & Deployment

**Hosting:**
- Not applicable; this repository is not deployed as a service.

**CI Pipeline:**
- None detected

## Environment Configuration

**Required env vars:**
- None detected in repository contents.
- The workflows rely on notebook-local paths and runtime package installs instead of environment variables.

**Secrets location:**
- Not detected in repo.
- Legacy Google Drive access is delegated to Colab interactive authentication, not committed secrets.

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- Hugging Face model downloads initiated by notebook calls such as `pipeline(...)`, `SetFitModel.from_pretrained(...)`, `SentenceTransformer(...)`, and `AutoModelForSequenceClassification.from_pretrained(...)`.

## Integration Notes

**Current-state integration boundaries:**
- `AbstractsV2.ipynb` runs as a local, file-based pipeline with no direct cloud storage dependency once input files exist in the repo root.
- `old/Christian_Escobar_Abstract_Classification_fix2.ipynb` is tightly coupled to Google Colab and Google Drive paths, so it is not directly portable without path rewrites.
- `googleScholarPeriodAbs.xlsx` contains workbook-internal query metadata (`Provider=Microsoft.Mashup.OleDb.1;Data Source=$Workbook$;Location=gschoolar_resultsPeriod_abs`) rather than an external API credential or service endpoint, so the repo currently holds a snapshot, not a live ingestion connector.
- No evidence of REST clients, database drivers, secret managers, or message queues was found in the repo.

---

*Integration audit: 2026-03-24*
