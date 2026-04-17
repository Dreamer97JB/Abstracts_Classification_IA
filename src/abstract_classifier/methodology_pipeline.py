from __future__ import annotations

import json
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score

from .methodology import (
    MethodologyAssignment,
    MethodologyContract,
    load_methodology_contract,
    validate_methodology_assignment,
)
from .taxonomy import ROOT, resolve_project_path
from .text_variants import (
    build_text_variant_frame,
    load_governed_text_metadata,
    validate_text_variant,
)

DEFAULT_METHODOLOGY_BASELINE_CONFIG = Path("configs/methodology_baseline.toml")
_REVIEW_REASON_SKIPPED = "skipped"
_SIGNAL_SEPARATOR = " | "


@dataclass(frozen=True)
class MethodologyHeuristicSettings:
    signal_margin: int


@dataclass(frozen=True)
class MethodologyCueSettings:
    non_empirical: tuple[str, ...]
    empirical: tuple[str, ...]
    qualitative: tuple[str, ...]
    quantitative: tuple[str, ...]


@dataclass(frozen=True)
class MethodologyBaselineConfig:
    version: str
    config_path: Path
    methodology_contract_path: Path
    supervision_config_path: Path
    default_input_artifact_path: Path
    default_output_root: Path
    default_text_variant: str
    heuristics: MethodologyHeuristicSettings
    cues: MethodologyCueSettings


@dataclass(frozen=True)
class MethodologyRunArtifacts:
    assignments_path: Path
    review_queue_path: Path
    summary_path: Path
    metrics_paths: dict[str, Path]


def load_methodology_baseline_config(
    path: str | Path = DEFAULT_METHODOLOGY_BASELINE_CONFIG,
    *,
    root: Path | None = None,
) -> MethodologyBaselineConfig:
    project_root = root or ROOT
    config_path = resolve_project_path(path, root=project_root)
    data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    heuristic_data = data.get("heuristics", {})
    cue_data = data.get("cues", {})

    return MethodologyBaselineConfig(
        version=str(data.get("version", "")),
        config_path=config_path,
        methodology_contract_path=resolve_project_path(
            data["methodology_contract"],
            root=project_root,
        ),
        supervision_config_path=resolve_project_path(
            data["supervision_config"],
            root=project_root,
        ),
        default_input_artifact_path=resolve_project_path(
            data["default_input_artifact"],
            root=project_root,
        ),
        default_output_root=resolve_project_path(
            data["default_output_root"],
            root=project_root,
        ),
        default_text_variant=validate_text_variant(str(data["default_text_variant"])),
        heuristics=MethodologyHeuristicSettings(
            signal_margin=int(heuristic_data.get("signal_margin", 1))
        ),
        cues=MethodologyCueSettings(
            non_empirical=_normalize_cues(cue_data.get("non_empirical", [])),
            empirical=_normalize_cues(cue_data.get("empirical", [])),
            qualitative=_normalize_cues(cue_data.get("qualitative", [])),
            quantitative=_normalize_cues(cue_data.get("quantitative", [])),
        ),
    )


def load_analysis_input_rows(
    input_artifact: str | Path,
    *,
    root: Path | None = None,
) -> pd.DataFrame:
    project_root = root or ROOT
    input_path = resolve_project_path(input_artifact, root=project_root)
    frame = pd.read_csv(input_path)
    required_columns = {"record_id", "title", "abstract"}
    missing_columns = sorted(required_columns - set(frame.columns))
    if missing_columns:
        raise ValueError(
            f"Input artifact is missing required columns: {missing_columns}"
        )
    return frame


def build_methodology_assignments(
    input_rows: pd.DataFrame,
    *,
    config: MethodologyBaselineConfig,
    contract: MethodologyContract | None = None,
    text_variant: str | None = None,
    text_metadata: pd.DataFrame | None = None,
    root: Path | None = None,
) -> pd.DataFrame:
    project_root = root or ROOT
    methodology_contract = contract or load_methodology_contract(
        config.methodology_contract_path,
        root=project_root,
    )
    effective_variant = validate_text_variant(text_variant or config.default_text_variant)
    governed_metadata = text_metadata
    if governed_metadata is None:
        governed_metadata = load_governed_text_metadata(
            root=project_root,
            supervision_config_path=config.supervision_config_path,
        )

    variant_rows = build_text_variant_frame(
        input_rows,
        text_variant=effective_variant,
        text_metadata=governed_metadata,
    )

    records: list[dict[str, object]] = []
    for row in variant_rows.to_dict(orient="records"):
        inference = infer_methodology_assignment(
            row=row,
            config=config,
            contract=methodology_contract,
        )
        record = dict(row)
        record.update(inference.assignment.as_record())
        record["methodology_text_variant"] = effective_variant
        record["methodology_empirical_score"] = inference.empirical_score
        record["methodology_non_empirical_score"] = inference.non_empirical_score
        record["methodology_qualitative_score"] = inference.qualitative_score
        record["methodology_quantitative_score"] = inference.quantitative_score
        record["methodology_signal_terms"] = inference.signal_terms
        records.append(record)

    return pd.DataFrame.from_records(records)


@dataclass(frozen=True)
class MethodologyInference:
    assignment: MethodologyAssignment
    empirical_score: int
    non_empirical_score: int
    qualitative_score: int
    quantitative_score: int
    signal_terms: str


def infer_methodology_assignment(
    *,
    row: dict[str, object],
    config: MethodologyBaselineConfig,
    contract: MethodologyContract,
) -> MethodologyInference:
    analysis_text = _compose_analysis_text(row)
    non_empirical_matches = _collect_matches(analysis_text, config.cues.non_empirical)
    empirical_matches = _collect_matches(analysis_text, config.cues.empirical)
    qualitative_matches = _collect_matches(analysis_text, config.cues.qualitative)
    quantitative_matches = _collect_matches(analysis_text, config.cues.quantitative)

    empirical_score = len(empirical_matches) + len(qualitative_matches) + len(
        quantitative_matches
    )
    non_empirical_score = len(non_empirical_matches)
    qualitative_score = len(qualitative_matches)
    quantitative_score = len(quantitative_matches)

    if empirical_score == 0 and non_empirical_score == 0:
        assignment = validate_methodology_assignment(
            methodology_label="NN",
            methodology_branch="NN",
            contract=contract,
        )
    elif empirical_score == 0:
        assignment = validate_methodology_assignment(
            methodology_label="no_empirico",
            methodology_branch="no_empirico",
            contract=contract,
        )
    elif non_empirical_score == 0:
        assignment = _resolve_empirical_assignment(
            qualitative_score=qualitative_score,
            quantitative_score=quantitative_score,
            config=config,
            contract=contract,
        )
    elif empirical_score >= non_empirical_score + config.heuristics.signal_margin:
        assignment = _resolve_empirical_assignment(
            qualitative_score=qualitative_score,
            quantitative_score=quantitative_score,
            config=config,
            contract=contract,
        )
    elif non_empirical_score >= empirical_score + config.heuristics.signal_margin:
        assignment = validate_methodology_assignment(
            methodology_label="no_empirico",
            methodology_branch="no_empirico",
            contract=contract,
        )
    else:
        assignment = validate_methodology_assignment(
            methodology_label=None,
            methodology_branch=None,
            methodology_review_required=True,
            methodology_review_reason=contract.review_reasons["conflicting_cues"],
            contract=contract,
        )

    signal_terms = _SIGNAL_SEPARATOR.join(
        sorted(
            set(
                (*non_empirical_matches, *empirical_matches, *qualitative_matches, *quantitative_matches)
            )
        )
    )
    return MethodologyInference(
        assignment=assignment,
        empirical_score=empirical_score,
        non_empirical_score=non_empirical_score,
        qualitative_score=qualitative_score,
        quantitative_score=quantitative_score,
        signal_terms=signal_terms,
    )


def _resolve_empirical_assignment(
    *,
    qualitative_score: int,
    quantitative_score: int,
    config: MethodologyBaselineConfig,
    contract: MethodologyContract,
) -> MethodologyAssignment:
    if qualitative_score == 0 and quantitative_score == 0:
        return validate_methodology_assignment(
            methodology_label="empirico",
            methodology_branch="empirico",
            methodology_review_required=True,
            methodology_review_reason=contract.review_reasons["insufficient_evidence"],
            contract=contract,
        )

    if qualitative_score == quantitative_score:
        return validate_methodology_assignment(
            methodology_label="empirico",
            methodology_branch="empirico",
            methodology_review_required=True,
            methodology_review_reason=contract.review_reasons["conflicting_cues"],
            contract=contract,
        )

    subtype = (
        "cualitativo" if qualitative_score > quantitative_score else "cuantitativo"
    )
    margin = abs(qualitative_score - quantitative_score)
    review_required = (
        qualitative_score > 0
        and quantitative_score > 0
        and margin <= config.heuristics.signal_margin
    )
    review_reason = (
        contract.review_reasons["conflicting_cues"] if review_required else ""
    )
    return validate_methodology_assignment(
        methodology_label="empirico",
        methodology_branch="empirico",
        methodology_subtype=subtype,
        methodology_review_required=review_required,
        methodology_review_reason=review_reason,
        contract=contract,
    )


def write_methodology_outputs(
    assignments: pd.DataFrame,
    *,
    run_dir: Path,
    reviewed_labels: pd.DataFrame | None = None,
    contract: MethodologyContract | None = None,
    root: Path | None = None,
) -> MethodologyRunArtifacts:
    project_root = root or ROOT
    methodology_contract = contract or load_methodology_contract(root=project_root)

    run_dir.mkdir(parents=True, exist_ok=True)
    assignments_path = run_dir / "methodology_assignments.csv"
    review_queue_path = run_dir / "methodology_review_queue.csv"
    summary_path = run_dir / "methodology_summary.json"
    metrics_paths: dict[str, Path] = {}

    assignments.to_csv(assignments_path, index=False, encoding="utf-8")
    review_queue = assignments.loc[
        assignments["methodology_review_required"].astype(bool)
    ].copy()
    review_queue.to_csv(review_queue_path, index=False, encoding="utf-8")

    summary = _build_methodology_summary(assignments, evaluation_status=_REVIEW_REASON_SKIPPED)

    if reviewed_labels is not None:
        metrics_paths = _write_methodology_evaluation(
            assignments=assignments,
            reviewed_labels=reviewed_labels,
            run_dir=run_dir,
            contract=methodology_contract,
        )
        if metrics_paths:
            summary["evaluation_status"] = "completed"

    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return MethodologyRunArtifacts(
        assignments_path=assignments_path,
        review_queue_path=review_queue_path,
        summary_path=summary_path,
        metrics_paths=metrics_paths,
    )


def load_reviewed_methodology_labels(
    reviewed_labels_artifact: str | Path,
    *,
    root: Path | None = None,
) -> pd.DataFrame:
    project_root = root or ROOT
    input_path = resolve_project_path(reviewed_labels_artifact, root=project_root)
    reviewed_labels = pd.read_csv(input_path)
    required_columns = {"record_id", "methodology_label"}
    missing_columns = sorted(required_columns - set(reviewed_labels.columns))
    if missing_columns:
        raise ValueError(
            "Reviewed methodology artifact is missing required columns: "
            f"{missing_columns}"
        )
    reviewed_labels["methodology_label"] = (
        reviewed_labels["methodology_label"].fillna("").map(str).str.strip()
    )
    reviewed_labels["methodology_subtype"] = (
        reviewed_labels.get("methodology_subtype", "")
        .fillna("")
        .map(str)
        .str.strip()
    )
    return reviewed_labels


def _write_methodology_evaluation(
    *,
    assignments: pd.DataFrame,
    reviewed_labels: pd.DataFrame,
    run_dir: Path,
    contract: MethodologyContract,
) -> dict[str, Path]:
    merged = assignments.merge(
        reviewed_labels.loc[:, ["record_id", "methodology_label", "methodology_subtype"]]
        .rename(
            columns={
                "methodology_label": "reviewed_methodology_label",
                "methodology_subtype": "reviewed_methodology_subtype",
            }
        ),
        on="record_id",
        how="inner",
        validate="one_to_one",
    )
    merged = merged.loc[merged["reviewed_methodology_label"].map(str).str.strip() != ""].copy()
    if merged.empty:
        return {}

    label_order = ["NN", "no_empirico", "empirico"]
    label_lookup = {label: label for label in label_order}
    overall_metrics = _build_label_metrics_json(
        merged["reviewed_methodology_label"],
        merged["methodology_label"],
        label_order=label_order,
        label_lookup=label_lookup,
        metrics_key="methodology_label",
    )
    overall_metrics["reviewed_row_count"] = int(len(merged))

    overall_path = run_dir / "methodology_metrics_overall.json"
    per_class_path = run_dir / "methodology_metrics_per_class.csv"
    confusion_path = run_dir / "methodology_confusion_matrix.csv"
    predictions_path = run_dir / "methodology_review_predictions.csv"

    overall_path.write_text(
        json.dumps(overall_metrics, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    _build_per_class_metrics_frame(
        merged["reviewed_methodology_label"],
        merged["methodology_label"],
        label_order=label_order,
        label_lookup=label_lookup,
    ).to_csv(per_class_path, index=False, encoding="utf-8")
    _build_confusion_matrix_frame(
        merged["reviewed_methodology_label"],
        merged["methodology_label"],
        label_order=label_order,
    ).to_csv(confusion_path, encoding="utf-8")
    merged.to_csv(predictions_path, index=False, encoding="utf-8")

    subtype_rows = merged.loc[
        (merged["reviewed_methodology_label"] == "empirico")
        & (merged["reviewed_methodology_subtype"].map(str).str.strip() != "")
    ].copy()
    extra_paths: dict[str, Path] = {
        "metrics_overall": overall_path,
        "metrics_per_class": per_class_path,
        "confusion_matrix": confusion_path,
        "review_predictions": predictions_path,
    }

    if not subtype_rows.empty:
        subtype_order = ["cualitativo", "cuantitativo"]
        subtype_lookup = {label: label for label in subtype_order}
        subtype_metrics_path = run_dir / "methodology_subtype_metrics.csv"
        subtype_confusion_path = run_dir / "methodology_subtype_confusion_matrix.csv"
        _build_per_class_metrics_frame(
            subtype_rows["reviewed_methodology_subtype"],
            subtype_rows["methodology_subtype"],
            label_order=subtype_order,
            label_lookup=subtype_lookup,
        ).to_csv(subtype_metrics_path, index=False, encoding="utf-8")
        _build_confusion_matrix_frame(
            subtype_rows["reviewed_methodology_subtype"],
            subtype_rows["methodology_subtype"],
            label_order=subtype_order,
        ).to_csv(subtype_confusion_path, encoding="utf-8")
        extra_paths["subtype_metrics"] = subtype_metrics_path
        extra_paths["subtype_confusion_matrix"] = subtype_confusion_path

        subtype_summary = _build_label_metrics_json(
            subtype_rows["reviewed_methodology_subtype"],
            subtype_rows["methodology_subtype"],
            label_order=subtype_order,
            label_lookup=subtype_lookup,
            metrics_key="methodology_subtype",
        )
        overall_metrics["subtype_metrics"] = subtype_summary
        overall_path.write_text(
            json.dumps(overall_metrics, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    return extra_paths


def _build_methodology_summary(
    assignments: pd.DataFrame,
    *,
    evaluation_status: str,
) -> dict[str, object]:
    label_counts = (
        assignments["methodology_label"]
        .fillna("")
        .map(str)
        .str.strip()
        .replace("", "unassigned")
        .value_counts()
        .to_dict()
    )
    review_reason_counts = (
        assignments.loc[assignments["methodology_review_required"].astype(bool)]
        .get("methodology_review_reason", pd.Series(dtype=str))
        .fillna("")
        .map(str)
        .str.strip()
        .replace("", "unspecified")
        .value_counts()
        .to_dict()
    )
    return {
        "row_count": int(len(assignments)),
        "label_counts": label_counts,
        "review_queue_count": int(assignments["methodology_review_required"].astype(bool).sum()),
        "review_reason_counts": review_reason_counts,
        "evaluation_status": evaluation_status,
    }


def _build_label_metrics_json(
    actual_labels: pd.Series,
    predicted_labels: pd.Series,
    *,
    label_order: list[str],
    label_lookup: dict[str, str],
    metrics_key: str,
) -> dict[str, object]:
    return {
        "metrics_key": metrics_key,
        "row_count": int(len(actual_labels)),
        "accuracy": float(accuracy_score(actual_labels, predicted_labels)),
        "macro_f1": float(
            f1_score(actual_labels, predicted_labels, labels=label_order, average="macro")
        ),
        "weighted_f1": float(
            f1_score(actual_labels, predicted_labels, labels=label_order, average="weighted")
        ),
        "label_order": [
            {"identifier": label, "label": label_lookup[label]} for label in label_order
        ],
    }


def _build_per_class_metrics_frame(
    actual_labels: pd.Series,
    predicted_labels: pd.Series,
    *,
    label_order: list[str],
    label_lookup: dict[str, str],
) -> pd.DataFrame:
    report = classification_report(
        actual_labels,
        predicted_labels,
        labels=label_order,
        output_dict=True,
        zero_division=0,
    )
    rows: list[dict[str, object]] = []
    for label in label_order:
        metrics = report[label]
        rows.append(
            {
                "identifier": label,
                "label": label_lookup[label],
                "precision": float(metrics["precision"]),
                "recall": float(metrics["recall"]),
                "f1_score": float(metrics["f1-score"]),
                "support": int(metrics["support"]),
            }
        )
    return pd.DataFrame.from_records(rows)


def _build_confusion_matrix_frame(
    actual_labels: pd.Series,
    predicted_labels: pd.Series,
    *,
    label_order: list[str],
) -> pd.DataFrame:
    matrix = confusion_matrix(actual_labels, predicted_labels, labels=label_order)
    frame = pd.DataFrame(matrix, index=label_order, columns=label_order)
    frame.index.name = "actual_identifier"
    return frame


def _compose_analysis_text(row: dict[str, object]) -> str:
    parts: list[str] = []
    for key in ("title", "abstract", "author_keywords", "index_keywords"):
        value = str(row.get(key, "")).strip()
        if value:
            parts.append(value.lower())
    return "\n".join(parts)


def _collect_matches(text: str, cues: tuple[str, ...]) -> tuple[str, ...]:
    matches = [cue for cue in cues if cue in text]
    return tuple(dict.fromkeys(matches))


def _normalize_cues(values: Any) -> tuple[str, ...]:
    cues: list[str] = []
    for value in values:
        text = re.sub(r"\s+", " ", str(value).strip().lower())
        if text:
            cues.append(text)
    return tuple(cues)
