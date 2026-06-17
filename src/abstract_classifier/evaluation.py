from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    classification_report,
    confusion_matrix,
    f1_score,
)

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
    build_capped_balanced_class_weight,
    load_theory_baseline_config,
    load_theory_dataset,
    load_run_manifest,
    load_trained_pipeline,
    resolve_run_dir,
    train_theory_baseline,
    validate_model_family,
    with_model_family,
    with_training_class_weight,
)


@dataclass(frozen=True)
class CalibrationArtifacts:
    run_dir: Path
    manifest_path: Path
    reliability_table_path: Path
    threshold_sweep_path: Path
    calibration_summary_path: Path
    promotion_gate_path: Path
    imbalance_policy_comparison_path: Path
    score_calibrator_path: Path


@dataclass(frozen=True)
class ConformalAdmissionSummary:
    policy_name: str
    alpha: float
    reference_row_count: int
    correct_reference_row_count: int
    minimum_required_correct_rows: int
    score_threshold: float
    nonconformity_threshold: float
    singleton_safe_rule: str
    threshold_source: str

    def to_dict(self) -> dict[str, object]:
        return {
            "policy_name": self.policy_name,
            "alpha": self.alpha,
            "reference_row_count": self.reference_row_count,
            "correct_reference_row_count": self.correct_reference_row_count,
            "minimum_required_correct_rows": self.minimum_required_correct_rows,
            "score_threshold": self.score_threshold,
            "nonconformity_threshold": self.nonconformity_threshold,
            "singleton_safe_rule": self.singleton_safe_rule,
            "threshold_source": self.threshold_source,
        }


class IdentityCalibrator:
    """Fallback calibrator when isotonic fitting is not statistically viable."""

    def predict(self, scores: list[float]) -> list[float]:
        return [float(min(max(score, 0.0), 1.0)) for score in scores]


def derive_conformal_admission_summary(
    predictions_artifact: str | Path,
    *,
    alpha: float = 0.2,
    minimum_required_correct_rows: int = 5,
) -> ConformalAdmissionSummary:
    predictions_path = Path(predictions_artifact)
    frame = pd.read_csv(predictions_path)
    required_columns = {
        "canonical_id",
        "predicted_canonical_id",
        "prediction_score",
    }
    missing_columns = sorted(required_columns - set(frame.columns))
    if missing_columns:
        raise ValueError(
            "Conformal admission reference predictions are missing required columns: "
            f"{missing_columns}"
        )

    if not 0.0 < float(alpha) < 1.0:
        raise ValueError("Conformal alpha must be between 0 and 1.")

    scores = pd.to_numeric(frame["prediction_score"], errors="coerce")
    valid = frame.loc[scores.notna()].copy()
    valid_scores = scores.loc[scores.notna()].astype(float).reset_index(drop=True)
    valid = valid.reset_index(drop=True)
    valid["prediction_score"] = valid_scores
    valid["is_correct"] = (
        valid["canonical_id"].astype(str) == valid["predicted_canonical_id"].astype(str)
    )
    correct_scores = (
        valid.loc[valid["is_correct"], "prediction_score"].astype(float).sort_values().tolist()
    )

    if len(correct_scores) >= int(minimum_required_correct_rows):
        score_threshold = _empirical_quantile_lower(correct_scores, alpha)
        threshold_source = "correct_predictions_lower_quantile"
    elif correct_scores:
        score_threshold = min(correct_scores)
        threshold_source = "correct_predictions_min_fallback"
    else:
        score_threshold = 1.0
        threshold_source = "no_correct_predictions_fail_safe"

    nonconformity_threshold = float(1.0 - score_threshold)
    return ConformalAdmissionSummary(
        policy_name="top1_score_singleton_safe_estimate",
        alpha=float(alpha),
        reference_row_count=int(len(valid)),
        correct_reference_row_count=int(len(correct_scores)),
        minimum_required_correct_rows=int(minimum_required_correct_rows),
        score_threshold=float(score_threshold),
        nonconformity_threshold=nonconformity_threshold,
        singleton_safe_rule=(
            "accept only when calibrated_prediction_score >= score_threshold; "
            "otherwise treat as uncertain_multi"
        ),
        threshold_source=threshold_source,
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
    operational_predictions_path = run_dir / "operational_predictions.csv"
    operational_summary_path = run_dir / "operational_summary.json"

    overall_metrics_path.write_text(
        json.dumps(overall_metrics, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    per_class_metrics.to_csv(per_class_path, index=False, encoding="utf-8")
    confusion_frame.to_csv(confusion_path, encoding="utf-8")
    predictions_frame.to_csv(predictions_path, index=False, encoding="utf-8")
    if config.trusted_experiment_artifact_path is not None:
        operational_predictions, operational_summary = score_operational_corpus(
            config=config,
            run_id=run_id,
            output_dir=run_dir,
            root=project_root,
        )
        operational_predictions.to_csv(
            operational_predictions_path,
            index=False,
            encoding="utf-8",
        )
        operational_summary_path.write_text(
            json.dumps(operational_summary, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    return {
        "run_dir": run_dir,
        "metrics_overall": overall_metrics_path,
        "metrics_per_class": per_class_path,
        "confusion_matrix": confusion_path,
        "predictions": predictions_path,
        "operational_predictions": operational_predictions_path
        if config.trusted_experiment_artifact_path is not None
        else None,
        "operational_summary": operational_summary_path
        if config.trusted_experiment_artifact_path is not None
        else None,
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


def score_operational_corpus(
    *,
    config: TheoryBaselineConfig,
    run_id: str,
    output_dir: str | Path | None = None,
    root: Path | None = None,
) -> tuple[pd.DataFrame, dict[str, object]]:
    if config.trusted_experiment_artifact_path is None:
        raise ValueError("trusted_experiment_artifact_path is not configured.")

    project_root = root or ROOT
    run_dir = resolve_run_dir(
        config=config,
        run_id=run_id,
        output_dir=output_dir,
        root=project_root,
    )
    manifest = load_run_manifest(run_dir)
    pipeline = load_trained_pipeline(run_dir)
    trusted_rows = pd.read_csv(config.trusted_experiment_artifact_path, encoding="utf-8")
    variant_name = validate_text_variant(str(manifest["text_variant"]))
    variant_rows = build_text_variant_frame(
        trusted_rows,
        text_variant=variant_name,
        text_metadata=None,
    )
    predicted_labels = pipeline.predict(variant_rows["text_input"])
    label_lookup = {
        item["canonical_id"]: item["label_canonica"]
        for item in manifest.get("label_lookup", [])
    }

    probabilities = pipeline.predict_proba(variant_rows["text_input"]) if hasattr(pipeline, "predict_proba") else None
    predictions_frame = _build_operational_predictions_frame(
        variant_rows=variant_rows,
        predicted_labels=predicted_labels,
        probabilities=probabilities,
        label_lookup=label_lookup,
        run_id=run_id,
        text_variant=variant_name,
    )
    summary = _build_operational_summary(
        predictions_frame,
        production_target_artifact_path=config.trusted_production_artifact_path,
        root=project_root,
    )
    return predictions_frame, summary


def compare_model_families(
    *,
    config: TheoryBaselineConfig,
    output_dir: str | Path,
    model_families: tuple[str, ...] | None = None,
    split_name: str | None = None,
    root: Path | None = None,
) -> dict[str, Path]:
    project_root = root or ROOT
    compare_root = Path(output_dir)
    if not compare_root.is_absolute():
        compare_root = (project_root / compare_root).resolve()
    compare_root.mkdir(parents=True, exist_ok=True)

    effective_split = (split_name or config.evaluation.default_split).strip().lower()
    requested_families = model_families or config.candidate_model_families
    if not requested_families:
        raise ValueError(
            "compare_model_families requires at least one challenger model family."
        )
    families = tuple(validate_model_family(item) for item in requested_families)

    comparison_rows: list[dict[str, object]] = []
    per_class_frames: list[pd.DataFrame] = []

    anchor_row, anchor_per_class = _anchor_comparison_rows(config, project_root)
    if anchor_row is not None:
        comparison_rows.append(anchor_row)
    if anchor_per_class is not None:
        per_class_frames.append(anchor_per_class)

    for family in families:
        family_config = with_model_family(config, family)
        variant_run_id = f"{family}_{effective_split}"
        family_dir = compare_root / family
        train_theory_baseline(
            config=family_config,
            run_id=variant_run_id,
            output_dir=family_dir,
            root=project_root,
        )
        evaluation_paths = evaluate_run(
            config=family_config,
            run_id=variant_run_id,
            output_dir=family_dir,
            split_name=effective_split,
            root=project_root,
        )
        overall_metrics = json.loads(
            evaluation_paths["metrics_overall"].read_text(encoding="utf-8")
        )
        operational_summary = (
            json.loads(
                evaluation_paths["operational_summary"].read_text(encoding="utf-8")
            )
            if evaluation_paths["operational_summary"] is not None
            else {}
        )
        comparison_rows.append(
            _build_comparison_row(
                run_id=variant_run_id,
                model_family=family,
                metrics=overall_metrics,
                operational_summary=operational_summary,
                output_dir=family_dir,
                root=project_root,
                trusted_production_artifact_path=config.trusted_production_artifact_path,
            )
        )
        per_class_frame = pd.read_csv(
            evaluation_paths["metrics_per_class"],
            encoding="utf-8",
        )
        per_class_frame.insert(0, "run_id", variant_run_id)
        per_class_frame.insert(1, "model_family", family)
        per_class_frames.append(per_class_frame)

    comparison_frame = pd.DataFrame.from_records(comparison_rows)
    comparison_frame = comparison_frame.sort_values(
        by=["macro_f1", "weighted_f1", "operational_median_prediction_margin"],
        ascending=[False, False, False],
        na_position="last",
    ).reset_index(drop=True)
    comparison_path = compare_root / "experiment_comparison.csv"
    comparison_frame.to_csv(comparison_path, index=False, encoding="utf-8")

    per_class_path = compare_root / "experiment_per_class_metrics.csv"
    if per_class_frames:
        pd.concat(per_class_frames, ignore_index=True).to_csv(
            per_class_path,
            index=False,
            encoding="utf-8",
        )
    else:
        pd.DataFrame().to_csv(per_class_path, index=False, encoding="utf-8")

    champion = comparison_frame.iloc[0].to_dict()
    champion_summary = {
        "selected_run_id": champion["run_id"],
        "selected_model_family": champion["model_family"],
        "selection_basis": [
            "macro_f1",
            "weighted_f1",
            "operational_median_prediction_margin",
        ],
        "trusted_production_artifact": (
            _relative_path(config.trusted_production_artifact_path, project_root)
            if config.trusted_production_artifact_path is not None
            else None
        ),
        "comparison_artifact": comparison_path.name,
    }
    champion_path = compare_root / "champion_summary.json"
    champion_path.write_text(
        json.dumps(champion_summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return {
        "comparison": comparison_path,
        "per_class": per_class_path,
        "champion": champion_path,
    }


def calibrate_run(
    *,
    config: TheoryBaselineConfig,
    run_id: str,
    model_run_dir: str | Path,
    output_dir: str | Path | None = None,
    root: Path | None = None,
) -> CalibrationArtifacts:
    project_root = root or ROOT
    model_dir = Path(model_run_dir)
    if not model_dir.is_absolute():
        model_dir = (project_root / model_dir).resolve()

    model_manifest = load_run_manifest(model_dir)
    pipeline = load_trained_pipeline(model_dir)
    if not hasattr(pipeline, "predict_proba"):
        raise ValueError("The configured model does not expose predict_proba().")

    dataset = load_theory_dataset(config, root=project_root)
    variant_name = validate_text_variant(str(model_manifest["text_variant"]))
    text_metadata = load_governed_text_metadata(
        root=project_root,
        supervision_config_path=config.supervision_config_path,
    )
    val_rows = build_text_variant_frame(
        dataset.rows_for_split("val"),
        text_variant=variant_name,
        text_metadata=text_metadata,
    )
    test_rows = build_text_variant_frame(
        dataset.rows_for_split("test"),
        text_variant=variant_name,
        text_metadata=text_metadata,
    )

    if val_rows.empty or test_rows.empty:
        raise ValueError("Calibration requires non-empty val and test splits.")

    val_predictions, val_scores, val_margins = _score_split(
        pipeline,
        val_rows["text_input"],
    )
    val_correct = (
        val_rows["canonical_id"].reset_index(drop=True) == pd.Series(val_predictions)
    ).astype(int)
    calibrator, calibrator_summary = _fit_score_calibrator(val_scores, val_correct)

    test_predictions, test_scores_raw, test_margins = _score_split(
        pipeline,
        test_rows["text_input"],
    )
    val_scores_calibrated = _calibrate_scores(calibrator, val_scores)
    test_scores_calibrated = _calibrate_scores(calibrator, test_scores_raw)

    reliability_table = pd.concat(
        [
            _build_reliability_table(
                split_name="val",
                score_view="raw",
                scores=val_scores,
                correctness=val_correct,
            ),
            _build_reliability_table(
                split_name="val",
                score_view="calibrated",
                scores=val_scores_calibrated,
                correctness=val_correct,
            ),
            _build_reliability_table(
                split_name="test",
                score_view="raw",
                scores=test_scores_raw,
                correctness=(
                    test_rows["canonical_id"].reset_index(drop=True)
                    == pd.Series(test_predictions)
                ).astype(int),
            ),
            _build_reliability_table(
                split_name="test",
                score_view="calibrated",
                scores=test_scores_calibrated,
                correctness=(
                    test_rows["canonical_id"].reset_index(drop=True)
                    == pd.Series(test_predictions)
                ).astype(int),
            ),
        ],
        ignore_index=True,
    )

    threshold_sweep = _build_threshold_sweep(
        actual_labels=test_rows["canonical_id"].reset_index(drop=True),
        predicted_labels=pd.Series(test_predictions),
        calibrated_scores=test_scores_calibrated,
        prediction_margins=test_margins,
        label_order=dataset.label_order,
        baseline_macro_f1=_load_reference_metric(model_dir, "macro_f1"),
        baseline_weighted_f1=_load_reference_metric(model_dir, "weighted_f1"),
        required_retained_accuracy=config.evaluation.required_retained_accuracy,
        required_coverage_rate=config.evaluation.required_coverage_rate,
    )
    recommended_policy = _select_recommended_policy(
        threshold_sweep=threshold_sweep,
        required_retained_accuracy=config.evaluation.required_retained_accuracy,
        required_coverage_rate=config.evaluation.required_coverage_rate,
    )
    imbalance_policy_comparison = _build_imbalance_policy_comparison(
        config=config,
        dataset=dataset,
        model_manifest=model_manifest,
        text_variant=variant_name,
        output_root=_resolve_calibration_run_dir(
            run_id=run_id,
            output_dir=output_dir,
            root=project_root,
        )
        / "imbalance_policy_runs",
        root=project_root,
    )

    run_dir = _resolve_calibration_run_dir(
        run_id=run_id,
        output_dir=output_dir,
        root=project_root,
    )
    run_dir.mkdir(parents=True, exist_ok=True)

    reliability_table_path = run_dir / "reliability_table.csv"
    threshold_sweep_path = run_dir / "threshold_sweep.csv"
    calibration_summary_path = run_dir / "calibration_summary.json"
    promotion_gate_path = run_dir / "promotion_gate.json"
    imbalance_policy_comparison_path = run_dir / "imbalance_policy_comparison.csv"
    score_calibrator_path = run_dir / "score_calibrator.joblib"
    manifest_path = run_dir / "calibration_manifest.json"

    joblib.dump(calibrator, score_calibrator_path)
    reliability_table.to_csv(reliability_table_path, index=False, encoding="utf-8")
    threshold_sweep.to_csv(threshold_sweep_path, index=False, encoding="utf-8")
    imbalance_policy_comparison.to_csv(
        imbalance_policy_comparison_path,
        index=False,
        encoding="utf-8",
    )

    promotion_gate = _build_promotion_gate(
        recommended_policy=recommended_policy,
        config=config,
        model_dir=model_dir,
        score_calibrator_path=score_calibrator_path,
        root=project_root,
    )
    promotion_gate_path.write_text(
        json.dumps(promotion_gate, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    calibration_summary = _build_calibration_summary(
        model_manifest=model_manifest,
        calibrator_summary=calibrator_summary,
        val_correct=val_correct,
        val_scores=val_scores,
        val_scores_calibrated=val_scores_calibrated,
        test_actual=test_rows["canonical_id"].reset_index(drop=True),
        test_predictions=pd.Series(test_predictions),
        test_scores_raw=test_scores_raw,
        test_scores_calibrated=test_scores_calibrated,
        recommended_policy=recommended_policy,
        promotion_gate=promotion_gate,
        imbalance_policy_comparison=imbalance_policy_comparison,
    )
    calibration_summary_path.write_text(
        json.dumps(calibration_summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    manifest = {
        "run_id": run_id,
        "config_version": config.version,
        "config_path": _relative_path(config.config_path, project_root),
        "model_run_id": model_manifest["run_id"],
        "model_run_directory": _relative_path(model_dir, project_root),
        "model_family": model_manifest["model_family"],
        "text_variant": variant_name,
        "calibration_split": "val",
        "evaluation_split": "test",
        "required_retained_accuracy": config.evaluation.required_retained_accuracy,
        "required_coverage_rate": config.evaluation.required_coverage_rate,
        "artifacts": {
            "score_calibrator": score_calibrator_path.name,
            "reliability_table": reliability_table_path.name,
            "threshold_sweep": threshold_sweep_path.name,
            "promotion_gate": promotion_gate_path.name,
            "calibration_summary": calibration_summary_path.name,
            "imbalance_policy_comparison": imbalance_policy_comparison_path.name,
        },
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return CalibrationArtifacts(
        run_dir=run_dir,
        manifest_path=manifest_path,
        reliability_table_path=reliability_table_path,
        threshold_sweep_path=threshold_sweep_path,
        calibration_summary_path=calibration_summary_path,
        promotion_gate_path=promotion_gate_path,
        imbalance_policy_comparison_path=imbalance_policy_comparison_path,
        score_calibrator_path=score_calibrator_path,
    )


def load_baseline_config(path: str | Path = DEFAULT_BASELINE_CONFIG) -> TheoryBaselineConfig:
    return load_theory_baseline_config(path)


def _score_split(pipeline, text_input: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    probabilities = pipeline.predict_proba(text_input)
    predicted_labels = pd.Series(pipeline.predict(text_input))
    probability_frame = pd.DataFrame(probabilities)
    ranked_scores = probability_frame.apply(
        lambda row: row.sort_values(ascending=False).tolist(),
        axis=1,
    )
    top_scores = pd.Series([float(scores[0]) for scores in ranked_scores], dtype="float64")
    margins = pd.Series(
        [float(scores[0] - scores[1]) for scores in ranked_scores],
        dtype="float64",
    )
    return predicted_labels, top_scores, margins


def _fit_score_calibrator(
    scores: pd.Series,
    correctness: pd.Series,
) -> tuple[IdentityCalibrator | IsotonicRegression, dict[str, object]]:
    unique_outcomes = set(int(value) for value in correctness.tolist())
    if len(unique_outcomes) < 2 or len(scores) < 8:
        return (
            IdentityCalibrator(),
            {
                "calibrator_type": "identity",
                "reason": "insufficient_val_variation",
                "val_row_count": int(len(scores)),
            },
        )

    calibrator = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
    calibrator.fit(scores.astype(float).tolist(), correctness.astype(int).tolist())
    return (
        calibrator,
        {
            "calibrator_type": "isotonic_regression",
            "reason": "fit_success",
            "val_row_count": int(len(scores)),
        },
    )


def _calibrate_scores(
    calibrator: IdentityCalibrator | IsotonicRegression,
    scores: pd.Series,
) -> pd.Series:
    calibrated = calibrator.predict(scores.astype(float).tolist())
    return pd.Series(calibrated, dtype="float64")


def _build_reliability_table(
    *,
    split_name: str,
    score_view: str,
    scores: pd.Series,
    correctness: pd.Series,
) -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            "score": scores.astype(float),
            "correct": correctness.astype(int),
        }
    )
    bins = [index / 10 for index in range(11)]
    frame["score_bin"] = pd.cut(
        frame["score"],
        bins=bins,
        include_lowest=True,
        duplicates="drop",
    )
    grouped = (
        frame.groupby("score_bin", observed=False)
        .agg(
            row_count=("correct", "size"),
            empirical_accuracy=("correct", "mean"),
            mean_score=("score", "mean"),
        )
        .reset_index()
    )
    grouped["split"] = split_name
    grouped["score_view"] = score_view
    grouped["bin_lower"] = grouped["score_bin"].map(
        lambda item: float(item.left) if pd.notna(item) else None
    )
    grouped["bin_upper"] = grouped["score_bin"].map(
        lambda item: float(item.right) if pd.notna(item) else None
    )
    grouped["score_gap"] = grouped["mean_score"] - grouped["empirical_accuracy"]
    return grouped.loc[
        :,
        [
            "split",
            "score_view",
            "bin_lower",
            "bin_upper",
            "row_count",
            "mean_score",
            "empirical_accuracy",
            "score_gap",
        ],
    ]


def _build_threshold_sweep(
    *,
    actual_labels: pd.Series,
    predicted_labels: pd.Series,
    calibrated_scores: pd.Series,
    prediction_margins: pd.Series,
    label_order: tuple[str, ...],
    baseline_macro_f1: float,
    baseline_weighted_f1: float,
    required_retained_accuracy: float,
    required_coverage_rate: float,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    score_thresholds = [round(0.35 + 0.05 * index, 2) for index in range(12)]
    margin_thresholds = [round(0.02 + 0.02 * index, 2) for index in range(10)]

    for score_threshold in score_thresholds:
        rows.append(
            _evaluate_policy_row(
                actual_labels=actual_labels,
                predicted_labels=predicted_labels,
                calibrated_scores=calibrated_scores,
                prediction_margins=prediction_margins,
                label_order=label_order,
                policy_name=f"score_only_s{score_threshold:.2f}_m0.00",
                abstention_mode="score_only",
                score_threshold=score_threshold,
                margin_threshold=0.0,
                baseline_macro_f1=baseline_macro_f1,
                baseline_weighted_f1=baseline_weighted_f1,
                required_retained_accuracy=required_retained_accuracy,
                required_coverage_rate=required_coverage_rate,
            )
        )

    for margin_threshold in margin_thresholds:
        rows.append(
            _evaluate_policy_row(
                actual_labels=actual_labels,
                predicted_labels=predicted_labels,
                calibrated_scores=calibrated_scores,
                prediction_margins=prediction_margins,
                label_order=label_order,
                policy_name=f"margin_only_s0.00_m{margin_threshold:.2f}",
                abstention_mode="margin_only",
                score_threshold=0.0,
                margin_threshold=margin_threshold,
                baseline_macro_f1=baseline_macro_f1,
                baseline_weighted_f1=baseline_weighted_f1,
                required_retained_accuracy=required_retained_accuracy,
                required_coverage_rate=required_coverage_rate,
            )
        )

    for score_threshold in score_thresholds:
        for margin_threshold in margin_thresholds:
            rows.append(
                _evaluate_policy_row(
                    actual_labels=actual_labels,
                    predicted_labels=predicted_labels,
                    calibrated_scores=calibrated_scores,
                    prediction_margins=prediction_margins,
                    label_order=label_order,
                    policy_name=(
                        f"score_and_margin_s{score_threshold:.2f}_m{margin_threshold:.2f}"
                    ),
                    abstention_mode="score_and_margin",
                    score_threshold=score_threshold,
                    margin_threshold=margin_threshold,
                    baseline_macro_f1=baseline_macro_f1,
                    baseline_weighted_f1=baseline_weighted_f1,
                    required_retained_accuracy=required_retained_accuracy,
                    required_coverage_rate=required_coverage_rate,
                )
            )

    return pd.DataFrame.from_records(rows).sort_values(
        by=[
            "meets_promotion_gate",
            "coverage_rate",
            "retained_accuracy",
            "retained_macro_f1",
            "retained_weighted_f1",
        ],
        ascending=[False, False, False, False, False],
        na_position="last",
    ).reset_index(drop=True)


def _evaluate_policy_row(
    *,
    actual_labels: pd.Series,
    predicted_labels: pd.Series,
    calibrated_scores: pd.Series,
    prediction_margins: pd.Series,
    label_order: tuple[str, ...],
    policy_name: str,
    abstention_mode: str,
    score_threshold: float,
    margin_threshold: float,
    baseline_macro_f1: float,
    baseline_weighted_f1: float,
    required_retained_accuracy: float,
    required_coverage_rate: float,
) -> dict[str, object]:
    if abstention_mode == "score_only":
        retained_mask = calibrated_scores >= score_threshold
    elif abstention_mode == "margin_only":
        retained_mask = prediction_margins >= margin_threshold
    else:
        retained_mask = (calibrated_scores >= score_threshold) & (
            prediction_margins >= margin_threshold
        )

    retained_count = int(retained_mask.sum())
    total_count = int(len(actual_labels))
    coverage_rate = float(retained_count / total_count) if total_count else 0.0

    if retained_count == 0:
        retained_accuracy = None
        retained_macro_f1 = None
        retained_weighted_f1 = None
    else:
        retained_actual = actual_labels.loc[retained_mask].reset_index(drop=True)
        retained_predicted = predicted_labels.loc[retained_mask].reset_index(drop=True)
        retained_accuracy = float(accuracy_score(retained_actual, retained_predicted))
        retained_macro_f1 = float(
            f1_score(
                retained_actual,
                retained_predicted,
                labels=label_order,
                average="macro",
                zero_division=0,
            )
        )
        retained_weighted_f1 = float(
            f1_score(
                retained_actual,
                retained_predicted,
                labels=label_order,
                average="weighted",
                zero_division=0,
            )
        )

    meets_gate = (
        retained_accuracy is not None
        and retained_macro_f1 is not None
        and retained_weighted_f1 is not None
        and coverage_rate >= required_coverage_rate
        and retained_accuracy >= required_retained_accuracy
        and retained_macro_f1 >= baseline_macro_f1
        and retained_weighted_f1 >= baseline_weighted_f1
    )
    return {
        "policy_name": policy_name,
        "abstention_mode": abstention_mode,
        "score_threshold": score_threshold,
        "margin_threshold": margin_threshold,
        "retained_row_count": retained_count,
        "coverage_rate": coverage_rate,
        "retained_accuracy": retained_accuracy,
        "retained_macro_f1": retained_macro_f1,
        "retained_weighted_f1": retained_weighted_f1,
        "baseline_macro_f1": baseline_macro_f1,
        "baseline_weighted_f1": baseline_weighted_f1,
        "meets_promotion_gate": meets_gate,
    }


def _select_recommended_policy(
    *,
    threshold_sweep: pd.DataFrame,
    required_retained_accuracy: float,
    required_coverage_rate: float,
) -> dict[str, object]:
    eligible = threshold_sweep.loc[threshold_sweep["meets_promotion_gate"]].copy()
    if not eligible.empty:
        best_row = eligible.iloc[0]
        decision = "promote"
        next_action = "promote_to_phase10"
        reasons = [
            "At least one abstention policy clears the retained-accuracy and coverage gates.",
            "The retained macro_f1 and weighted_f1 stay above the Phase 7 uncalibrated champion.",
        ]
    else:
        fallback = threshold_sweep.loc[
            threshold_sweep["coverage_rate"] >= required_coverage_rate
        ].copy()
        if not fallback.empty:
            fallback = fallback.sort_values(
                by=["retained_accuracy", "retained_macro_f1", "coverage_rate"],
                ascending=[False, False, False],
                na_position="last",
            ).reset_index(drop=True)
            best_row = fallback.iloc[0]
            decision = "hold_for_phase9"
            next_action = "hold_for_phase9"
            reasons = [
                "Calibration found a policy with workable coverage, but it still misses the full promotion gate.",
                (
                    "Phase 9 pseudo-label expansion is required before a governed production re-run."
                ),
            ]
        else:
            best_row = threshold_sweep.iloc[0]
            decision = "reject"
            next_action = "recalibrate_again"
            reasons = [
                "No abstention policy reaches the minimum safe coverage gate.",
                "The current champion is not trustworthy enough for autonomous promotion.",
            ]

    return {
        "promotion_decision": decision,
        "next_action": next_action,
        "decision_reasons": reasons,
        "recommended_policy_name": str(best_row["policy_name"]),
        "recommended_abstention_mode": str(best_row["abstention_mode"]),
        "recommended_score_threshold": float(best_row["score_threshold"]),
        "recommended_margin_threshold": float(best_row["margin_threshold"]),
        "retained_row_count": int(best_row["retained_row_count"]),
        "coverage_rate": float(best_row["coverage_rate"]),
        "retained_accuracy": (
            float(best_row["retained_accuracy"])
            if pd.notna(best_row["retained_accuracy"])
            else None
        ),
        "retained_macro_f1": (
            float(best_row["retained_macro_f1"])
            if pd.notna(best_row["retained_macro_f1"])
            else None
        ),
        "retained_weighted_f1": (
            float(best_row["retained_weighted_f1"])
            if pd.notna(best_row["retained_weighted_f1"])
            else None
        ),
    }


def _build_promotion_gate(
    *,
    recommended_policy: dict[str, object],
    config: TheoryBaselineConfig,
    model_dir: Path,
    score_calibrator_path: Path,
    root: Path,
) -> dict[str, object]:
    return {
        "promotion_decision": recommended_policy["promotion_decision"],
        "next_action": recommended_policy["next_action"],
        "decision_reasons": recommended_policy["decision_reasons"],
        "recommended_policy_name": recommended_policy["recommended_policy_name"],
        "recommended_abstention_mode": recommended_policy["recommended_abstention_mode"],
        "recommended_score_threshold": recommended_policy["recommended_score_threshold"],
        "recommended_margin_threshold": recommended_policy["recommended_margin_threshold"],
        "required_retained_accuracy": config.evaluation.required_retained_accuracy,
        "required_coverage_rate": config.evaluation.required_coverage_rate,
        "retained_row_count": recommended_policy["retained_row_count"],
        "coverage_rate": recommended_policy["coverage_rate"],
        "retained_accuracy": recommended_policy["retained_accuracy"],
        "retained_macro_f1": recommended_policy["retained_macro_f1"],
        "retained_weighted_f1": recommended_policy["retained_weighted_f1"],
        "phase7_reference_run_directory": _relative_path(model_dir, root),
        "phase7_reference_macro_f1": _load_reference_metric(model_dir, "macro_f1"),
        "phase7_reference_weighted_f1": _load_reference_metric(model_dir, "weighted_f1"),
        "score_calibrator_artifact": _relative_path(score_calibrator_path, root),
    }


def _build_calibration_summary(
    *,
    model_manifest: dict[str, object],
    calibrator_summary: dict[str, object],
    val_correct: pd.Series,
    val_scores: pd.Series,
    val_scores_calibrated: pd.Series,
    test_actual: pd.Series,
    test_predictions: pd.Series,
    test_scores_raw: pd.Series,
    test_scores_calibrated: pd.Series,
    recommended_policy: dict[str, object],
    promotion_gate: dict[str, object],
    imbalance_policy_comparison: pd.DataFrame,
) -> dict[str, object]:
    test_correct = (test_actual.reset_index(drop=True) == test_predictions).astype(int)
    best_imbalance_row = (
        imbalance_policy_comparison.sort_values(
            by=["macro_f1", "weighted_f1", "accuracy"],
            ascending=[False, False, False],
        )
        .iloc[0]
        .to_dict()
        if not imbalance_policy_comparison.empty
        else None
    )
    return {
        "model_run_id": model_manifest["run_id"],
        "model_family": model_manifest["model_family"],
        "text_variant": model_manifest["text_variant"],
        "calibrator": calibrator_summary,
        "val_brier_raw": float(
            brier_score_loss(val_correct.astype(int), val_scores.astype(float))
        ),
        "val_brier_calibrated": float(
            brier_score_loss(val_correct.astype(int), val_scores_calibrated.astype(float))
        ),
        "test_brier_raw": float(
            brier_score_loss(test_correct.astype(int), test_scores_raw.astype(float))
        ),
        "test_brier_calibrated": float(
            brier_score_loss(test_correct.astype(int), test_scores_calibrated.astype(float))
        ),
        "recommended_policy_name": recommended_policy["recommended_policy_name"],
        "recommended_abstention_mode": recommended_policy["recommended_abstention_mode"],
        "recommended_score_threshold": recommended_policy["recommended_score_threshold"],
        "recommended_margin_threshold": recommended_policy["recommended_margin_threshold"],
        "promotion_decision": promotion_gate["promotion_decision"],
        "next_action": promotion_gate["next_action"],
        "decision_reasons": promotion_gate["decision_reasons"],
        "best_imbalance_strategy": best_imbalance_row,
    }


def _build_imbalance_policy_comparison(
    *,
    config: TheoryBaselineConfig,
    dataset,
    model_manifest: dict[str, object],
    text_variant: str,
    output_root: Path,
    root: Path,
) -> pd.DataFrame:
    output_root.mkdir(parents=True, exist_ok=True)
    model_family = validate_model_family(str(model_manifest["model_family"]))
    family_config = with_model_family(config, model_family)
    baseline_class_weight = model_manifest.get("config_snapshot", {}).get("training", {}).get(
        "class_weight"
    )
    strategies: list[tuple[str, str | dict[str, float] | None]] = [
        ("baseline", baseline_class_weight),
        ("balanced", "balanced"),
        ("capped_balanced", build_capped_balanced_class_weight(dataset)),
    ]

    rows: list[dict[str, object]] = []
    for strategy_name, class_weight in strategies:
        strategy_config = with_training_class_weight(family_config, class_weight)
        strategy_dir = output_root / strategy_name
        train_run_id = f"{model_family}_{strategy_name}_train"
        eval_run_id = f"{model_family}_{strategy_name}_test"
        train_theory_baseline(
            config=strategy_config,
            run_id=train_run_id,
            output_dir=strategy_dir,
            text_variant=text_variant,
            root=root,
        )
        evaluation_paths = evaluate_run(
            config=strategy_config,
            run_id=train_run_id,
            output_dir=strategy_dir,
            split_name="test",
            root=root,
        )
        metrics = json.loads(evaluation_paths["metrics_overall"].read_text(encoding="utf-8"))
        rows.append(
            {
                "strategy_name": strategy_name,
                "run_id": eval_run_id,
                "model_family": model_family,
                "text_variant": text_variant,
                "class_weight": class_weight,
                "accuracy": metrics["accuracy"],
                "macro_f1": metrics["macro_f1"],
                "weighted_f1": metrics["weighted_f1"],
                "output_dir": _relative_path(strategy_dir, root),
            }
        )
    return pd.DataFrame.from_records(rows)


def _load_reference_metric(model_dir: Path, metric_name: str) -> float:
    metrics_path = model_dir / "metrics_overall.json"
    if not metrics_path.exists():
        raise FileNotFoundError(f"Metrics artifact not found at {metrics_path}")
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    return float(metrics[metric_name])


def _resolve_calibration_run_dir(
    *,
    run_id: str,
    output_dir: str | Path | None,
    root: Path,
) -> Path:
    if output_dir is not None:
        candidate = Path(output_dir)
        if not candidate.is_absolute():
            candidate = root / candidate
        return candidate.resolve()
    return (root / "reports" / "tmp_phase8" / run_id).resolve()


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


def _build_operational_predictions_frame(
    *,
    variant_rows: pd.DataFrame,
    predicted_labels: Any,
    probabilities: Any,
    label_lookup: dict[str, str],
    run_id: str,
    text_variant: str,
) -> pd.DataFrame:
    predictions = variant_rows.loc[
        :,
        [
            "record_id",
            "source_dataset",
            "source_sheet",
            "source_path",
            "source_role",
            "title",
            "year",
            "doi",
            "merge_cluster_size",
            "merge_status",
            "keywords_available",
            "keywords_applied",
        ],
    ].copy()
    predictions["run_id"] = run_id
    predictions["text_variant"] = text_variant
    predictions["predicted_canonical_id"] = predicted_labels
    predictions["predicted_label_canonica"] = [
        label_lookup.get(predicted_label, predicted_label)
        for predicted_label in predicted_labels
    ]

    if probabilities is None:
        predictions["prediction_score"] = None
        predictions["second_prediction_score"] = None
        predictions["prediction_margin"] = None
        return predictions

    probability_frame = pd.DataFrame(probabilities)
    ranked_scores = probability_frame.apply(
        lambda row: row.sort_values(ascending=False).tolist(),
        axis=1,
    )
    predictions["prediction_score"] = [float(scores[0]) for scores in ranked_scores]
    predictions["second_prediction_score"] = [float(scores[1]) for scores in ranked_scores]
    predictions["prediction_margin"] = (
        predictions["prediction_score"] - predictions["second_prediction_score"]
    )
    return predictions


def _build_operational_summary(
    predictions_frame: pd.DataFrame,
    *,
    production_target_artifact_path: Path | None,
    root: Path,
) -> dict[str, object]:
    row_count = int(len(predictions_frame))
    prediction_score = pd.to_numeric(
        predictions_frame.get("prediction_score"),
        errors="coerce",
    )
    prediction_margin = pd.to_numeric(
        predictions_frame.get("prediction_margin"),
        errors="coerce",
    )
    return {
        "row_count": row_count,
        "source_composition": (
            predictions_frame.groupby("source_dataset", dropna=False)
            .size()
            .astype(int)
            .to_dict()
        ),
        "median_prediction_score": _series_stat(prediction_score, "median"),
        "p10_prediction_score": _quantile(prediction_score, 0.1),
        "median_prediction_margin": _series_stat(prediction_margin, "median"),
        "p10_prediction_margin": _quantile(prediction_margin, 0.1),
        "predicted_label_counts": (
            predictions_frame["predicted_canonical_id"]
            .value_counts()
            .sort_index()
            .astype(int)
            .to_dict()
        ),
        "trusted_production_artifact": (
            _relative_path(production_target_artifact_path, root)
            if production_target_artifact_path
            else None
        ),
    }


def _build_comparison_row(
    *,
    run_id: str,
    model_family: str,
    metrics: dict[str, object],
    operational_summary: dict[str, object],
    output_dir: Path,
    root: Path,
    trusted_production_artifact_path: Path | None,
) -> dict[str, object]:
    return {
        "run_id": run_id,
        "model_family": model_family,
        "text_variant": metrics.get("text_variant", ""),
        "split": metrics.get("split", ""),
        "accuracy": metrics.get("accuracy"),
        "macro_f1": metrics.get("macro_f1"),
        "weighted_f1": metrics.get("weighted_f1"),
        "operational_row_count": operational_summary.get("row_count"),
        "operational_median_prediction_score": operational_summary.get(
            "median_prediction_score"
        ),
        "operational_median_prediction_margin": operational_summary.get(
            "median_prediction_margin"
        ),
        "operational_p10_prediction_margin": operational_summary.get(
            "p10_prediction_margin"
        ),
        "trusted_production_artifact": (
            _relative_path(trusted_production_artifact_path, root)
            if trusted_production_artifact_path is not None
            else None
        ),
        "output_dir": _relative_path(output_dir, root),
    }


def _anchor_comparison_rows(
    config: TheoryBaselineConfig,
    root: Path,
) -> tuple[dict[str, object] | None, pd.DataFrame | None]:
    if config.baseline_anchor_run_dir is None:
        return None, None

    run_dir = config.baseline_anchor_run_dir
    manifest = load_run_manifest(run_dir)
    overall_metrics = json.loads(
        (run_dir / "metrics_overall.json").read_text(encoding="utf-8")
    )
    per_class_path = run_dir / "metrics_per_class.csv"
    per_class_frame = pd.read_csv(per_class_path, encoding="utf-8")
    per_class_frame.insert(0, "run_id", str(manifest["run_id"]))
    per_class_frame.insert(1, "model_family", str(manifest["model_family"]))

    operational_summary = _anchor_operational_summary(config)
    row = {
        "run_id": str(manifest["run_id"]),
        "model_family": str(manifest["model_family"]),
        "text_variant": overall_metrics.get("text_variant", manifest.get("text_variant", "")),
        "split": overall_metrics.get("split", ""),
        "accuracy": overall_metrics.get("accuracy"),
        "macro_f1": overall_metrics.get("macro_f1"),
        "weighted_f1": overall_metrics.get("weighted_f1"),
        "operational_row_count": operational_summary.get("row_count"),
        "operational_median_prediction_score": operational_summary.get(
            "median_prediction_score"
        ),
        "operational_median_prediction_margin": operational_summary.get(
            "median_prediction_margin"
        ),
        "operational_p10_prediction_margin": operational_summary.get(
            "p10_prediction_margin"
        ),
        "trusted_production_artifact": (
            _relative_path(config.trusted_production_artifact_path, root)
            if config.trusted_production_artifact_path is not None
            else None
        ),
        "output_dir": _relative_path(run_dir, root),
    }
    return row, per_class_frame


def _anchor_operational_summary(config: TheoryBaselineConfig) -> dict[str, object]:
    if (
        config.baseline_anchor_predictions_path is None
        or config.trusted_experiment_artifact_path is None
    ):
        return {}

    trusted_rows = pd.read_csv(config.trusted_experiment_artifact_path, encoding="utf-8")
    baseline_predictions = pd.read_csv(
        config.baseline_anchor_predictions_path,
        encoding="utf-8",
    )
    filtered = baseline_predictions.loc[
        baseline_predictions["record_id"].isin(set(trusted_rows["record_id"].tolist()))
    ].copy()
    if filtered.empty:
        return {}

    score_series = pd.to_numeric(filtered.get("prediction_score"), errors="coerce")
    margin_series = pd.to_numeric(filtered.get("prediction_margin"), errors="coerce")
    return {
        "row_count": int(len(filtered)),
        "median_prediction_score": _series_stat(score_series, "median"),
        "median_prediction_margin": _series_stat(margin_series, "median"),
        "p10_prediction_margin": _quantile(margin_series, 0.1),
    }


def _series_stat(series: pd.Series, stat: str) -> float | None:
    clean = series.dropna()
    if clean.empty:
        return None
    if stat == "median":
        return float(clean.median())
    raise ValueError(f"Unsupported stat: {stat}")


def _quantile(series: pd.Series, q: float) -> float | None:
    clean = series.dropna()
    if clean.empty:
        return None
    return float(clean.quantile(q))


def _relative_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _empirical_quantile_lower(values: list[float], q: float) -> float:
    if not values:
        raise ValueError("Cannot compute empirical quantile from an empty list.")
    ordered = sorted(float(value) for value in values)
    if len(ordered) == 1:
        return ordered[0]
    q_clamped = min(max(float(q), 0.0), 1.0)
    index = int(q_clamped * (len(ordered) - 1))
    return float(ordered[index])
