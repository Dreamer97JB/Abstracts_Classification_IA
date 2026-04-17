from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score

from .taxonomy import ROOT
from .text_variants import (
    build_text_variant_frame,
    load_governed_text_metadata,
    summarize_keyword_coverage,
    validate_text_variant,
)
from .training import (
    DEFAULT_BASELINE_CONFIG,
    TheoryBaselineConfig,
    load_theory_baseline_config,
    load_theory_dataset,
    load_run_manifest,
    load_trained_pipeline,
    resolve_run_dir,
    train_theory_baseline,
)


def evaluate_run(
    *,
    config: TheoryBaselineConfig,
    run_id: str,
    output_dir: str | Path | None = None,
    split_name: str | None = None,
    root: Path | None = None,
) -> dict[str, Path]:
    project_root = root or ROOT
    run_dir = resolve_run_dir(
        config=config,
        run_id=run_id,
        output_dir=output_dir,
        root=project_root,
    )
    manifest = load_run_manifest(run_dir)
    if manifest["run_id"] != run_id:
        raise ValueError(
            f"Requested run_id `{run_id}` does not match manifest run_id "
            f"`{manifest['run_id']}`."
        )

    pipeline = load_trained_pipeline(run_dir)
    dataset = load_theory_dataset(config, root=project_root)
    effective_split = (split_name or config.evaluation.default_split).strip().lower()
    evaluation_rows = dataset.rows_for_split(effective_split)
    text_metadata = load_governed_text_metadata(
        root=project_root,
        supervision_config_path=config.supervision_config_path,
    )
    variant_name = validate_text_variant(str(manifest["text_variant"]))
    variant_rows = build_text_variant_frame(
        evaluation_rows,
        text_variant=variant_name,
        text_metadata=text_metadata,
    )
    keyword_coverage = summarize_keyword_coverage(
        variant_rows,
        text_variant=variant_name,
    )

    predicted_labels = pipeline.predict(variant_rows["text_input"])
    if hasattr(pipeline, "predict_proba"):
        probabilities = pipeline.predict_proba(variant_rows["text_input"])
        prediction_scores = probabilities.max(axis=1)
    else:
        prediction_scores = [None] * len(variant_rows)

    overall_metrics = _build_overall_metrics(
        variant_rows=variant_rows,
        predicted_labels=predicted_labels,
        prediction_scores=prediction_scores,
        label_order=dataset.label_order,
        label_lookup=dataset.label_lookup,
        run_id=run_id,
        split_name=effective_split,
        split_version=dataset.split_version,
        text_variant=variant_name,
        keyword_coverage=keyword_coverage.to_dict(),
    )
    per_class_metrics = _build_per_class_metrics(
        variant_rows=variant_rows,
        predicted_labels=predicted_labels,
        label_order=dataset.label_order,
        label_lookup=dataset.label_lookup,
    )
    confusion_frame = _build_confusion_matrix_frame(
        variant_rows=variant_rows,
        predicted_labels=predicted_labels,
        label_order=dataset.label_order,
    )
    predictions_frame = _build_predictions_frame(
        variant_rows=variant_rows,
        predicted_labels=predicted_labels,
        prediction_scores=prediction_scores,
        label_lookup=dataset.label_lookup,
        split_name=effective_split,
        split_version=dataset.split_version,
        text_variant=variant_name,
    )

    overall_metrics_path = run_dir / "metrics_overall.json"
    per_class_path = run_dir / "metrics_per_class.csv"
    confusion_path = run_dir / "confusion_matrix.csv"
    predictions_path = run_dir / "predictions.csv"

    overall_metrics_path.write_text(
        json.dumps(overall_metrics, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    per_class_metrics.to_csv(per_class_path, index=False, encoding="utf-8")
    confusion_frame.to_csv(confusion_path, encoding="utf-8")
    predictions_frame.to_csv(predictions_path, index=False, encoding="utf-8")
    return {
        "run_dir": run_dir,
        "metrics_overall": overall_metrics_path,
        "metrics_per_class": per_class_path,
        "confusion_matrix": confusion_path,
        "predictions": predictions_path,
    }


def compare_text_variants(
    *,
    config: TheoryBaselineConfig,
    variants: tuple[str, ...],
    output_dir: str | Path,
    split_name: str | None = None,
    root: Path | None = None,
) -> Path:
    project_root = root or ROOT
    compare_root = Path(output_dir)
    if not compare_root.is_absolute():
        compare_root = (project_root / compare_root).resolve()
    compare_root.mkdir(parents=True, exist_ok=True)

    effective_split = (split_name or config.evaluation.default_split).strip().lower()
    comparison_rows: list[dict[str, object]] = []
    for variant in variants:
        variant_name = validate_text_variant(variant)
        variant_run_id = f"{variant_name}_{effective_split}"
        variant_dir = compare_root / variant_name
        train_theory_baseline(
            config=config,
            run_id=variant_run_id,
            output_dir=variant_dir,
            text_variant=variant_name,
            root=project_root,
        )
        evaluation_paths = evaluate_run(
            config=config,
            run_id=variant_run_id,
            output_dir=variant_dir,
            split_name=effective_split,
            root=project_root,
        )
        overall_metrics = json.loads(
            evaluation_paths["metrics_overall"].read_text(encoding="utf-8")
        )
        comparison_rows.append(
            {
                "run_id": variant_run_id,
                "text_variant": variant_name,
                "split": effective_split,
                "split_version": overall_metrics["split_version"],
                "accuracy": overall_metrics["accuracy"],
                "macro_f1": overall_metrics["macro_f1"],
                "weighted_f1": overall_metrics["weighted_f1"],
                "keyword_availability_rate": overall_metrics["keyword_coverage"][
                    "keyword_availability_rate"
                ],
                "keyword_coverage_rate": overall_metrics["keyword_coverage"][
                    "keyword_coverage_rate"
                ],
                "output_dir": _relative_path(variant_dir, project_root),
            }
        )

    comparison_frame = pd.DataFrame.from_records(comparison_rows)
    comparison_path = compare_root / "variant_comparison.csv"
    comparison_frame.to_csv(comparison_path, index=False, encoding="utf-8")
    return comparison_path


def load_baseline_config(path: str | Path = DEFAULT_BASELINE_CONFIG) -> TheoryBaselineConfig:
    return load_theory_baseline_config(path)


def _build_overall_metrics(
    *,
    variant_rows: pd.DataFrame,
    predicted_labels: Any,
    prediction_scores: Any,
    label_order: tuple[str, ...],
    label_lookup: dict[str, str],
    run_id: str,
    split_name: str,
    split_version: str,
    text_variant: str,
    keyword_coverage: dict[str, object],
) -> dict[str, object]:
    actual_labels = variant_rows["canonical_id"]
    return {
        "run_id": run_id,
        "split": split_name,
        "split_version": split_version,
        "text_variant": text_variant,
        "row_count": int(len(variant_rows)),
        "accuracy": float(accuracy_score(actual_labels, predicted_labels)),
        "macro_f1": float(
            f1_score(actual_labels, predicted_labels, labels=label_order, average="macro")
        ),
        "weighted_f1": float(
            f1_score(actual_labels, predicted_labels, labels=label_order, average="weighted")
        ),
        "label_order": [
            {
                "canonical_id": canonical_id,
                "label_canonica": label_lookup[canonical_id],
            }
            for canonical_id in label_order
        ],
        "prediction_score_semantics": (
            "max_class_probability"
            if len(prediction_scores) > 0 and prediction_scores[0] is not None
            else "not_available"
        ),
        "keyword_coverage": keyword_coverage,
    }


def _build_per_class_metrics(
    *,
    variant_rows: pd.DataFrame,
    predicted_labels: Any,
    label_order: tuple[str, ...],
    label_lookup: dict[str, str],
) -> pd.DataFrame:
    report = classification_report(
        variant_rows["canonical_id"],
        predicted_labels,
        labels=list(label_order),
        output_dict=True,
        zero_division=0,
    )
    rows: list[dict[str, object]] = []
    for canonical_id in label_order:
        metrics = report[canonical_id]
        rows.append(
            {
                "canonical_id": canonical_id,
                "label_canonica": label_lookup[canonical_id],
                "precision": float(metrics["precision"]),
                "recall": float(metrics["recall"]),
                "f1_score": float(metrics["f1-score"]),
                "support": int(metrics["support"]),
            }
        )
    return pd.DataFrame.from_records(rows)


def _build_confusion_matrix_frame(
    *,
    variant_rows: pd.DataFrame,
    predicted_labels: Any,
    label_order: tuple[str, ...],
) -> pd.DataFrame:
    matrix = confusion_matrix(
        variant_rows["canonical_id"],
        predicted_labels,
        labels=list(label_order),
    )
    frame = pd.DataFrame(matrix, index=label_order, columns=label_order)
    frame.index.name = "actual_canonical_id"
    return frame


def _build_predictions_frame(
    *,
    variant_rows: pd.DataFrame,
    predicted_labels: Any,
    prediction_scores: Any,
    label_lookup: dict[str, str],
    split_name: str,
    split_version: str,
    text_variant: str,
) -> pd.DataFrame:
    predictions = variant_rows.loc[
        :,
        [
            "record_id",
            "source_dataset",
            "source_sheet",
            "title",
            "year",
            "doi",
            "label_original",
            "canonical_id",
            "label_canonica",
            "author_keywords",
            "index_keywords",
            "keywords_available",
            "keywords_applied",
        ],
    ].copy()
    predictions["split"] = split_name
    predictions["split_version"] = split_version
    predictions["text_variant"] = text_variant
    predictions["predicted_canonical_id"] = predicted_labels
    predictions["predicted_label_canonica"] = [
        label_lookup[predicted_label] for predicted_label in predicted_labels
    ]
    predictions["prediction_score"] = prediction_scores
    return predictions


def _relative_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())
