from __future__ import annotations

import json
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .taxonomy import ROOT, resolve_project_path

DEFAULT_CLIENT_REPORTING_CONFIG = Path("configs/client_reporting.toml")
_LIST_SPLIT_RE = re.compile(r"\s*[;|]\s*")
_WHITESPACE_RE = re.compile(r"\s+")
_PARENS_RE = re.compile(r"\([^)]*\)")
_NON_NAME_RE = re.compile(r"[^A-Za-zÀ-ÿ0-9.\- ]+")


@dataclass(frozen=True)
class ClientReportingConfig:
    version: str
    config_path: Path
    top_n_terms: int
    top_n_authors: int
    top_n_references: int
    min_term_frequency: int
    min_reference_token_length: int


@dataclass(frozen=True)
class ClientReportingArtifacts:
    client_results_path: Path
    label_theme_correlations_path: Path
    label_keyword_correlations_path: Path
    author_summary_path: Path
    reference_summary_path: Path
    summary_path: Path
    report_path: Path


def load_client_reporting_config(
    path: str | Path = DEFAULT_CLIENT_REPORTING_CONFIG,
    *,
    root: Path | None = None,
) -> ClientReportingConfig:
    project_root = root or ROOT
    config_path = resolve_project_path(path, root=project_root)
    data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    return ClientReportingConfig(
        version=str(data.get("version", "")),
        config_path=config_path,
        top_n_terms=int(data.get("top_n_terms", 25)),
        top_n_authors=int(data.get("top_n_authors", 25)),
        top_n_references=int(data.get("top_n_references", 25)),
        min_term_frequency=int(data.get("min_term_frequency", 1)),
        min_reference_token_length=int(data.get("min_reference_token_length", 3)),
    )


def build_client_reporting_bundle(
    *,
    input_rows: pd.DataFrame,
    methodology_assignments: pd.DataFrame | None,
    theme_assignments: pd.DataFrame | None,
    theme_summary: pd.DataFrame | None,
    run_dir: Path,
    config: ClientReportingConfig,
    root: Path | None = None,
    context: dict[str, object] | None = None,
) -> ClientReportingArtifacts:
    project_root = root or ROOT
    reporting_rows = (
        methodology_assignments.copy()
        if methodology_assignments is not None
        else input_rows.copy()
    )
    reporting_rows["analysis_run_id"] = str((context or {}).get("analysis_run_id", ""))
    client_results = _build_client_results(
        reporting_rows,
        theme_assignments=theme_assignments,
    )
    label_theme_correlations = _build_label_theme_correlations(theme_assignments)
    label_keyword_correlations = _build_label_keyword_correlations(
        reporting_rows,
        config=config,
    )
    author_summary = _build_author_summary(reporting_rows, config=config)
    reference_summary = _build_reference_summary(reporting_rows, config=config)
    summary = _build_reporting_summary(
        client_results=client_results,
        label_theme_correlations=label_theme_correlations,
        label_keyword_correlations=label_keyword_correlations,
        author_summary=author_summary,
        reference_summary=reference_summary,
        theme_summary=theme_summary,
        context=context or {},
    )

    client_results_path = run_dir / "client_results.csv"
    label_theme_correlations_path = run_dir / "label_theme_correlations.csv"
    label_keyword_correlations_path = run_dir / "label_keyword_correlations.csv"
    author_summary_path = run_dir / "label_author_summary.csv"
    reference_summary_path = run_dir / "label_reference_summary.csv"
    summary_path = run_dir / "client_reporting_summary.json"
    report_path = run_dir / "client_report.md"

    client_results.to_csv(client_results_path, index=False, encoding="utf-8")
    label_theme_correlations.to_csv(
        label_theme_correlations_path,
        index=False,
        encoding="utf-8",
    )
    label_keyword_correlations.to_csv(
        label_keyword_correlations_path,
        index=False,
        encoding="utf-8",
    )
    author_summary.to_csv(author_summary_path, index=False, encoding="utf-8")
    reference_summary.to_csv(reference_summary_path, index=False, encoding="utf-8")
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    report_path.write_text(
        _render_client_report(
            summary=summary,
            client_results=client_results,
            label_theme_correlations=label_theme_correlations,
            label_keyword_correlations=label_keyword_correlations,
            author_summary=author_summary,
            reference_summary=reference_summary,
            run_dir=run_dir,
            project_root=project_root,
            config=config,
        ),
        encoding="utf-8",
    )

    return ClientReportingArtifacts(
        client_results_path=client_results_path,
        label_theme_correlations_path=label_theme_correlations_path,
        label_keyword_correlations_path=label_keyword_correlations_path,
        author_summary_path=author_summary_path,
        reference_summary_path=reference_summary_path,
        summary_path=summary_path,
        report_path=report_path,
    )


def _build_client_results(
    reporting_rows: pd.DataFrame,
    *,
    theme_assignments: pd.DataFrame | None,
) -> pd.DataFrame:
    results = reporting_rows.copy()
    theme_rollup = _roll_up_record_themes(theme_assignments)
    if not theme_rollup.empty:
        results = results.merge(
            theme_rollup,
            on="record_id",
            how="left",
            validate="one_to_one",
        )
    else:
        results["primary_theme"] = ""
        results["theme_labels"] = ""

    theory_id_column, theory_label_column = _resolve_theory_columns(results)
    results["client_theory_id"] = _safe_series(results, theory_id_column)
    results["client_theory_label"] = _safe_series(results, theory_label_column)
    results["client_review_required"] = (
        _bool_series(results, "needs_review")
        | _bool_series(results, "methodology_review_required")
    )
    results["client_review_reason"] = _combine_review_reasons(
        _safe_series(results, "review_reason"),
        _safe_series(results, "methodology_review_reason"),
    )

    selected_columns = [
        "record_id",
        "source_dataset",
        "source_sheet",
        "title",
        "year",
        "doi",
        "authors",
        "journal",
        "client_theory_id",
        "client_theory_label",
        "prediction_score",
        "second_predicted_label_canonica",
        "second_prediction_score",
        "prediction_margin",
        "methodology_label",
        "methodology_subtype",
        "primary_theme",
        "theme_labels",
        "client_review_required",
        "client_review_reason",
        "model_run_id",
        "prediction_run_id",
        "analysis_run_id",
    ]
    existing_columns = [column for column in selected_columns if column in results.columns]
    return results.loc[:, existing_columns].copy()


def _build_label_theme_correlations(theme_assignments: pd.DataFrame | None) -> pd.DataFrame:
    empty = pd.DataFrame(
        columns=["theory_label", "theme_label", "theme_source", "record_count", "assignment_count"]
    )
    if theme_assignments is None or theme_assignments.empty:
        return empty

    theory_label_column = _resolve_theory_label_column(theme_assignments)
    correlations = (
        theme_assignments.groupby(
            [theory_label_column, "theme_label", "theme_source"],
            dropna=False,
        )
        .agg(
            record_count=("record_id", "nunique"),
            assignment_count=("record_id", "size"),
        )
        .reset_index()
        .rename(columns={theory_label_column: "theory_label"})
        .sort_values(
            by=["theory_label", "record_count", "assignment_count", "theme_label"],
            ascending=[True, False, False, True],
        )
        .reset_index(drop=True)
    )
    return correlations


def _build_label_keyword_correlations(
    reporting_rows: pd.DataFrame,
    *,
    config: ClientReportingConfig,
) -> pd.DataFrame:
    theory_label_column = _resolve_theory_label_column(reporting_rows)
    records: list[dict[str, object]] = []
    for row in reporting_rows.to_dict(orient="records"):
        theory_label = str(row.get(theory_label_column, "")).strip()
        if not theory_label:
            continue
        for origin in ("author_keywords", "index_keywords"):
            for keyword in _split_terms(str(row.get(origin, ""))):
                records.append(
                    {
                        "record_id": row["record_id"],
                        "theory_label": theory_label,
                        "keyword": keyword,
                        "keyword_origin": origin,
                    }
                )

    if not records:
        return pd.DataFrame(
            columns=["theory_label", "keyword", "keyword_origin", "record_count"]
        )

    correlations = (
        pd.DataFrame.from_records(records)
        .groupby(["theory_label", "keyword", "keyword_origin"], dropna=False)
        .agg(record_count=("record_id", "nunique"))
        .reset_index()
        .loc[lambda frame: frame["record_count"] >= config.min_term_frequency]
        .sort_values(
            by=["theory_label", "record_count", "keyword"],
            ascending=[True, False, True],
        )
        .reset_index(drop=True)
    )
    return correlations


def _build_author_summary(
    reporting_rows: pd.DataFrame,
    *,
    config: ClientReportingConfig,
) -> pd.DataFrame:
    theory_label_column = _resolve_theory_label_column(reporting_rows)
    records: list[dict[str, object]] = []
    for row in reporting_rows.to_dict(orient="records"):
        theory_label = str(row.get(theory_label_column, "")).strip()
        if not theory_label:
            continue
        for author_name in _split_authors(str(row.get("authors", ""))):
            records.append(
                {
                    "record_id": row["record_id"],
                    "theory_label": theory_label,
                    "author_name": author_name,
                }
            )

    if not records:
        return pd.DataFrame(columns=["theory_label", "author_name", "record_count"])

    summary = (
        pd.DataFrame.from_records(records)
        .groupby(["theory_label", "author_name"], dropna=False)
        .agg(record_count=("record_id", "nunique"))
        .reset_index()
        .sort_values(
            by=["theory_label", "record_count", "author_name"],
            ascending=[True, False, True],
        )
        .groupby("theory_label", group_keys=False)
        .head(config.top_n_authors)
        .reset_index(drop=True)
    )
    return summary


def _build_reference_summary(
    reporting_rows: pd.DataFrame,
    *,
    config: ClientReportingConfig,
) -> pd.DataFrame:
    theory_label_column = _resolve_theory_label_column(reporting_rows)
    records: list[dict[str, object]] = []
    for row in reporting_rows.to_dict(orient="records"):
        theory_label = str(row.get(theory_label_column, "")).strip()
        if not theory_label:
            continue
        for reference_author in _extract_reference_authors(
            str(row.get("references", "")),
            min_token_length=config.min_reference_token_length,
        ):
            records.append(
                {
                    "record_id": row["record_id"],
                    "theory_label": theory_label,
                    "reference_author": reference_author,
                }
            )

    if not records:
        return pd.DataFrame(
            columns=["theory_label", "reference_author", "record_count"]
        )

    summary = (
        pd.DataFrame.from_records(records)
        .groupby(["theory_label", "reference_author"], dropna=False)
        .agg(record_count=("record_id", "nunique"))
        .reset_index()
        .sort_values(
            by=["theory_label", "record_count", "reference_author"],
            ascending=[True, False, True],
        )
        .groupby("theory_label", group_keys=False)
        .head(config.top_n_references)
        .reset_index(drop=True)
    )
    return summary


def _build_reporting_summary(
    *,
    client_results: pd.DataFrame,
    label_theme_correlations: pd.DataFrame,
    label_keyword_correlations: pd.DataFrame,
    author_summary: pd.DataFrame,
    reference_summary: pd.DataFrame,
    theme_summary: pd.DataFrame | None,
    context: dict[str, object],
) -> dict[str, object]:
    label_counts = (
        client_results.get("client_theory_label", pd.Series(dtype=str))
        .fillna("")
        .map(str)
        .str.strip()
        .replace("", "unassigned")
        .value_counts()
        .to_dict()
    )
    review_counts = {
        "client_review_required": int(
            client_results.get("client_review_required", pd.Series(dtype=bool))
            .fillna(False)
            .astype(bool)
            .sum()
        ),
        "client_ready": int(
            len(client_results)
            - client_results.get("client_review_required", pd.Series(dtype=bool))
            .fillna(False)
            .astype(bool)
            .sum()
        ),
    }
    return {
        "context": context,
        "row_count": int(len(client_results)),
        "label_counts": label_counts,
        "review_counts": review_counts,
        "theme_assignment_count": 0 if theme_summary is None else int(theme_summary["assignment_count"].sum()),
        "keyword_correlation_rows": int(len(label_keyword_correlations)),
        "theme_correlation_rows": int(len(label_theme_correlations)),
        "author_summary_rows": int(len(author_summary)),
        "reference_summary_rows": int(len(reference_summary)),
    }


def _render_client_report(
    *,
    summary: dict[str, object],
    client_results: pd.DataFrame,
    label_theme_correlations: pd.DataFrame,
    label_keyword_correlations: pd.DataFrame,
    author_summary: pd.DataFrame,
    reference_summary: pd.DataFrame,
    run_dir: Path,
    project_root: Path,
    config: ClientReportingConfig,
) -> str:
    lines: list[str] = []
    context = summary.get("context", {})
    lines.append("# Client Report")
    lines.append("")
    if context:
        lines.append(f"- Analysis run id: `{context.get('analysis_run_id', '')}`")
        lines.append(f"- Input artifact: `{context.get('input_artifact', '')}`")
        lines.append("")
    lines.append("## Corpus Summary")
    lines.append("")
    lines.append(f"- Rows in client results: `{summary['row_count']}`")
    lines.append(
        f"- Review required rows: `{summary['review_counts']['client_review_required']}`"
    )
    lines.append(f"- Ready rows: `{summary['review_counts']['client_ready']}`")
    lines.append(f"- Theme correlation rows: `{summary['theme_correlation_rows']}`")
    lines.append(f"- Keyword correlation rows: `{summary['keyword_correlation_rows']}`")
    lines.append(f"- Author summary rows: `{summary['author_summary_rows']}`")
    lines.append(f"- Reference summary rows: `{summary['reference_summary_rows']}`")
    lines.append("")

    lines.append("## Theory Distribution")
    lines.append("")
    for label, count in summary.get("label_counts", {}).items():
        lines.append(f"- {label}: `{count}`")
    lines.append("")

    lines.append("## Top Theme Correlations")
    lines.append("")
    lines.extend(
        _render_top_rows(
            label_theme_correlations,
            ["theory_label", "theme_label", "record_count"],
            limit=config.top_n_terms,
        )
    )
    lines.append("")

    lines.append("## Top Keyword Correlations")
    lines.append("")
    lines.extend(
        _render_top_rows(
            label_keyword_correlations,
            ["theory_label", "keyword", "record_count"],
            limit=config.top_n_terms,
        )
    )
    lines.append("")

    lines.append("## Top Authors By Label")
    lines.append("")
    lines.extend(
        _render_top_rows(
            author_summary,
            ["theory_label", "author_name", "record_count"],
            limit=config.top_n_authors,
        )
    )
    lines.append("")

    lines.append("## Top Reference Authors By Label")
    lines.append("")
    lines.extend(
        _render_top_rows(
            reference_summary,
            ["theory_label", "reference_author", "record_count"],
            limit=config.top_n_references,
        )
    )
    lines.append("")

    lines.append("## Artifact Paths")
    lines.append("")
    for file_name in (
        "client_results.csv",
        "label_theme_correlations.csv",
        "label_keyword_correlations.csv",
        "label_author_summary.csv",
        "label_reference_summary.csv",
        "client_reporting_summary.json",
    ):
        lines.append(
            f"- `{_relative_path(run_dir / file_name, project_root)}`"
        )
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _render_top_rows(
    frame: pd.DataFrame,
    columns: list[str],
    *,
    limit: int,
) -> list[str]:
    if frame.empty:
        return ["_None_"]
    rows = frame.loc[:, columns].head(limit).to_dict(orient="records")
    return [
        "- " + ", ".join(f"{column}={row[column]!r}" for column in columns)
        for row in rows
    ]


def _roll_up_record_themes(theme_assignments: pd.DataFrame | None) -> pd.DataFrame:
    if theme_assignments is None or theme_assignments.empty:
        return pd.DataFrame(columns=["record_id", "primary_theme", "theme_labels"])

    theme_rows = (
        theme_assignments.sort_values(by=["record_id", "theme_rank"])
        .groupby("record_id", dropna=False)
        .agg(
            primary_theme=("theme_label", "first"),
            theme_labels=("theme_label", lambda values: " | ".join(dict.fromkeys(values))),
        )
        .reset_index()
    )
    return theme_rows


def _resolve_theory_columns(frame: pd.DataFrame) -> tuple[str, str]:
    theory_id_column = (
        "predicted_canonical_id"
        if "predicted_canonical_id" in frame.columns
        else "canonical_id"
    )
    theory_label_column = _resolve_theory_label_column(frame)
    return theory_id_column, theory_label_column


def _resolve_theory_label_column(frame: pd.DataFrame) -> str:
    return (
        "predicted_label_canonica"
        if "predicted_label_canonica" in frame.columns
        else "label_canonica"
    )


def _safe_series(frame: pd.DataFrame, column: str) -> pd.Series:
    if column in frame.columns:
        return frame[column]
    return pd.Series([""] * len(frame), index=frame.index)


def _bool_series(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series([False] * len(frame), index=frame.index)
    return frame[column].fillna(False).astype(bool)


def _combine_review_reasons(theory_reasons: pd.Series, methodology_reasons: pd.Series) -> pd.Series:
    values: list[str] = []
    for theory_reason, methodology_reason in zip(theory_reasons.tolist(), methodology_reasons.tolist(), strict=False):
        joined = [
            reason
            for reason in (str(theory_reason).strip(), str(methodology_reason).strip())
            if reason and reason.lower() != "nan"
        ]
        values.append(" | ".join(dict.fromkeys(joined)))
    return pd.Series(values, index=theory_reasons.index)


def _split_terms(raw_value: str) -> list[str]:
    text = raw_value.strip()
    if not text:
        return []
    if ";" in text or "|" in text:
        parts = _LIST_SPLIT_RE.split(text)
    elif "," in text:
        parts = [part.strip() for part in text.split(",")]
    else:
        parts = [text]
    return [part for part in (_normalize_term(part) for part in parts) if part]


def _split_authors(raw_value: str) -> list[str]:
    text = _clean_name_fragment(raw_value)
    if not text:
        return []
    if ";" in text:
        parts = [part.strip() for part in text.split(";")]
    elif text.count(",") == 1:
        left, right = [part.strip() for part in text.split(",", 1)]
        if len(left.split()) == 1:
            parts = [text]
        else:
            parts = [left, right]
    elif "," in text:
        parts = [part.strip() for part in text.split(",")]
    else:
        parts = [text]
    return [part for part in (_clean_name_fragment(part) for part in parts) if part]


def _extract_reference_authors(raw_value: str, *, min_token_length: int) -> list[str]:
    text = raw_value.strip()
    if not text:
        return []

    authors: list[str] = []
    for item in raw_value.split(";"):
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


def _normalize_term(value: str) -> str:
    text = _clean_name_fragment(value).lower()
    return text


def _clean_name_fragment(value: str) -> str:
    text = _PARENS_RE.sub("", value)
    text = _NON_NAME_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip(" -.,")
    return text


def _relative_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())
