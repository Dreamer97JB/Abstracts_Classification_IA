from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .taxonomy import ROOT, resolve_project_path

DEFAULT_CORPUS_TRUST_CONFIG = Path("configs/corpus_trust.toml")
TRUST_PROFILE_COLUMNS = [
    "record_id",
    "source_dataset",
    "source_sheet",
    "source_path",
    "source_role",
    "source_system",
    "title",
    "year",
    "doi",
    "doi_normalized",
    "merge_cluster_size",
    "merge_status",
    "keywords_available",
    "abstract_word_count",
    "metadata_support_count",
    "ambiguous_overlap_exposure",
    "missing_title",
    "missing_abstract",
    "abstract_too_thin",
    "missing_year",
    "missing_doi",
    "missing_authors",
    "missing_journal",
    "keywords_missing",
    "large_merge_cluster",
    "metadata_poor_experiment",
    "metadata_poor_production",
    "trust_flag_count",
    "trust_flags",
    "trust_status",
    "include_in_experiment",
    "include_in_production",
    "experiment_exclusion_reason",
    "production_exclusion_reason",
]


@dataclass(frozen=True)
class CorpusTrustRules:
    min_abstract_words: int
    experiment_min_metadata_fields: int
    production_min_metadata_fields: int
    exclude_ambiguous_overlap: bool
    production_requires_year: bool


@dataclass(frozen=True)
class CorpusTrustConfig:
    version: str
    config_path: Path
    phase5_inference_input_path: Path
    phase5_overlap_review_path: Path
    phase5_summary_path: Path
    default_output_root: Path
    rules: CorpusTrustRules


@dataclass(frozen=True)
class CorpusTrustArtifacts:
    run_dir: Path
    manifest_path: Path
    trust_profile_path: Path
    excluded_rows_path: Path
    trusted_experiment_path: Path
    trusted_production_path: Path
    summary_path: Path
    comparison_summary_path: Path


def load_corpus_trust_config(
    path: str | Path = DEFAULT_CORPUS_TRUST_CONFIG,
    *,
    root: Path | None = None,
) -> CorpusTrustConfig:
    project_root = root or ROOT
    config_path = resolve_project_path(path, root=project_root)
    data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    rules_data = data.get("rules", {})

    rules = CorpusTrustRules(
        min_abstract_words=int(rules_data.get("min_abstract_words", 0)),
        experiment_min_metadata_fields=int(
            rules_data.get("experiment_min_metadata_fields", 0)
        ),
        production_min_metadata_fields=int(
            rules_data.get("production_min_metadata_fields", 0)
        ),
        exclude_ambiguous_overlap=bool(
            rules_data.get("exclude_ambiguous_overlap", True)
        ),
        production_requires_year=bool(
            rules_data.get("production_requires_year", True)
        ),
    )
    if rules.min_abstract_words <= 0:
        raise ValueError("Corpus trust min_abstract_words must be positive.")
    if rules.experiment_min_metadata_fields <= 0:
        raise ValueError(
            "Corpus trust experiment_min_metadata_fields must be positive."
        )
    if rules.production_min_metadata_fields < rules.experiment_min_metadata_fields:
        raise ValueError(
            "Corpus trust production_min_metadata_fields must be >= experiment_min_metadata_fields."
        )

    return CorpusTrustConfig(
        version=str(data.get("version", "")),
        config_path=config_path,
        phase5_inference_input_path=resolve_project_path(
            data["phase5_inference_input"],
            root=project_root,
        ),
        phase5_overlap_review_path=resolve_project_path(
            data["phase5_overlap_review"],
            root=project_root,
        ),
        phase5_summary_path=resolve_project_path(
            data["phase5_summary"],
            root=project_root,
        ),
        default_output_root=resolve_project_path(
            data["default_output_root"],
            root=project_root,
        ),
        rules=rules,
    )


def build_corpus_trust_profile(
    corpus_frame: pd.DataFrame,
    overlap_review_frame: pd.DataFrame,
    *,
    config: CorpusTrustConfig,
) -> pd.DataFrame:
    profile = corpus_frame.copy()
    _ensure_default_columns(profile)

    ambiguous_record_ids = _ambiguous_record_ids(overlap_review_frame)

    profile["abstract_word_count"] = profile["abstract"].map(_word_count)
    profile["keywords_available"] = profile.apply(_keywords_available, axis=1)
    profile["metadata_support_count"] = profile.apply(_metadata_support_count, axis=1)
    profile["ambiguous_overlap_exposure"] = profile["record_id"].isin(
        ambiguous_record_ids
    )
    profile["missing_title"] = profile["title"].map(lambda value: not _has_text(value))
    profile["missing_abstract"] = profile["abstract_word_count"] == 0
    profile["abstract_too_thin"] = (
        (profile["abstract_word_count"] > 0)
        & (profile["abstract_word_count"] < config.rules.min_abstract_words)
    )
    profile["missing_year"] = profile["year"].isna()
    profile["missing_doi"] = ~profile.apply(_has_doi, axis=1)
    profile["missing_authors"] = profile["authors"].map(lambda value: not _has_text(value))
    profile["missing_journal"] = profile["journal"].map(lambda value: not _has_text(value))
    profile["keywords_missing"] = ~profile["keywords_available"]
    profile["large_merge_cluster"] = (
        pd.to_numeric(profile["merge_cluster_size"], errors="coerce")
        .fillna(1)
        .astype(int)
        > 1
    )
    profile["metadata_poor_experiment"] = (
        profile["metadata_support_count"] < config.rules.experiment_min_metadata_fields
    )
    profile["metadata_poor_production"] = (
        profile["metadata_support_count"] < config.rules.production_min_metadata_fields
    )

    profile["trust_flags"] = profile.apply(_build_trust_flags, axis=1)
    profile["trust_flag_count"] = profile["trust_flags"].map(
        lambda value: 0 if not value else len(value.split(" | "))
    )
    profile["experiment_exclusion_reason"] = profile.apply(
        lambda row: _join_reasons(_experiment_exclusion_reasons(row, config)),
        axis=1,
    )
    profile["production_exclusion_reason"] = profile.apply(
        lambda row: _join_reasons(_production_exclusion_reasons(row, config)),
        axis=1,
    )
    profile["include_in_experiment"] = profile["experiment_exclusion_reason"].eq("")
    profile["include_in_production"] = profile["production_exclusion_reason"].eq("")
    profile["trust_status"] = profile.apply(_trust_status, axis=1)
    return profile.sort_values(by=["source_dataset", "record_id"]).reset_index(drop=True)


def build_trusted_views(profile: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    trusted_experiment = profile.loc[profile["include_in_experiment"]].reset_index(drop=True)
    trusted_production = profile.loc[profile["include_in_production"]].reset_index(drop=True)
    excluded_rows = profile.loc[
        ~profile["include_in_experiment"] | ~profile["include_in_production"]
    ].reset_index(drop=True)
    return trusted_experiment, trusted_production, excluded_rows


def build_trust_summary(
    profile: pd.DataFrame,
    *,
    overlap_review_frame: pd.DataFrame,
) -> dict[str, object]:
    trusted_experiment, trusted_production, excluded_rows = build_trusted_views(profile)
    return {
        "profile_row_count": int(len(profile)),
        "trusted_experiment_row_count": int(len(trusted_experiment)),
        "trusted_production_row_count": int(len(trusted_production)),
        "excluded_row_count": int(len(excluded_rows)),
        "ambiguous_overlap_row_count": int(profile["ambiguous_overlap_exposure"].sum()),
        "trust_status_counts": _series_counts(profile["trust_status"]),
        "experiment_exclusion_reason_counts": _reason_counts(
            profile["experiment_exclusion_reason"]
        ),
        "production_exclusion_reason_counts": _reason_counts(
            profile["production_exclusion_reason"]
        ),
        "keyword_availability": {
            "row_count": int(len(profile)),
            "available_count": int(profile["keywords_available"].sum()),
            "availability_rate": float(profile["keywords_available"].mean())
            if len(profile)
            else 0.0,
        },
        "source_composition": {
            "baseline": _composition_rows(profile),
            "trusted_experiment": _composition_rows(trusted_experiment),
            "trusted_production": _composition_rows(trusted_production),
        },
        "manual_overlap_review_row_count": int(len(overlap_review_frame)),
    }


def build_phase5_comparison_summary(
    profile: pd.DataFrame,
    *,
    phase5_input_frame: pd.DataFrame,
    phase5_summary: dict[str, object],
) -> dict[str, object]:
    trusted_experiment, trusted_production, _ = build_trusted_views(profile)
    baseline_count = int(len(phase5_input_frame))
    baseline_keyword_rate = _safe_float(
        ((phase5_summary.get("keyword_coverage") or {}).get("keyword_availability_rate")),
        default=0.0,
    )
    return {
        "phase5_baseline": {
            "input_row_count": baseline_count,
            "manual_overlap_review_count": int(
                phase5_summary.get("manual_overlap_review_count", 0)
            ),
            "exact_merge_decision_count": int(
                phase5_summary.get("exact_merge_decision_count", 0)
            ),
            "keyword_availability_rate": baseline_keyword_rate,
            "source_composition": _composition_rows(phase5_input_frame),
        },
        "phase6_trusted_experiment": {
            "row_count": int(len(trusted_experiment)),
            "retention_rate_vs_phase5": _rate(len(trusted_experiment), baseline_count),
            "source_composition": _composition_rows(trusted_experiment),
            "keyword_availability_rate": _rate(
                int(trusted_experiment["keywords_available"].sum()),
                len(trusted_experiment),
            ),
        },
        "phase6_trusted_production": {
            "row_count": int(len(trusted_production)),
            "retention_rate_vs_phase5": _rate(len(trusted_production), baseline_count),
            "source_composition": _composition_rows(trusted_production),
            "keyword_availability_rate": _rate(
                int(trusted_production["keywords_available"].sum()),
                len(trusted_production),
            ),
        },
        "delta_vs_phase5": {
            "trusted_experiment_row_delta": int(len(trusted_experiment) - baseline_count),
            "trusted_production_row_delta": int(len(trusted_production) - baseline_count),
            "ambiguous_overlap_exposed_count": int(
                profile["ambiguous_overlap_exposure"].sum()
            ),
            "experiment_exclusion_reason_counts": _reason_counts(
                profile["experiment_exclusion_reason"]
            ),
            "production_exclusion_reason_counts": _reason_counts(
                profile["production_exclusion_reason"]
            ),
        },
    }


def run_corpus_trust(
    *,
    config: CorpusTrustConfig,
    run_id: str,
    output_dir: str | Path | None = None,
    root: Path | None = None,
) -> CorpusTrustArtifacts:
    project_root = root or ROOT
    phase5_input = pd.read_csv(config.phase5_inference_input_path, encoding="utf-8")
    overlap_review = pd.read_csv(config.phase5_overlap_review_path, encoding="utf-8")
    phase5_summary = json.loads(config.phase5_summary_path.read_text(encoding="utf-8"))

    profile = build_corpus_trust_profile(
        phase5_input,
        overlap_review,
        config=config,
    )
    trusted_experiment, trusted_production, excluded_rows = build_trusted_views(profile)
    trust_summary = build_trust_summary(profile, overlap_review_frame=overlap_review)
    comparison_summary = build_phase5_comparison_summary(
        profile,
        phase5_input_frame=phase5_input,
        phase5_summary=phase5_summary,
    )

    run_dir = _resolve_run_dir(
        config=config,
        run_id=run_id,
        output_dir=output_dir,
        root=project_root,
    )
    run_dir.mkdir(parents=True, exist_ok=True)

    trust_profile_path = run_dir / "trust_profile.csv"
    excluded_rows_path = run_dir / "excluded_rows.csv"
    trusted_experiment_path = run_dir / "trusted_experiment_corpus.csv"
    trusted_production_path = run_dir / "trusted_production_corpus.csv"
    summary_path = run_dir / "trust_summary.json"
    comparison_summary_path = run_dir / "phase5_vs_phase6_comparison.json"
    manifest_path = run_dir / "trust_manifest.json"

    profile.to_csv(trust_profile_path, index=False, encoding="utf-8")
    excluded_rows.to_csv(excluded_rows_path, index=False, encoding="utf-8")
    trusted_experiment.to_csv(trusted_experiment_path, index=False, encoding="utf-8")
    trusted_production.to_csv(trusted_production_path, index=False, encoding="utf-8")
    summary_path.write_text(
        json.dumps(trust_summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    comparison_summary_path.write_text(
        json.dumps(comparison_summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    manifest = {
        "run_id": run_id,
        "config_version": config.version,
        "config_path": _relative_path(config.config_path, project_root),
        "phase5_inputs": {
            "inference_input": _relative_path(
                config.phase5_inference_input_path,
                project_root,
            ),
            "overlap_review": _relative_path(
                config.phase5_overlap_review_path,
                project_root,
            ),
            "summary": _relative_path(config.phase5_summary_path, project_root),
        },
        "artifacts": {
            "trust_profile": trust_profile_path.name,
            "excluded_rows": excluded_rows_path.name,
            "trusted_experiment_corpus": trusted_experiment_path.name,
            "trusted_production_corpus": trusted_production_path.name,
            "trust_summary": summary_path.name,
            "phase5_vs_phase6_comparison": comparison_summary_path.name,
        },
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return CorpusTrustArtifacts(
        run_dir=run_dir,
        manifest_path=manifest_path,
        trust_profile_path=trust_profile_path,
        excluded_rows_path=excluded_rows_path,
        trusted_experiment_path=trusted_experiment_path,
        trusted_production_path=trusted_production_path,
        summary_path=summary_path,
        comparison_summary_path=comparison_summary_path,
    )


def _ensure_default_columns(frame: pd.DataFrame) -> None:
    defaults = {
        "source_sheet": "",
        "source_path": "",
        "source_role": "",
        "source_system": "",
        "authors": "",
        "doi": "",
        "doi_normalized": "",
        "abstract": "",
        "journal": "",
        "author_keywords": "",
        "index_keywords": "",
        "references": "",
        "merge_cluster_size": 1,
        "merge_status": "unique",
    }
    for column, default in defaults.items():
        if column not in frame.columns:
            frame[column] = default


def _ambiguous_record_ids(overlap_review_frame: pd.DataFrame) -> set[str]:
    if overlap_review_frame.empty:
        return set()
    candidate_columns = (
        "left_winner_record_id",
        "right_winner_record_id",
        "left_record_id",
        "right_record_id",
    )
    ambiguous_ids: set[str] = set()
    for column in candidate_columns:
        if column not in overlap_review_frame.columns:
            continue
        values = overlap_review_frame[column].dropna().astype(str)
        ambiguous_ids.update(value for value in values if value.strip())
    return ambiguous_ids


def _word_count(value: object) -> int:
    text = str(value or "").strip()
    if not text:
        return 0
    return len(text.split())


def _has_text(value: object) -> bool:
    if value is None:
        return False
    try:
        if pd.isna(value):
            return False
    except TypeError:
        pass
    return bool(str(value).strip())


def _has_doi(row: pd.Series) -> bool:
    return _has_text(row.get("doi_normalized")) or _has_text(row.get("doi"))


def _keywords_available(row: pd.Series) -> bool:
    return _has_text(row.get("author_keywords")) or _has_text(row.get("index_keywords"))


def _metadata_support_count(row: pd.Series) -> int:
    return sum(
        [
            _has_text(row.get("authors")),
            _has_doi(row),
            _has_text(row.get("journal")),
            _has_text(row.get("references")),
            bool(row.get("keywords_available", False)),
            not pd.isna(row.get("year")),
        ]
    )


def _build_trust_flags(row: pd.Series) -> str:
    flags: list[str] = []
    if bool(row["missing_title"]):
        flags.append("missing_title")
    if bool(row["missing_abstract"]):
        flags.append("missing_abstract")
    if bool(row["abstract_too_thin"]):
        flags.append("abstract_too_thin")
    if bool(row["ambiguous_overlap_exposure"]):
        flags.append("ambiguous_overlap_exposure")
    if bool(row["metadata_poor_experiment"]):
        flags.append("metadata_poor_experiment")
    if bool(row["metadata_poor_production"]):
        flags.append("metadata_poor_production")
    if bool(row["missing_year"]):
        flags.append("missing_year")
    if bool(row["missing_doi"]):
        flags.append("missing_doi")
    if bool(row["missing_authors"]):
        flags.append("missing_authors")
    if bool(row["missing_journal"]):
        flags.append("missing_journal")
    if bool(row["keywords_missing"]):
        flags.append("keywords_missing")
    if bool(row["large_merge_cluster"]):
        flags.append("large_merge_cluster")
    return _join_reasons(flags)


def _experiment_exclusion_reasons(
    row: pd.Series,
    config: CorpusTrustConfig,
) -> list[str]:
    reasons: list[str] = []
    if bool(row["missing_title"]):
        reasons.append("missing_title")
    if bool(row["missing_abstract"]):
        reasons.append("missing_abstract")
    if bool(row["abstract_too_thin"]):
        reasons.append("abstract_too_thin")
    if config.rules.exclude_ambiguous_overlap and bool(row["ambiguous_overlap_exposure"]):
        reasons.append("ambiguous_overlap_exposure")
    if bool(row["metadata_poor_experiment"]):
        reasons.append("metadata_poor_experiment")
    return reasons


def _production_exclusion_reasons(
    row: pd.Series,
    config: CorpusTrustConfig,
) -> list[str]:
    reasons = list(_experiment_exclusion_reasons(row, config))
    if config.rules.production_requires_year and bool(row["missing_year"]):
        reasons.append("missing_year")
    if bool(row["metadata_poor_production"]):
        reasons.append("metadata_poor_production")
    return reasons


def _join_reasons(reasons: list[str]) -> str:
    deduped = list(dict.fromkeys(reason for reason in reasons if reason))
    return " | ".join(deduped)


def _trust_status(row: pd.Series) -> str:
    if not bool(row["include_in_experiment"]):
        return "excluded"
    if not bool(row["include_in_production"]):
        return "review"
    if bool(row["keywords_missing"]) or bool(row["missing_doi"]) or bool(row["large_merge_cluster"]):
        return "review"
    return "trusted"


def _reason_counts(series: pd.Series) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in series.fillna("").astype(str):
        if not value.strip():
            continue
        for reason in value.split(" | "):
            counts[reason] = counts.get(reason, 0) + 1
    return dict(sorted(counts.items()))


def _series_counts(series: pd.Series) -> dict[str, int]:
    counts = series.value_counts(dropna=False).to_dict()
    return {str(key): int(value) for key, value in sorted(counts.items())}


def _composition_rows(frame: pd.DataFrame) -> list[dict[str, object]]:
    if frame.empty or "source_dataset" not in frame.columns:
        return []
    composition_frame = frame.copy()
    if "keywords_available" not in composition_frame.columns:
        composition_frame["keywords_available"] = composition_frame.apply(
            _keywords_available,
            axis=1,
        )
    grouped = (
        composition_frame.groupby("source_dataset", dropna=False)
        .agg(
            row_count=("record_id", "size"),
            keyword_rows_available=("keywords_available", "sum"),
        )
        .reset_index()
        .sort_values(by=["source_dataset"])
        .reset_index(drop=True)
    )
    records: list[dict[str, object]] = []
    for row in grouped.to_dict(orient="records"):
        row_count = int(row["row_count"])
        keyword_rows = int(row["keyword_rows_available"])
        records.append(
            {
                "source_dataset": str(row["source_dataset"]),
                "row_count": row_count,
                "keyword_rows_available": keyword_rows,
                "keyword_availability_rate": _rate(keyword_rows, row_count),
            }
        )
    return records


def _rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return float(numerator / denominator)


def _safe_float(value: object, *, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _resolve_run_dir(
    *,
    config: CorpusTrustConfig,
    run_id: str,
    output_dir: str | Path | None,
    root: Path,
) -> Path:
    if output_dir is not None:
        candidate = Path(output_dir)
        if not candidate.is_absolute():
            candidate = root / candidate
        return candidate.resolve()
    return (config.default_output_root / run_id).resolve()


def _relative_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())
