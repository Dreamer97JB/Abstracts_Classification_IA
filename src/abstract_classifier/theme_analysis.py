from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

from .taxonomy import ROOT, resolve_project_path
from .text_variants import load_governed_text_metadata

DEFAULT_THEME_PIPELINE_CONFIG = Path("configs/theme_pipeline.toml")
_KEYWORD_SPLIT_RE = re.compile(r"\s*[;|]\s*")
_WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class ThemeTfidfSettings:
    ngram_min: int
    ngram_max: int
    max_features: int
    min_df: int


@dataclass(frozen=True)
class ThemePipelineConfig:
    version: str
    config_path: Path
    supervision_config_path: Path
    default_output_root: Path
    max_themes_per_record: int
    tfidf: ThemeTfidfSettings


def load_theme_pipeline_config(
    path: str | Path = DEFAULT_THEME_PIPELINE_CONFIG,
    *,
    root: Path | None = None,
) -> ThemePipelineConfig:
    project_root = root or ROOT
    config_path = resolve_project_path(path, root=project_root)
    data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    tfidf_data = data.get("tfidf", {})

    return ThemePipelineConfig(
        version=str(data.get("version", "")),
        config_path=config_path,
        supervision_config_path=resolve_project_path(
            data["supervision_config"],
            root=project_root,
        ),
        default_output_root=resolve_project_path(
            data["default_output_root"],
            root=project_root,
        ),
        max_themes_per_record=int(data.get("max_themes_per_record", 3)),
        tfidf=ThemeTfidfSettings(
            ngram_min=int(tfidf_data.get("ngram_min", 1)),
            ngram_max=int(tfidf_data.get("ngram_max", 2)),
            max_features=int(tfidf_data.get("max_features", 512)),
            min_df=int(tfidf_data.get("min_df", 1)),
        ),
    )


def build_theme_outputs(
    input_rows: pd.DataFrame,
    *,
    config: ThemePipelineConfig,
    text_metadata: pd.DataFrame | None = None,
    root: Path | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    project_root = root or ROOT
    metadata = text_metadata
    if metadata is None:
        metadata = load_governed_text_metadata(
            root=project_root,
            supervision_config_path=config.supervision_config_path,
        )

    base_rows = input_rows.drop(
        columns=[
            column
            for column in (
                "author_keywords",
                "index_keywords",
                "keywords_available",
                "keywords_applied",
                "text_input",
            )
            if column in input_rows.columns
        ],
        errors="ignore",
    )

    merged = base_rows.merge(
        metadata.loc[
            :,
            ["record_id", "author_keywords", "index_keywords", "keywords_available"],
        ],
        on="record_id",
        how="left",
        validate="one_to_one",
    )
    missing_metadata = merged["keywords_available"].isna()
    if missing_metadata.any():
        missing_ids = merged.loc[missing_metadata, "record_id"].tolist()
        raise ValueError(
            f"Missing governed theme metadata for record ids: {missing_ids[:5]}"
        )

    merged["author_keywords"] = merged["author_keywords"].fillna("")
    merged["index_keywords"] = merged["index_keywords"].fillna("")
    merged["keywords_available"] = merged["keywords_available"].astype(bool)
    merged["theme_text"] = (
        merged["title"].fillna("").map(str).str.strip()
        + "\n"
        + merged["abstract"].fillna("").map(str).str.strip()
    ).str.strip()

    fallback_terms = _build_tfidf_fallback_terms(merged, config=config)
    assignment_records: list[dict[str, object]] = []
    context_columns = [
        column
        for column in (
            "source_dataset",
            "source_sheet",
            "title",
            "canonical_id",
            "label_canonica",
            "methodology_label",
            "methodology_subtype",
        )
        if column in merged.columns
    ]

    for row in merged.to_dict(orient="records"):
        record_themes = _extract_record_themes(
            row=row,
            fallback_terms=fallback_terms,
            config=config,
        )
        for rank, theme in enumerate(record_themes, start=1):
            record = {
                "record_id": row["record_id"],
                "theme_rank": rank,
                "theme_label": theme["theme_label"],
                "theme_source": theme["theme_source"],
                "theme_origin": theme["theme_origin"],
                "theme_score": theme["theme_score"],
                "keywords_available": bool(row["keywords_available"]),
            }
            for column in context_columns:
                record[column] = row.get(column, "")
            assignment_records.append(record)

    assignments = pd.DataFrame.from_records(assignment_records)
    if assignments.empty:
        summary = pd.DataFrame(
            columns=["theme_label", "theme_source", "record_count", "assignment_count"]
        )
    else:
        summary = (
            assignments.groupby(["theme_label", "theme_source"], dropna=False)
            .agg(record_count=("record_id", "nunique"), assignment_count=("record_id", "size"))
            .reset_index()
            .sort_values(
                by=["record_count", "assignment_count", "theme_label"],
                ascending=[False, False, True],
            )
            .reset_index(drop=True)
        )
    return assignments, summary


def _build_tfidf_fallback_terms(
    merged: pd.DataFrame,
    *,
    config: ThemePipelineConfig,
) -> dict[str, list[dict[str, object]]]:
    try:
        vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words="english",
            ngram_range=(config.tfidf.ngram_min, config.tfidf.ngram_max),
            max_features=config.tfidf.max_features,
            min_df=config.tfidf.min_df,
        )
        matrix = vectorizer.fit_transform(merged["theme_text"].fillna("").map(str))
    except ValueError:
        return {}

    feature_names = vectorizer.get_feature_names_out()
    fallback_terms: dict[str, list[dict[str, object]]] = {}
    for position, record_id in enumerate(merged["record_id"].tolist()):
        row_vector = matrix.getrow(position)
        if row_vector.nnz == 0:
            fallback_terms[record_id] = []
            continue
        ordered_indices = row_vector.indices[row_vector.data.argsort()[::-1]]
        ordered_scores = sorted(
            zip(ordered_indices, row_vector.data[row_vector.data.argsort()[::-1]]),
            key=lambda item: item[1],
            reverse=True,
        )
        seen: set[str] = set()
        themes: list[dict[str, object]] = []
        for feature_index, score in ordered_scores:
            theme_label = _normalize_theme(feature_names[feature_index])
            if not theme_label or theme_label in seen:
                continue
            seen.add(theme_label)
            themes.append(
                {
                    "theme_label": theme_label,
                    "theme_source": "tfidf",
                    "theme_origin": "title_abstract_tfidf",
                    "theme_score": float(score),
                }
            )
            if len(themes) >= config.max_themes_per_record:
                break
        fallback_terms[record_id] = themes
    return fallback_terms


def _extract_record_themes(
    *,
    row: dict[str, object],
    fallback_terms: dict[str, list[dict[str, object]]],
    config: ThemePipelineConfig,
) -> list[dict[str, object]]:
    seen: set[str] = set()
    record_themes: list[dict[str, object]] = []
    for origin_key in ("author_keywords", "index_keywords"):
        for theme_label in _split_keywords(str(row.get(origin_key, ""))):
            if theme_label in seen:
                continue
            seen.add(theme_label)
            record_themes.append(
                {
                    "theme_label": theme_label,
                    "theme_source": "keyword",
                    "theme_origin": origin_key,
                    "theme_score": 1.0,
                }
            )
            if len(record_themes) >= config.max_themes_per_record:
                return record_themes

    if record_themes:
        return record_themes

    for fallback_theme in fallback_terms.get(str(row["record_id"]), []):
        if fallback_theme["theme_label"] in seen:
            continue
        seen.add(str(fallback_theme["theme_label"]))
        record_themes.append(fallback_theme)
        if len(record_themes) >= config.max_themes_per_record:
            break

    return record_themes


def _split_keywords(raw_keywords: str) -> list[str]:
    stripped = raw_keywords.strip()
    if not stripped:
        return []

    if ";" in stripped or "|" in stripped:
        parts = _KEYWORD_SPLIT_RE.split(stripped)
    elif "," in stripped:
        parts = [part.strip() for part in stripped.split(",")]
    else:
        parts = [stripped]

    normalized = [_normalize_theme(part) for part in parts]
    return [value for value in normalized if value]


def _normalize_theme(value: str) -> str:
    text = value.strip().lower()
    text = re.sub(r"[_/]+", " ", text)
    text = re.sub(r"[^\w\s-]", " ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip(" -")
    if not text or len(text) < 3:
        return ""
    return text
