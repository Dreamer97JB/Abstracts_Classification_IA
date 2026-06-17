"""Build and normalize small client-facing CSV packs for manual theory review."""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd

from .taxonomy import TaxonomyContract, load_taxonomy

ROOT = Path(__file__).resolve().parents[2]
REVIEW_OUTCOME_CANONICAL = "canonical_label"
REVIEW_OUTCOME_OUT_OF_SCOPE = "out_of_scope_theory"
REVIEW_OUTCOME_INSUFFICIENT = "insufficient_theory_signal"
REVIEW_OUTCOME_UNRESOLVED = "unresolved_review"
_OUT_OF_SCOPE_HINTS = (
    "out_of_scope_theory",
    "no aplica",
    "no encaja",
    "fuera de categoria",
    "fuera de taxonomia",
    "sin relacion",
    "sin correlacion",
)
_INSUFFICIENT_HINTS = (
    "insufficient_theory_signal",
    "senal insuficiente",
    "senial insuficiente",
    "señal insuficiente",
    "insuficiente evidencia",
    "evidencia insuficiente",
)
_MODEL_ID_SENTINEL = "prediccion_modelo_id"
_MODEL_LABEL_SENTINEL = "prediccion_modelo_etiqueta"


_NON_NAME_RE = re.compile(r"[^0-9A-Za-zÀ-ÿ' -]+")
_PARENS_RE = re.compile(r"\([^)]*\)")
_WHITESPACE_RE = re.compile(r"\s+")
_WEAK_SIGNAL_RULES: tuple[dict[str, str], ...] = (
    {"rule_id": "title_strong_realism", "signal_source": "title", "cue": "scientific realism", "canonical_id": "tipo_1_realismo_fuerte"},
    {"rule_id": "title_critical_realism", "signal_source": "title", "cue": "critical realism", "canonical_id": "tipo_2_realismo_moderado_critico"},
    {"rule_id": "title_antirealism", "signal_source": "title", "cue": "anti-realism", "canonical_id": "tipo_3_antirrealismo_epistemologico"},
    {"rule_id": "title_pragmatism", "signal_source": "title", "cue": "pragmatism", "canonical_id": "tipo_4_pragmatismo_epistemologico"},
    {"rule_id": "title_social_construction", "signal_source": "title", "cue": "social construction", "canonical_id": "tipo_5_constructivismo_moderado"},
    {"rule_id": "title_constructivism", "signal_source": "title", "cue": "constructivism", "canonical_id": "tipo_5_constructivismo_moderado"},
    {"rule_id": "title_strong_programme", "signal_source": "title", "cue": "strong programme", "canonical_id": "tipo_6_constructivismo_fuerte_relativismo"},
    {"rule_id": "title_relativism", "signal_source": "title", "cue": "relativism", "canonical_id": "tipo_6_constructivismo_fuerte_relativismo"},
    {"rule_id": "keywords_critical_realism", "signal_source": "keywords", "cue": "critical realism", "canonical_id": "tipo_2_realismo_moderado_critico"},
    {"rule_id": "keywords_pragmatism", "signal_source": "keywords", "cue": "pragmatism", "canonical_id": "tipo_4_pragmatismo_epistemologico"},
    {"rule_id": "keywords_social_construction", "signal_source": "keywords", "cue": "social construction", "canonical_id": "tipo_5_constructivismo_moderado"},
    {"rule_id": "keywords_strong_programme", "signal_source": "keywords", "cue": "strong programme", "canonical_id": "tipo_6_constructivismo_fuerte_relativismo"},
    {"rule_id": "reference_popper", "signal_source": "reference_author", "cue": "popper", "canonical_id": "tipo_1_realismo_fuerte"},
    {"rule_id": "reference_bhaskar", "signal_source": "reference_author", "cue": "bhaskar", "canonical_id": "tipo_2_realismo_moderado_critico"},
    {"rule_id": "reference_fraassen", "signal_source": "reference_author", "cue": "fraassen", "canonical_id": "tipo_3_antirrealismo_epistemologico"},
    {"rule_id": "reference_dewey", "signal_source": "reference_author", "cue": "dewey", "canonical_id": "tipo_4_pragmatismo_epistemologico"},
    {"rule_id": "reference_kuhn", "signal_source": "reference_author", "cue": "kuhn", "canonical_id": "tipo_5_constructivismo_moderado"},
    {"rule_id": "reference_latour", "signal_source": "reference_author", "cue": "latour", "canonical_id": "tipo_5_constructivismo_moderado"},
    {"rule_id": "reference_bloor", "signal_source": "reference_author", "cue": "bloor", "canonical_id": "tipo_6_constructivismo_fuerte_relativismo"},
    {"rule_id": "reference_collins", "signal_source": "reference_author", "cue": "collins", "canonical_id": "tipo_6_constructivismo_fuerte_relativismo"},
)


def _md_plain(text: str, max_len: int) -> str:
    """One-line snippet for Markdown tables."""
    s = " ".join(str(text).split())
    if len(s) > max_len:
        s = s[: max_len - 3].rstrip() + "..."
    return s.replace("|", "/")


def _build_instructions_markdown(
    *,
    client_frame: pd.DataFrame,
    taxonomy: TaxonomyContract,
) -> str:
    rows_md = [
        "| Orden | Valor exacto para `canonical_id_corregido` | Valor exacto para `etiqueta_canonica_corregida` |",
        "| ---: | --- | --- |",
    ]
    for c in taxonomy.classes:
        rows_md.append(f"| {c.order} | `{c.identifier}` | {c.label} |")
    table = "\n".join(rows_md)

    first = client_frame.iloc[0]
    rid = str(first["record_id"])
    tit = _md_plain(str(first["titulo"]), 220)
    abst = _md_plain(str(first["resumen_abstract"]), 420)
    pid = str(first["prediccion_modelo_id"]).strip()
    plab = str(first["prediccion_modelo_etiqueta"]).strip()
    sid = str(first.get("segunda_opcion_id", "") or "").strip()
    slab = str(first.get("segunda_opcion_etiqueta", "") or "").strip()
    alt = next((c for c in taxonomy.classes if c.identifier != pid), taxonomy.classes[0])

    second_hint = ""
    if sid:
        second_hint = (
            f"\nEn esta fila la segunda opcion del modelo fue `{sid}` ({slab}). "
            "Solo debe quedar una clase final en las columnas corregidas; esa columna es orientativa.\n"
        )

    return f"""# Instrucciones - revision de etiquetas (teoria canonica)

Este paquete lista filas seleccionadas por el modelo para que usted confirme o corrija la clase de teoria epistemologica segun la taxonomia canonica del proyecto (Arbor / `Article/Articulo_Arbor.pdf`).

## Valores permitidos para clases canonicas

Solo puede usar combinaciones que aparecen en esta tabla:

{table}

## Que debe hacer

1. Abra `client_micro_review.csv` en Excel o LibreOffice.
2. Para cada fila, lea `titulo` y `resumen_abstract` y decida la clase.
3. Si la fila pertenece a una de las seis clases canonicas:
   - rellene `canonical_id_corregido`
   - rellene `etiqueta_canonica_corregida`
   - use `notas_revisor` solo para comentarios opcionales
4. Si coincide con la prediccion del modelo, puede copiar `prediccion_modelo_id` y `prediccion_modelo_etiqueta` o escribir `OK modelo` en `notas_revisor`.
5. Si la fila no encaja en ninguna de las seis clases o no ofrece senal teorica suficiente:
   - deje vacias `canonical_id_corregido` y `etiqueta_canonica_corregida`
   - escriba en `notas_revisor` exactamente uno de estos estados:
     - `out_of_scope_theory`
     - `insufficient_theory_signal`

Use `out_of_scope_theory` cuando considere que el texto no pertenece realmente a la tarea de teoria canonica.
Use `insufficient_theory_signal` cuando el texto podria estar relacionado, pero no ofrece evidencia suficiente para asignar con seguridad una de las seis clases.
{second_hint}
## Reglas

- No cambie `record_id`.
- No anada ni borre filas.
- No invente categorias: use una de las seis clases canonicas o uno de los dos estados especiales descritos arriba.

## Ejemplo practico - primera fila de este CSV

- `record_id`: `{rid}`
- `titulo`: {tit}
- `resumen_abstract` (extracto): {abst}
- Prediccion del modelo: `{pid}` - {plab}

### Si confirma una clase canonica

| Columna | Valor |
| --- | --- |
| `record_id` | `{rid}` |
| `canonical_id_corregido` | `{pid}` |
| `etiqueta_canonica_corregida` | {plab} |
| `notas_revisor` | `OK modelo` |

### Si corrige a otra clase canonica

| Columna | Valor |
| --- | --- |
| `record_id` | `{rid}` |
| `canonical_id_corregido` | `{alt.identifier}` |
| `etiqueta_canonica_corregida` | {alt.label} |
| `notas_revisor` | discrepancia con modelo |

### Si la fila no encaja en la taxonomia

| Columna | Valor |
| --- | --- |
| `record_id` | `{rid}` |
| `canonical_id_corregido` | *(vacio)* |
| `etiqueta_canonica_corregida` | *(vacio)* |
| `notas_revisor` | `out_of_scope_theory` |

Despues de devolver el archivo, el equipo importara sus correcciones con trazabilidad y podra reutilizarlas en futuras iteraciones del clasificador.
"""


def _as_bool(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin(("true", "1", "yes"))


def _normalize_free_text(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().lower()


def _normalize_label_text(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", text).strip().lower()


def _clean_name_fragment(value: str) -> str:
    text = _PARENS_RE.sub("", value)
    text = _NON_NAME_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip(" -.,")
    return text


def _extract_reference_authors(raw_value: object, *, min_token_length: int = 3) -> list[str]:
    text = str(raw_value or "").strip()
    if not text:
        return []

    authors: list[str] = []
    for item in text.split(";"):
        candidate = _clean_name_fragment(item.split(",", 1)[0])
        if not candidate:
            continue
        tokens = candidate.split()
        if len(tokens) > 4:
            continue
        if not any(len(token) >= min_token_length for token in tokens):
            continue
        authors.append(candidate)
    return authors


def _normalize_search_text(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.casefold()
    return re.sub(r"\s+", " ", text).strip()


def build_weak_signal_artifacts(
    frame: pd.DataFrame,
    *,
    taxonomy_config_path: str | Path | None = None,
    root: Path | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Emit conservative weak-signal votes from title, keywords, and references."""
    project_root = root or ROOT
    tax_path = Path(taxonomy_config_path or "configs/taxonomy.toml")
    if not tax_path.is_absolute():
        tax_path = (project_root / tax_path).resolve()
    taxonomy = load_taxonomy(tax_path, root=project_root)
    label_lookup = {item.identifier: item.label for item in taxonomy.classes}

    vote_rows: list[dict[str, Any]] = []
    for row in frame.to_dict(orient="records"):
        record_id = str(row.get("record_id", "") or "").strip()
        if not record_id:
            continue

        title_text = _normalize_search_text(row.get("title", ""))
        keyword_text = _normalize_search_text(
            " ".join(
                part
                for part in (
                    str(row.get("author_keywords", "") or ""),
                    str(row.get("index_keywords", "") or ""),
                )
                if part
            )
        )
        reference_authors = [
            _normalize_search_text(author)
            for author in _extract_reference_authors(row.get("references", ""))
        ]

        for rule in _WEAK_SIGNAL_RULES:
            cue = _normalize_search_text(rule["cue"])
            matched_value = ""
            if rule["signal_source"] == "title" and cue in title_text:
                matched_value = rule["cue"]
            elif rule["signal_source"] == "keywords" and cue in keyword_text:
                matched_value = rule["cue"]
            elif rule["signal_source"] == "reference_author":
                matched_value = next((author for author in reference_authors if cue in author), "")

            if not matched_value:
                continue

            canonical_id = rule["canonical_id"]
            vote_rows.append(
                {
                    "record_id": record_id,
                    "rule_id": rule["rule_id"],
                    "signal_source": rule["signal_source"],
                    "matched_cue": matched_value,
                    "canonical_id": canonical_id,
                    "label_canonica": label_lookup.get(canonical_id, canonical_id),
                    "vote_weight": 1.0,
                }
            )

    vote_frame = pd.DataFrame.from_records(vote_rows)
    if vote_frame.empty:
        return (
            pd.DataFrame(
                {
                    "record_id": frame["record_id"].astype(str),
                    "weak_signal_vote_count": 0,
                    "weak_signal_distinct_rule_count": 0,
                    "weak_signal_majority_canonical_id": "",
                    "weak_signal_majority_label": "",
                    "weak_signal_sources": "",
                    "weak_signal_evidence": "",
                }
            ).drop_duplicates(subset=["record_id"]),
            vote_frame,
        )

    summary_rows: list[dict[str, Any]] = []
    for record_id, grp in vote_frame.groupby("record_id", sort=False):
        counts = grp.groupby("canonical_id").size().sort_values(ascending=False)
        top_count = int(counts.iloc[0])
        top_ids = sorted(counts[counts == top_count].index.tolist())
        majority_id = top_ids[0] if len(top_ids) == 1 else ""
        summary_rows.append(
            {
                "record_id": record_id,
                "weak_signal_vote_count": int(len(grp)),
                "weak_signal_distinct_rule_count": int(grp["rule_id"].nunique()),
                "weak_signal_majority_canonical_id": majority_id,
                "weak_signal_majority_label": label_lookup.get(majority_id, "") if majority_id else "",
                "weak_signal_sources": " | ".join(
                    sorted(set(grp["signal_source"].astype(str).tolist()))
                ),
                "weak_signal_evidence": " | ".join(
                    f"{item['signal_source']}:{item['matched_cue']}->{item['canonical_id']}"
                    for item in grp.to_dict(orient="records")
                ),
            }
        )

    result = frame.loc[:, ["record_id"]].drop_duplicates().merge(
        pd.DataFrame.from_records(summary_rows),
        on="record_id",
        how="left",
    )
    for column in ("weak_signal_vote_count", "weak_signal_distinct_rule_count"):
        result[column] = result[column].fillna(0).astype(int)
    for column in (
        "weak_signal_majority_canonical_id",
        "weak_signal_majority_label",
        "weak_signal_sources",
        "weak_signal_evidence",
    ):
        result[column] = result[column].fillna("").astype(str)
    return result, vote_frame


def _infer_review_outcome(note_value: object) -> str:
    normalized = _normalize_free_text(note_value)
    if not normalized:
        return REVIEW_OUTCOME_UNRESOLVED
    if any(token in normalized for token in _OUT_OF_SCOPE_HINTS):
        return REVIEW_OUTCOME_OUT_OF_SCOPE
    if any(token in normalized for token in _INSUFFICIENT_HINTS):
        return REVIEW_OUTCOME_INSUFFICIENT
    return REVIEW_OUTCOME_UNRESOLVED


def load_client_micro_review_feedback(
    path: str | Path,
    *,
    taxonomy_config_path: str | Path | None = None,
    root: Path | None = None,
) -> pd.DataFrame:
    """Normalize a reviewed client micro-pack into canonical and non-canonical outcomes."""
    project_root = root or ROOT
    review_path = Path(path)
    if not review_path.is_absolute():
        review_path = (project_root / review_path).resolve()

    frame = pd.read_csv(review_path, sep=None, engine="python", encoding="utf-8")
    frame.columns = [str(column).replace("\ufeff", "").strip() for column in frame.columns]
    if "record_id" not in frame.columns:
        raise ValueError("Reviewed client micro-pack must include `record_id`.")

    tax_path = Path(taxonomy_config_path or "configs/taxonomy.toml")
    if not tax_path.is_absolute():
        tax_path = (project_root / tax_path).resolve()
    taxonomy = load_taxonomy(tax_path, root=project_root)
    canonical_lookup = {item.identifier: item.label for item in taxonomy.classes}

    work = frame.copy()
    for column in (
        "canonical_id_corregido",
        "etiqueta_canonica_corregida",
        "notas_revisor",
        "prediccion_modelo_id",
        "prediccion_modelo_etiqueta",
        "segunda_opcion_id",
        "segunda_opcion_etiqueta",
        "review_state_modelo",
        "ood_score_modelo",
    ):
        if column not in work.columns:
            work[column] = ""
        work[column] = work[column].fillna("").map(str).str.strip()

    # Reviewer shortcut support: when the sheet keeps literal placeholders
    # `prediccion_modelo_id` / `prediccion_modelo_etiqueta`, treat them as
    # "confirmed model label" and copy the current model prediction values.
    canonical_sentinel_mask = (
        work["canonical_id_corregido"].str.casefold() == _MODEL_ID_SENTINEL
    )
    label_sentinel_mask = (
        work["etiqueta_canonica_corregida"].str.casefold() == _MODEL_LABEL_SENTINEL
    )
    if canonical_sentinel_mask.any():
        work.loc[canonical_sentinel_mask, "canonical_id_corregido"] = work.loc[
            canonical_sentinel_mask,
            "prediccion_modelo_id",
        ].astype(str)
    if label_sentinel_mask.any():
        work.loc[label_sentinel_mask, "etiqueta_canonica_corregida"] = work.loc[
            label_sentinel_mask,
            "prediccion_modelo_etiqueta",
        ].astype(str)

    work["review_outcome"] = REVIEW_OUTCOME_UNRESOLVED
    work["import_decision"] = "unresolved_review"

    has_canonical = work["canonical_id_corregido"].ne("")
    invalid_ids = sorted(
        set(
            work.loc[
                has_canonical & ~work["canonical_id_corregido"].isin(canonical_lookup),
                "canonical_id_corregido",
            ].tolist()
        )
    )
    if invalid_ids:
        raise ValueError(f"Unknown canonical ids in reviewed client pack: {invalid_ids}")

    work.loc[has_canonical, "review_outcome"] = REVIEW_OUTCOME_CANONICAL
    work.loc[has_canonical, "import_decision"] = "accepted_canonical_label"
    for idx in work.index[has_canonical]:
        cid = str(work.at[idx, "canonical_id_corregido"])
        expected = canonical_lookup[cid]
        provided = str(work.at[idx, "etiqueta_canonica_corregida"]).strip()
        if provided and _normalize_label_text(provided) != _normalize_label_text(expected):
            raise ValueError(
                "Canonical label mismatch in reviewed client pack for "
                f"`{work.at[idx, 'record_id']}`: expected `{expected}`, got `{provided}`."
            )
        work.at[idx, "etiqueta_canonica_corregida"] = expected

    unresolved_mask = ~has_canonical
    work.loc[unresolved_mask, "review_outcome"] = work.loc[unresolved_mask, "notas_revisor"].map(
        _infer_review_outcome
    )
    noncanonical_mask = work["review_outcome"].isin(
        (REVIEW_OUTCOME_OUT_OF_SCOPE, REVIEW_OUTCOME_INSUFFICIENT)
    )
    work.loc[noncanonical_mask, "import_decision"] = "accepted_noncanonical_state"

    selected_columns = [
        "record_id",
        "prediccion_modelo_id",
        "prediccion_modelo_etiqueta",
        "segunda_opcion_id",
        "segunda_opcion_etiqueta",
        "review_state_modelo",
        "ood_score_modelo",
        "canonical_id_corregido",
        "etiqueta_canonica_corregida",
        "notas_revisor",
        "review_outcome",
        "import_decision",
    ]
    result = work.loc[:, selected_columns].copy()
    if result["record_id"].duplicated().any():
        dupes = result.loc[result["record_id"].duplicated(), "record_id"].astype(str).tolist()
        raise ValueError(f"Duplicate record ids in reviewed client pack: {dupes[:5]}")
    return result


def export_client_micro_review_pack(
    *,
    predictions_path: Path,
    output_dir: Path,
    max_rows: int = 50,
    model_run_id: str | None = None,
    trusted_corpus_path: Path | None = None,
    gold_supervision_path: Path | None = None,
    abstract_max_chars: int = 8000,
    taxonomy_config_path: str | Path | None = None,
) -> dict[str, Path]:
    """Write client_micro_review.csv plus instructions and manifest."""
    predictions_path = Path(predictions_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    frame = pd.read_csv(predictions_path, encoding="utf-8")
    if model_run_id:
        frame = frame.loc[frame["model_run_id"].astype(str) == str(model_run_id)].copy()
    if frame.empty:
        raise ValueError(f"No prediction rows after filter (model_run_id={model_run_id!r}).")

    if gold_supervision_path:
        gold = pd.read_csv(Path(gold_supervision_path), encoding="utf-8")
        gold_ids = set(gold["record_id"].astype(str))
        frame = frame.loc[~frame["record_id"].astype(str).isin(gold_ids)].copy()

    if trusted_corpus_path:
        trusted = pd.read_csv(Path(trusted_corpus_path), encoding="utf-8")
        t_ids = set(trusted["record_id"].astype(str))
        frame = frame.loc[frame["record_id"].astype(str).isin(t_ids)].copy()

    work = frame.copy()
    weak_signal_summary, weak_signal_votes = build_weak_signal_artifacts(
        work,
        taxonomy_config_path=taxonomy_config_path,
        root=ROOT,
    )
    work = work.merge(weak_signal_summary, on="record_id", how="left")
    if "predicted_canonical_id" in work.columns:
        work["weak_signal_conflict"] = (
            work["weak_signal_majority_canonical_id"].astype(str).ne("")
            & work["predicted_canonical_id"].astype(str).ne(
                work["weak_signal_majority_canonical_id"].astype(str)
            )
        )
    else:
        work["weak_signal_conflict"] = False
    if "needs_review" in work.columns:
        work = work.loc[_as_bool(work["needs_review"])].copy()
    if work.empty:
        work = frame.copy().merge(weak_signal_summary, on="record_id", how="left")
        if "predicted_canonical_id" in work.columns:
            work["weak_signal_conflict"] = (
                work["weak_signal_majority_canonical_id"].astype(str).ne("")
                & work["predicted_canonical_id"].astype(str).ne(
                    work["weak_signal_majority_canonical_id"].astype(str)
                )
            )
        else:
            work["weak_signal_conflict"] = False

    work["_sort_pri"] = 0
    if "review_taxonomy_conflict" in work.columns:
        work.loc[_as_bool(work["review_taxonomy_conflict"]), "_sort_pri"] = 2
    if "review_low_confidence" in work.columns:
        low_conf_mask = (work["_sort_pri"] < 2) & _as_bool(work["review_low_confidence"])
        work.loc[low_conf_mask, "_sort_pri"] = 1
    work["weak_signal_vote_count"] = pd.to_numeric(
        work.get("weak_signal_vote_count", 0),
        errors="coerce",
    ).fillna(0).astype(int)
    work["ood_outlier_score"] = pd.to_numeric(
        work["ood_outlier_score"]
        if "ood_outlier_score" in work.columns
        else pd.Series(0.0, index=work.index),
        errors="coerce",
    ).fillna(0.0)
    work["review_state"] = (
        work["review_state"]
        if "review_state" in work.columns
        else pd.Series("", index=work.index)
    ).fillna("").astype(str)
    work["title"] = (
        work["title"]
        if "title" in work.columns
        else pd.Series("", index=work.index)
    ).fillna("").astype(str)
    margin = (
        work["prediction_margin"]
        if "prediction_margin" in work.columns
        else pd.Series(0.0, index=work.index)
    )
    work["_margin"] = margin.fillna(0.0).astype(float)

    def _selection_reason(row: pd.Series) -> str:
        reasons: list[str] = []
        if bool(row.get("review_taxonomy_conflict", False)):
            reasons.append("taxonomy_conflict")
        if bool(row.get("weak_signal_conflict", False)):
            reasons.append("weak_signal_conflict")
        review_state_value = str(row.get("review_state", "") or "")
        if review_state_value == "out_of_scope_theory":
            reasons.append("candidate_out_of_scope")
        elif review_state_value == "insufficient_theory_signal":
            reasons.append("insufficient_theory_signal")
        if float(row.get("ood_outlier_score", 0.0) or 0.0) >= 0.75:
            reasons.append("ood_outlier_candidate")
        if bool(row.get("review_low_confidence", False)):
            reasons.append("uncertain_model_case")
        if (
            str(row.get("source_dataset", "")).strip() == "scopus_base"
            and len(str(row.get("title", "")).strip()) >= 40
            and bool(row.get("review_low_confidence", False))
        ):
            reasons.append("title_rich_scopus_uncertain")
        margin_value = float(row.get("_margin", 0.0) or 0.0)
        if 0.02 <= margin_value <= 0.08:
            reasons.append("near_admission_margin")
        if int(row.get("weak_signal_vote_count", 0) or 0) > 0 and not reasons:
            reasons.append("weak_signal_supported_case")
        return " | ".join(reasons) or "generic_review_case"

    def _selection_priority(row: pd.Series) -> int:
        priority = 0
        if bool(row.get("review_taxonomy_conflict", False)):
            priority += 100
        if bool(row.get("weak_signal_conflict", False)):
            priority += 90
        review_state_value = str(row.get("review_state", "") or "")
        if review_state_value == "out_of_scope_theory":
            priority += 80
        elif review_state_value == "insufficient_theory_signal":
            priority += 70
        if float(row.get("ood_outlier_score", 0.0) or 0.0) >= 0.75:
            priority += 60
        if bool(row.get("review_low_confidence", False)):
            priority += 25
        if (
            str(row.get("source_dataset", "")).strip() == "scopus_base"
            and len(str(row.get("title", "")).strip()) >= 40
            and bool(row.get("review_low_confidence", False))
        ):
            priority += 20
        margin_value = float(row.get("_margin", 0.0) or 0.0)
        if 0.02 <= margin_value <= 0.08:
            priority += 15
        priority += min(int(row.get("weak_signal_vote_count", 0) or 0), 5)
        return priority

    work["selection_reason"] = work.apply(_selection_reason, axis=1)
    work["selection_priority"] = work.apply(_selection_priority, axis=1)
    work = work.sort_values(
        by=[
            "selection_priority",
            "_sort_pri",
            "weak_signal_vote_count",
            "ood_outlier_score",
            "_margin",
        ],
        ascending=[False, False, False, False, True],
    )
    work = work.drop_duplicates(subset=["record_id"], keep="first").head(int(max_rows))

    title = work["title"] if "title" in work.columns else pd.Series("", index=work.index)
    abstract = work["abstract"] if "abstract" in work.columns else pd.Series("", index=work.index)
    abs_str = abstract.fillna("").astype(str).str.slice(0, int(abstract_max_chars))

    pred_id = (
        work["predicted_canonical_id"]
        if "predicted_canonical_id" in work.columns
        else pd.Series("", index=work.index)
    )
    pred_lab = (
        work["predicted_label_canonica"]
        if "predicted_label_canonica" in work.columns
        else pd.Series("", index=work.index)
    )
    sec_id = (
        work["second_predicted_canonical_id"]
        if "second_predicted_canonical_id" in work.columns
        else pd.Series("", index=work.index)
    )
    sec_lab = (
        work["second_predicted_label_canonica"]
        if "second_predicted_label_canonica" in work.columns
        else pd.Series("", index=work.index)
    )
    cal = (
        work["calibrated_prediction_score"]
        if "calibrated_prediction_score" in work.columns
        else pd.Series("", index=work.index)
    )
    reason = (
        work["review_reason"]
        if "review_reason" in work.columns
        else pd.Series("", index=work.index)
    )
    review_state = (
        work["review_state"]
        if "review_state" in work.columns
        else pd.Series("", index=work.index)
    )
    ood_score = (
        work["ood_outlier_score"]
        if "ood_outlier_score" in work.columns
        else pd.Series("", index=work.index)
    )
    src = (
        work["source_dataset"]
        if "source_dataset" in work.columns
        else pd.Series("", index=work.index)
    )

    out = pd.DataFrame(
        {
            "record_id": work["record_id"].astype(str),
            "titulo": title.fillna("").astype(str),
            "resumen_abstract": abs_str,
            "fuente": src.fillna("").astype(str),
            "prediccion_modelo_id": pred_id.fillna("").astype(str),
            "prediccion_modelo_etiqueta": pred_lab.fillna("").astype(str),
            "segunda_opcion_id": sec_id.fillna("").astype(str),
            "segunda_opcion_etiqueta": sec_lab.fillna("").astype(str),
            "review_state_modelo": review_state.fillna("").astype(str),
            "ood_score_modelo": ood_score,
            "weak_signal_mayoria_id": work["weak_signal_majority_canonical_id"].fillna("").astype(str),
            "weak_signal_mayoria_etiqueta": work["weak_signal_majority_label"].fillna("").astype(str),
            "weak_signal_conflicto": work["weak_signal_conflict"].astype(bool),
            "weak_signal_evidencia": work["weak_signal_evidence"].fillna("").astype(str),
            "motivo_seleccion_pack": work["selection_reason"].fillna("").astype(str),
            "margen_prediccion": work["_margin"],
            "score_calibrado": cal,
            "motivo_revision": reason.fillna("").astype(str),
            "canonical_id_corregido": "",
            "etiqueta_canonica_corregida": "",
            "notas_revisor": "",
        }
    )

    csv_path = output_dir / "client_micro_review.csv"
    readme_path = output_dir / "INSTRUCCIONES_REVISION_CLIENTE.md"
    meta_path = output_dir / "client_micro_review_manifest.json"
    weak_signal_summary_path = output_dir / "weak_signal_summary.csv"
    weak_signal_votes_path = output_dir / "weak_signal_votes.csv"

    tax_path = Path(taxonomy_config_path or "configs/taxonomy.toml")
    tax_resolved = tax_path.resolve() if tax_path.is_absolute() else (ROOT / tax_path).resolve()
    taxonomy = load_taxonomy(tax_resolved, root=ROOT)
    instructions_md = _build_instructions_markdown(client_frame=out, taxonomy=taxonomy)

    out.to_csv(csv_path, index=False, encoding="utf-8")
    out.loc[
        :,
        [
            "record_id",
            "weak_signal_mayoria_id",
            "weak_signal_mayoria_etiqueta",
            "weak_signal_conflicto",
            "weak_signal_evidencia",
            "motivo_seleccion_pack",
        ],
    ].to_csv(weak_signal_summary_path, index=False, encoding="utf-8")
    weak_signal_votes.to_csv(weak_signal_votes_path, index=False, encoding="utf-8")
    readme_path.write_text(instructions_md, encoding="utf-8")

    meta: dict[str, Any] = {
        "source_predictions": str(predictions_path.resolve()),
        "taxonomy_config": str(tax_resolved),
        "row_count": int(len(out)),
        "max_rows_requested": int(max_rows),
        "selection_strategy": "informative_conflict_first_v1",
        "selection_reason_counts": out["motivo_seleccion_pack"].value_counts().to_dict(),
        "model_run_id_filter": model_run_id,
        "trusted_corpus_filter": str(trusted_corpus_path) if trusted_corpus_path else None,
        "gold_exclusion": str(gold_supervision_path) if gold_supervision_path else None,
        "review_outcome_tokens": [
            REVIEW_OUTCOME_OUT_OF_SCOPE,
            REVIEW_OUTCOME_INSUFFICIENT,
        ],
        "weak_signal_vote_row_count": int(len(weak_signal_votes)),
        "outputs": {
            "csv": csv_path.name,
            "instructions": readme_path.name,
            "weak_signal_summary": weak_signal_summary_path.name,
            "weak_signal_votes": weak_signal_votes_path.name,
        },
    }
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "csv": csv_path,
        "instructions": readme_path,
        "manifest": meta_path,
        "weak_signal_summary": weak_signal_summary_path,
        "weak_signal_votes": weak_signal_votes_path,
    }
