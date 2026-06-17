from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass
from pathlib import Path

import joblib
import pandas as pd

from .contracts import NormalizedSourceRow
from .io.sources import load_normalized_rows
from .overlap import OverlapOutcome, build_overlap_decisions, completeness_score
from .taxonomy import ROOT, load_taxonomy, resolve_project_path
from .text_variants import build_text_variant_frame, summarize_keyword_coverage
from .training import load_run_manifest, load_trained_pipeline

DEFAULT_THEORY_INFERENCE_CONFIG = Path("configs/theory_inference.toml")
_OPPOSITION_RIGHT = {"tipo_5_constructivismo_moderado", "tipo_6_constructivismo_fuerte_relativismo"}


@dataclass(frozen=True)
class InferenceReviewSettings:
    low_confidence_threshold: float
    conflict_margin_threshold: float
    abstention_policy_name: str
    score_threshold: float
    margin_threshold: float
    abstention_mode: str
    insufficient_signal_ood_threshold: float
    out_of_scope_ood_threshold: float
    out_of_scope_score_threshold: float
    out_of_scope_margin_threshold: float
    taxonomy_conflict_pairs: tuple[frozenset[str], ...]


@dataclass(frozen=True)
class TheoryInferenceConfig:
    version: str
    config_path: Path
    source_manifest_path: Path
    default_output_root: Path
    default_source_datasets: tuple[str, ...]
    trusted_production_artifact_path: Path | None
    promotion_gate_artifact_path: Path | None
    review: InferenceReviewSettings


@dataclass(frozen=True)
class AppliedAbstentionPolicy:
    policy_name: str
    score_threshold: float
    margin_threshold: float
    abstention_mode: str
    promotion_decision: str
    next_action: str
    calibrator_artifact_path: Path | None


@dataclass(frozen=True)
class InferenceCorpusBundle:
    corpus_frame: pd.DataFrame
    merge_decisions_frame: pd.DataFrame
    overlap_review_frame: pd.DataFrame


@dataclass(frozen=True)
class InferenceRunArtifacts:
    run_dir: Path
    manifest_path: Path
    inference_input_path: Path
    merge_decisions_path: Path
    overlap_review_path: Path
    predictions_path: Path
    low_confidence_review_path: Path
    taxonomy_conflict_review_path: Path
    insufficient_theory_signal_review_path: Path
    out_of_scope_theory_review_path: Path
    review_priority_high_path: Path
    review_priority_medium_path: Path
    review_pack_manifest_path: Path
    production_readiness_summary_path: Path
    summary_path: Path


def load_theory_inference_config(
    path: str | Path = DEFAULT_THEORY_INFERENCE_CONFIG,
    *,
    root: Path | None = None,
) -> TheoryInferenceConfig:
    project_root = root or ROOT
    config_path = resolve_project_path(path, root=project_root)
    data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    review_data = data.get("review", {})

    taxonomy_conflict_pairs = tuple(
        frozenset((str(item["left"]), str(item["right"])))
        for item in data.get("taxonomy_conflict_pairs", [])
    )

    return TheoryInferenceConfig(
        version=str(data.get("version", "")),
        config_path=config_path,
        source_manifest_path=resolve_project_path(
            data["source_manifest"],
            root=project_root,
        ),
        default_output_root=resolve_project_path(
            data["default_output_root"],
            root=project_root,
        ),
        default_source_datasets=tuple(str(item) for item in data.get("default_source_datasets", [])),
        trusted_production_artifact_path=_optional_resolved_path(
            data.get("trusted_production_artifact"),
            root=project_root,
        ),
        promotion_gate_artifact_path=_optional_resolved_path(
            data.get("promotion_gate_artifact"),
            root=project_root,
        ),
        review=InferenceReviewSettings(
            low_confidence_threshold=float(review_data.get("low_confidence_threshold", 0.45)),
            conflict_margin_threshold=float(review_data.get("conflict_margin_threshold", 0.08)),
            abstention_policy_name=str(
                review_data.get("abstention_policy_name", "default_phase5_review_gate")
            ).strip(),
            score_threshold=float(review_data.get("score_threshold", 0.45)),
            margin_threshold=float(review_data.get("margin_threshold", 0.08)),
            abstention_mode=str(review_data.get("abstention_mode", "score_and_margin")).strip(),
            insufficient_signal_ood_threshold=float(
                review_data.get("insufficient_signal_ood_threshold", 0.60)
            ),
            out_of_scope_ood_threshold=float(
                review_data.get("out_of_scope_ood_threshold", 0.85)
            ),
            out_of_scope_score_threshold=float(
                review_data.get("out_of_scope_score_threshold", 0.25)
            ),
            out_of_scope_margin_threshold=float(
                review_data.get("out_of_scope_margin_threshold", 0.03)
            ),
            taxonomy_conflict_pairs=taxonomy_conflict_pairs,
        ),
    )


def run_batch_inference(
    *,
    config: TheoryInferenceConfig,
    run_id: str,
    model_run_dir: str | Path,
    output_dir: str | Path | None = None,
    source_datasets: tuple[str, ...] | None = None,
    row_limit: int | None = None,
    root: Path | None = None,
) -> InferenceRunArtifacts:
    project_root = root or ROOT
    effective_sources = source_datasets or config.default_source_datasets
    if not effective_sources:
        raise ValueError("At least one source_dataset must be selected for inference.")

    model_dir = resolve_project_path(model_run_dir, root=project_root)
    model_manifest = load_run_manifest(model_dir)
    pipeline = load_trained_pipeline(model_dir)
    applied_policy = _load_abstention_policy(config, root=project_root)
    taxonomy = load_taxonomy(
        model_manifest["inputs"]["taxonomy_config"],
        root=project_root,
    )
    model_text_variant = str(model_manifest["text_variant"])

    corpus_bundle = _load_inference_corpus_bundle(
        config=config,
        source_datasets=effective_sources,
        row_limit=row_limit,
        text_variant=model_text_variant,
        root=project_root,
    )
    variant_rows = corpus_bundle.corpus_frame
    keyword_coverage = summarize_keyword_coverage(variant_rows, text_variant=model_text_variant)

    if not hasattr(pipeline, "predict_proba"):
        raise ValueError("The configured model does not expose predict_proba().")

    probabilities = pipeline.predict_proba(variant_rows["text_input"])
    class_ids = list(pipeline.classes_)
    predictions = _build_predictions_frame(
        variant_rows=variant_rows,
        probabilities=probabilities,
        class_ids=class_ids,
        taxonomy=taxonomy,
        config=config,
        run_id=run_id,
        model_manifest=model_manifest,
        model_run_dir=model_dir,
        keyword_coverage=keyword_coverage.to_dict(),
        applied_policy=applied_policy,
    )

    run_dir = _resolve_inference_run_dir(
        config=config,
        run_id=run_id,
        output_dir=output_dir,
        root=project_root,
    )
    run_dir.mkdir(parents=True, exist_ok=True)

    inference_input_path = run_dir / "inference_input.csv"
    merge_decisions_path = run_dir / "merge_decisions.csv"
    overlap_review_path = run_dir / "overlap_manual_review.csv"
    predictions_path = run_dir / "predictions.csv"
    low_confidence_review_path = run_dir / "low_confidence_review.csv"
    taxonomy_conflict_review_path = run_dir / "taxonomy_conflict_review.csv"
    insufficient_theory_signal_review_path = run_dir / "insufficient_theory_signal_review.csv"
    out_of_scope_theory_review_path = run_dir / "out_of_scope_theory_review.csv"
    review_priority_high_path = run_dir / "review_priority_high.csv"
    review_priority_medium_path = run_dir / "review_priority_medium.csv"
    review_pack_manifest_path = run_dir / "review_pack_manifest.json"
    production_readiness_summary_path = run_dir / "production_readiness_summary.json"
    summary_path = run_dir / "corpus_summary.json"
    manifest_path = run_dir / "prediction_manifest.json"

    corpus_bundle.corpus_frame.to_csv(inference_input_path, index=False, encoding="utf-8")
    corpus_bundle.merge_decisions_frame.to_csv(
        merge_decisions_path,
        index=False,
        encoding="utf-8",
    )
    corpus_bundle.overlap_review_frame.to_csv(
        overlap_review_path,
        index=False,
        encoding="utf-8",
    )
    predictions.to_csv(predictions_path, index=False, encoding="utf-8")
    predictions.loc[predictions["review_low_confidence"]].to_csv(
        low_confidence_review_path,
        index=False,
        encoding="utf-8",
    )
    predictions.loc[predictions["review_taxonomy_conflict"]].to_csv(
        taxonomy_conflict_review_path,
        index=False,
        encoding="utf-8",
    )
    predictions.loc[
        predictions["review_state"].astype(str) == "insufficient_theory_signal"
    ].to_csv(
        insufficient_theory_signal_review_path,
        index=False,
        encoding="utf-8",
    )
    predictions.loc[
        predictions["review_state"].astype(str) == "out_of_scope_theory"
    ].to_csv(
        out_of_scope_theory_review_path,
        index=False,
        encoding="utf-8",
    )
    review_priority_high = _build_review_priority_frame(predictions, "review_priority_high")
    review_priority_medium = _build_review_priority_frame(predictions, "review_priority_medium")
    review_priority_high.to_csv(review_priority_high_path, index=False, encoding="utf-8")
    review_priority_medium.to_csv(review_priority_medium_path, index=False, encoding="utf-8")

    summary = _build_inference_summary(
        predictions=predictions,
        corpus_bundle=corpus_bundle,
        keyword_coverage=keyword_coverage.to_dict(),
        source_datasets=effective_sources,
        row_limit=row_limit,
        applied_policy=applied_policy,
    )
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    production_readiness_summary = _build_production_readiness_summary(
        predictions=predictions,
        applied_policy=applied_policy,
        root=project_root,
    )
    production_readiness_summary_path.write_text(
        json.dumps(production_readiness_summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    review_pack_manifest = _build_review_pack_manifest(
        applied_policy=applied_policy,
        review_priority_high=review_priority_high,
        review_priority_medium=review_priority_medium,
    )
    review_pack_manifest_path.write_text(
        json.dumps(review_pack_manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    manifest = {
        "run_id": run_id,
        "config_version": config.version,
        "config_path": _relative_path(config.config_path, project_root),
        "model_run_id": model_manifest["run_id"],
        "model_run_directory": _relative_path(model_dir, project_root),
        "model_text_variant": model_text_variant,
        "selected_source_datasets": list(effective_sources),
        "row_limit": row_limit,
        "review_thresholds": {
            "low_confidence_threshold": config.review.low_confidence_threshold,
            "conflict_margin_threshold": config.review.conflict_margin_threshold,
            "abstention_policy_name": applied_policy.policy_name,
            "score_threshold": applied_policy.score_threshold,
            "margin_threshold": applied_policy.margin_threshold,
            "abstention_mode": applied_policy.abstention_mode,
            "insufficient_signal_ood_threshold": config.review.insufficient_signal_ood_threshold,
            "out_of_scope_ood_threshold": config.review.out_of_scope_ood_threshold,
            "out_of_scope_score_threshold": config.review.out_of_scope_score_threshold,
            "out_of_scope_margin_threshold": config.review.out_of_scope_margin_threshold,
            "taxonomy_conflict_pairs": [sorted(pair) for pair in config.review.taxonomy_conflict_pairs],
        },
        "artifacts": {
            "inference_input": inference_input_path.name,
            "merge_decisions": merge_decisions_path.name,
            "overlap_manual_review": overlap_review_path.name,
            "predictions": predictions_path.name,
            "low_confidence_review": low_confidence_review_path.name,
            "taxonomy_conflict_review": taxonomy_conflict_review_path.name,
            "insufficient_theory_signal_review": insufficient_theory_signal_review_path.name,
            "out_of_scope_theory_review": out_of_scope_theory_review_path.name,
            "review_priority_high": review_priority_high_path.name,
            "review_priority_medium": review_priority_medium_path.name,
            "review_pack_manifest": review_pack_manifest_path.name,
            "production_readiness_summary": production_readiness_summary_path.name,
            "summary": summary_path.name,
        },
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return InferenceRunArtifacts(
        run_dir=run_dir,
        manifest_path=manifest_path,
        inference_input_path=inference_input_path,
        merge_decisions_path=merge_decisions_path,
        overlap_review_path=overlap_review_path,
        predictions_path=predictions_path,
        low_confidence_review_path=low_confidence_review_path,
        taxonomy_conflict_review_path=taxonomy_conflict_review_path,
        insufficient_theory_signal_review_path=insufficient_theory_signal_review_path,
        out_of_scope_theory_review_path=out_of_scope_theory_review_path,
        review_priority_high_path=review_priority_high_path,
        review_priority_medium_path=review_priority_medium_path,
        review_pack_manifest_path=review_pack_manifest_path,
        production_readiness_summary_path=production_readiness_summary_path,
        summary_path=summary_path,
    )


def assemble_inference_corpus(rows: list[NormalizedSourceRow]) -> InferenceCorpusBundle:
    decisions = build_overlap_decisions(rows)
    merge_decisions = [
        decision
        for decision in decisions
        if decision.outcome in {OverlapOutcome.MERGE_DOI, OverlapOutcome.MERGE_TITLE_YEAR}
    ]
    review_decisions = [
        decision for decision in decisions if decision.outcome == OverlapOutcome.MANUAL_REVIEW
    ]

    parent = {row.record_id: row.record_id for row in rows}

    def find(item: str) -> str:
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    def union(left: str, right: str) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    for decision in merge_decisions:
        union(decision.left.record_id, decision.right.record_id)

    clusters: dict[str, list[NormalizedSourceRow]] = {}
    for row in rows:
        clusters.setdefault(find(row.record_id), []).append(row)

    record_to_winner: dict[str, str] = {}
    cluster_records: list[dict[str, object]] = []
    for cluster_rows in clusters.values():
        winner = _select_cluster_winner(cluster_rows)
        merged_record_ids = sorted(row.record_id for row in cluster_rows)
        merged_source_datasets = sorted(set(row.source_dataset for row in cluster_rows))
        cluster_outcomes = sorted(
            {
                decision.outcome.value
                for decision in merge_decisions
                if decision.left.record_id in merged_record_ids
                or decision.right.record_id in merged_record_ids
            }
        )
        for row in cluster_rows:
            record_to_winner[row.record_id] = winner.record_id
        record = winner.to_dict()
        record["canonical_id"] = ""
        record["label_canonica"] = ""
        record["merge_cluster_size"] = len(cluster_rows)
        record["merge_status"] = "exact_merged" if len(cluster_rows) > 1 else "unique"
        record["merged_record_ids"] = " | ".join(merged_record_ids)
        record["merged_source_datasets"] = " | ".join(merged_source_datasets)
        record["merge_methods"] = " | ".join(cluster_outcomes)
        cluster_records.append(record)

    merge_decisions_frame = pd.DataFrame.from_records(
        [decision.to_dict() for decision in merge_decisions]
    )
    overlap_review_frame = pd.DataFrame.from_records(
        [decision.to_dict() for decision in review_decisions]
    )
    if not overlap_review_frame.empty:
        overlap_review_frame["left_winner_record_id"] = overlap_review_frame["left_record_id"].map(
            record_to_winner
        )
        overlap_review_frame["right_winner_record_id"] = overlap_review_frame["right_record_id"].map(
            record_to_winner
        )

    return InferenceCorpusBundle(
        corpus_frame=pd.DataFrame.from_records(cluster_records).sort_values(
            by=["source_dataset", "record_id"]
        ).reset_index(drop=True),
        merge_decisions_frame=merge_decisions_frame,
        overlap_review_frame=overlap_review_frame,
    )


def _select_cluster_winner(cluster_rows: list[NormalizedSourceRow]) -> NormalizedSourceRow:
    return min(
        cluster_rows,
        key=lambda row: (
            -completeness_score(row),
            0 if row.source_system == "scopus" else 1,
            row.record_id,
        ),
    )


def _build_predictions_frame(
    *,
    variant_rows: pd.DataFrame,
    probabilities,
    class_ids: list[str],
    taxonomy,
    config: TheoryInferenceConfig,
    run_id: str,
    model_manifest: dict[str, object],
    model_run_dir: Path,
    keyword_coverage: dict[str, object],
    applied_policy: AppliedAbstentionPolicy,
) -> pd.DataFrame:
    label_lookup = {
        taxonomy_class.identifier: taxonomy_class.label for taxonomy_class in taxonomy.classes
    }
    probability_frame = pd.DataFrame(probabilities, columns=class_ids)
    ranked_class_ids = probability_frame.apply(
        lambda row: row.sort_values(ascending=False).index.tolist(),
        axis=1,
    )
    ranked_scores = probability_frame.apply(
        lambda row: row.sort_values(ascending=False).tolist(),
        axis=1,
    )

    predictions = variant_rows.drop(columns=["text_input"], errors="ignore").copy()
    predictions["prediction_run_id"] = run_id
    predictions["model_run_id"] = str(model_manifest["run_id"])
    predictions["model_config_version"] = str(model_manifest.get("config_version", ""))
    predictions["model_family"] = str(model_manifest.get("model_family", ""))
    predictions["model_run_directory"] = str(model_run_dir)
    predictions["predicted_canonical_id"] = [labels[0] for labels in ranked_class_ids]
    predictions["predicted_label_canonica"] = [
        label_lookup[label_id] for label_id in predictions["predicted_canonical_id"]
    ]
    predictions["prediction_score"] = [float(scores[0]) for scores in ranked_scores]
    predictions["second_predicted_canonical_id"] = [labels[1] for labels in ranked_class_ids]
    predictions["second_predicted_label_canonica"] = [
        label_lookup[label_id] for label_id in predictions["second_predicted_canonical_id"]
    ]
    predictions["second_prediction_score"] = [float(scores[1]) for scores in ranked_scores]
    predictions["prediction_margin"] = (
        predictions["prediction_score"] - predictions["second_prediction_score"]
    )
    predictions["calibrated_prediction_score"] = _apply_score_calibrator(
        predictions["prediction_score"],
        applied_policy.calibrator_artifact_path,
    )
    predictions["review_low_confidence"] = (
        predictions["calibrated_prediction_score"] < config.review.low_confidence_threshold
    )
    predictions["review_taxonomy_conflict"] = predictions.apply(
        lambda row: frozenset(
            (row["predicted_canonical_id"], row["second_predicted_canonical_id"])
        )
        in config.review.taxonomy_conflict_pairs
        and row["prediction_margin"] <= config.review.conflict_margin_threshold,
        axis=1,
    )
    predictions["review_opposition_risk"] = predictions.apply(
        lambda row: _is_opposition_risk(
            str(row.get("predicted_canonical_id", "") or ""),
            str(row.get("second_predicted_canonical_id", "") or ""),
        ),
        axis=1,
    )
    predictions["needs_review"] = (
        predictions["review_low_confidence"]
        | predictions["review_taxonomy_conflict"]
        | predictions["review_opposition_risk"]
    )
    predictions["abstention_policy_name"] = applied_policy.policy_name
    predictions["applied_score_threshold"] = applied_policy.score_threshold
    predictions["applied_margin_threshold"] = applied_policy.margin_threshold
    predictions["abstention_mode"] = applied_policy.abstention_mode
    predictions["delivery_tier"] = predictions.apply(
        lambda row: _assign_delivery_tier(row, applied_policy),
        axis=1,
    )
    predictions["abstained"] = predictions["delivery_tier"] != "auto_ready"
    predictions["needs_review"] = predictions["needs_review"] | predictions["abstained"]
    predictions["ood_outlier_score"] = predictions.apply(
        lambda row: _compute_ood_outlier_score(row, config),
        axis=1,
    )
    predictions["ood_signal_flags"] = predictions.apply(_compose_ood_signal_flags, axis=1)
    predictions["review_state"] = predictions.apply(
        lambda row: _assign_review_state(row, config),
        axis=1,
    )
    predictions["needs_review"] = predictions["review_state"].astype(str) != "auto_classified"
    predictions["review_reason"] = predictions.apply(_compose_review_reason, axis=1)
    predictions["keyword_availability_rate"] = keyword_coverage["keyword_availability_rate"]
    predictions["keyword_coverage_rate"] = keyword_coverage["keyword_coverage_rate"]
    return predictions


def _compose_review_reason(row: pd.Series) -> str:
    reasons: list[str] = []
    review_state = str(row.get("review_state", "") or "")
    if review_state and review_state != "auto_classified":
        reasons.append(review_state)
    if bool(row["review_low_confidence"]):
        reasons.append("low_confidence")
    if bool(row["review_taxonomy_conflict"]):
        reasons.append("taxonomy_conflict")
    if bool(row.get("review_opposition_risk", False)):
        reasons.append("opposition_risk_2_vs_5_6")
    if bool(row.get("abstained", False)):
        reasons.append(str(row.get("delivery_tier", "abstained")))
    ood_flags = str(row.get("ood_signal_flags", "") or "").strip()
    if ood_flags:
        reasons.append(ood_flags)
    return " | ".join(reasons)


def _build_inference_summary(
    *,
    predictions: pd.DataFrame,
    corpus_bundle: InferenceCorpusBundle,
    keyword_coverage: dict[str, object],
    source_datasets: tuple[str, ...],
    row_limit: int | None,
    applied_policy: AppliedAbstentionPolicy,
) -> dict[str, object]:
    label_counts = (
        predictions["predicted_label_canonica"].value_counts().sort_index().to_dict()
    )
    return {
        "source_datasets": list(source_datasets),
        "row_limit": row_limit,
        "inference_row_count": int(len(predictions)),
        "exact_merge_decision_count": int(len(corpus_bundle.merge_decisions_frame)),
        "manual_overlap_review_count": int(len(corpus_bundle.overlap_review_frame)),
        "low_confidence_review_count": int(predictions["review_low_confidence"].sum()),
        "taxonomy_conflict_review_count": int(predictions["review_taxonomy_conflict"].sum()),
        "opposition_risk_review_count": int(predictions["review_opposition_risk"].sum()),
        "abstained_count": int(predictions["abstained"].sum()),
        "auto_ready_count": int((predictions["delivery_tier"] == "auto_ready").sum()),
        "review_state_counts": (
            predictions["review_state"].astype(str).value_counts().sort_index().astype(int).to_dict()
            if "review_state" in predictions.columns
            else {}
        ),
        "abstention_policy_name": applied_policy.policy_name,
        "label_counts": label_counts,
        "keyword_coverage": keyword_coverage,
    }


def _load_inference_corpus_bundle(
    *,
    config: TheoryInferenceConfig,
    source_datasets: tuple[str, ...],
    row_limit: int | None,
    text_variant: str,
    root: Path,
) -> InferenceCorpusBundle:
    if config.trusted_production_artifact_path is not None:
        corpus_frame = pd.read_csv(config.trusted_production_artifact_path, encoding="utf-8")
        if source_datasets:
            corpus_frame = corpus_frame.loc[
                corpus_frame["source_dataset"].isin(set(source_datasets))
            ].copy()
        if row_limit is not None:
            corpus_frame = corpus_frame.head(row_limit).copy()
        if corpus_frame.empty:
            raise ValueError(
                "No trusted production rows matched the selected source_datasets: "
                f"{source_datasets}"
            )
        variant_rows = build_text_variant_frame(
            corpus_frame,
            text_variant=text_variant,
            text_metadata=None,
        )
        return InferenceCorpusBundle(
            corpus_frame=variant_rows.reset_index(drop=True),
            merge_decisions_frame=pd.DataFrame(),
            overlap_review_frame=pd.DataFrame(),
        )

    raw_rows = load_normalized_rows(
        config.source_manifest_path,
        project_root=root,
        row_limit=row_limit,
    )
    selected_rows = [
        row
        for row in raw_rows
        if row.source_role == "corpus" and row.source_dataset in source_datasets
    ]
    if not selected_rows:
        raise ValueError(
            "No governed corpus rows matched the selected source_datasets: "
            f"{source_datasets}"
        )
    corpus_bundle = assemble_inference_corpus(selected_rows)
    variant_rows = build_text_variant_frame(
        corpus_bundle.corpus_frame,
        text_variant=text_variant,
        text_metadata=None,
    )
    return InferenceCorpusBundle(
        corpus_frame=variant_rows.reset_index(drop=True),
        merge_decisions_frame=corpus_bundle.merge_decisions_frame,
        overlap_review_frame=corpus_bundle.overlap_review_frame,
    )


def _load_abstention_policy(
    config: TheoryInferenceConfig,
    *,
    root: Path,
) -> AppliedAbstentionPolicy:
    gate_path = config.promotion_gate_artifact_path
    if gate_path is not None and gate_path.exists():
        gate = json.loads(gate_path.read_text(encoding="utf-8"))
        calibrator_artifact = gate.get("score_calibrator_artifact")
        calibrator_path = (
            resolve_project_path(calibrator_artifact, root=root)
            if calibrator_artifact
            else None
        )
        return AppliedAbstentionPolicy(
            policy_name=str(gate.get("recommended_policy_name", config.review.abstention_policy_name)),
            score_threshold=float(gate.get("recommended_score_threshold", config.review.score_threshold)),
            margin_threshold=float(gate.get("recommended_margin_threshold", config.review.margin_threshold)),
            abstention_mode=str(gate.get("recommended_abstention_mode", config.review.abstention_mode)),
            promotion_decision=str(gate.get("promotion_decision", "reject")),
            next_action=str(gate.get("next_action", "recalibrate_again")),
            calibrator_artifact_path=calibrator_path,
        )

    return AppliedAbstentionPolicy(
        policy_name=config.review.abstention_policy_name,
        score_threshold=config.review.score_threshold,
        margin_threshold=config.review.margin_threshold,
        abstention_mode=config.review.abstention_mode,
        promotion_decision="reject",
        next_action="recalibrate_again",
        calibrator_artifact_path=None,
    )


def _apply_score_calibrator(
    scores: pd.Series,
    calibrator_artifact_path: Path | None,
) -> pd.Series:
    if calibrator_artifact_path is None or not calibrator_artifact_path.exists():
        return scores.astype(float)
    calibrator = joblib.load(calibrator_artifact_path)
    calibrated = calibrator.predict(scores.astype(float).tolist())
    return pd.Series(calibrated, index=scores.index, dtype="float64")


def _assign_delivery_tier(
    row: pd.Series,
    policy: AppliedAbstentionPolicy,
) -> str:
    calibrated_score = float(row["calibrated_prediction_score"])
    margin = float(row["prediction_margin"])
    passes_score = calibrated_score >= policy.score_threshold
    passes_margin = margin >= policy.margin_threshold
    if policy.abstention_mode == "score_only":
        auto_ready = passes_score
    elif policy.abstention_mode == "margin_only":
        auto_ready = passes_margin
    else:
        auto_ready = passes_score and passes_margin
    if (
        auto_ready
        and not bool(row["review_taxonomy_conflict"])
        and not bool(row.get("review_opposition_risk", False))
    ):
        return "auto_ready"
    if calibrated_score >= (policy.score_threshold - 0.05):
        return "review_priority_high"
    if calibrated_score >= 0.35 or margin >= max(policy.margin_threshold / 2.0, 0.02):
        return "review_priority_medium"
    return "defer_untrusted"


def _compute_ood_outlier_score(
    row: pd.Series,
    config: TheoryInferenceConfig,
) -> float:
    calibrated_score = float(row.get("calibrated_prediction_score", 0.0) or 0.0)
    margin = float(row.get("prediction_margin", 0.0) or 0.0)
    score_floor = max(config.review.low_confidence_threshold, 1e-6)
    margin_floor = max(config.review.conflict_margin_threshold, 1e-6)

    score_component = min(max((score_floor - calibrated_score) / score_floor, 0.0), 1.0)
    margin_component = min(max((margin_floor - margin) / margin_floor, 0.0), 1.0)
    keyword_component = 0.0 if bool(row.get("keywords_available", False)) else 1.0

    abstract_text = str(row.get("abstract", "") or "").strip()
    abstract_words = len(abstract_text.split()) if abstract_text else 0
    thin_text = abstract_words < 80 or len(abstract_text) < 400
    thin_text_component = 1.0 if thin_text else 0.0

    score = (
        0.45 * score_component
        + 0.30 * margin_component
        + 0.15 * keyword_component
        + 0.10 * thin_text_component
    )
    return float(round(score, 6))


def _compose_ood_signal_flags(row: pd.Series) -> str:
    flags: list[str] = []
    calibrated_score = float(row.get("calibrated_prediction_score", 0.0) or 0.0)
    margin = float(row.get("prediction_margin", 0.0) or 0.0)
    if calibrated_score < 0.25:
        flags.append("very_low_score")
    elif calibrated_score < 0.45:
        flags.append("low_score")
    if margin < 0.03:
        flags.append("very_low_margin")
    elif margin < 0.08:
        flags.append("low_margin")
    if not bool(row.get("keywords_available", False)):
        flags.append("keywords_missing")
    abstract_text = str(row.get("abstract", "") or "").strip()
    if len(abstract_text) < 400 or len(abstract_text.split()) < 80:
        flags.append("thin_text")
    return " | ".join(flags)


def _assign_review_state(
    row: pd.Series,
    config: TheoryInferenceConfig,
) -> str:
    if str(row.get("delivery_tier", "")) == "auto_ready" and not bool(row.get("review_taxonomy_conflict", False)):
        return "auto_classified"

    ood_score = float(row.get("ood_outlier_score", 0.0) or 0.0)
    calibrated_score = float(row.get("calibrated_prediction_score", 0.0) or 0.0)
    margin = float(row.get("prediction_margin", 0.0) or 0.0)

    if not bool(row.get("review_taxonomy_conflict", False)):
        if (
            ood_score >= config.review.out_of_scope_ood_threshold
            and calibrated_score < config.review.out_of_scope_score_threshold
            and margin < config.review.out_of_scope_margin_threshold
        ):
            return "out_of_scope_theory"
        if (
            (bool(row.get("review_low_confidence", False)) or bool(row.get("abstained", False)))
            and ood_score >= config.review.insufficient_signal_ood_threshold
        ):
            return "insufficient_theory_signal"

    return "needs_review"


def _is_opposition_risk(predicted_id: str, second_id: str) -> bool:
    """High-risk boundary from expert guidance: 2 versus 5/6."""
    pred = predicted_id.strip()
    second = second_id.strip()
    return (
        (pred == "tipo_2_realismo_moderado_critico" and second in _OPPOSITION_RIGHT)
        or (second == "tipo_2_realismo_moderado_critico" and pred in _OPPOSITION_RIGHT)
    )


def _build_review_priority_frame(predictions: pd.DataFrame, tier: str) -> pd.DataFrame:
    return (
        predictions.loc[predictions["delivery_tier"] == tier]
        .sort_values(by=["prediction_margin", "calibrated_prediction_score"], ascending=[True, True])
        .reset_index(drop=True)
    )


def _build_production_readiness_summary(
    *,
    predictions: pd.DataFrame,
    applied_policy: AppliedAbstentionPolicy,
    root: Path,
) -> dict[str, object]:
    phase5_summary_path = root / "reports" / "phase5" / "full_corpus_analysis" / "client_reporting_summary.json"
    phase5_summary = (
        json.loads(phase5_summary_path.read_text(encoding="utf-8"))
        if phase5_summary_path.exists()
        else {}
    )
    phase5_review_required = int(
        phase5_summary.get("review_counts", {}).get("client_review_required", 0)
    )
    phase5_client_ready = int(
        phase5_summary.get("review_counts", {}).get("client_ready", 0)
    )
    high_count = int((predictions["delivery_tier"] == "review_priority_high").sum())
    medium_count = int((predictions["delivery_tier"] == "review_priority_medium").sum())
    defer_count = int((predictions["delivery_tier"] == "defer_untrusted").sum())
    auto_ready_count = int((predictions["delivery_tier"] == "auto_ready").sum())
    expert_review_queue_count = high_count + medium_count
    return {
        "abstention_policy_name": applied_policy.policy_name,
        "promotion_decision": applied_policy.promotion_decision,
        "next_action": applied_policy.next_action,
        "auto_ready_count": auto_ready_count,
        "auto_ready_rate": float(auto_ready_count / len(predictions)) if len(predictions) else 0.0,
        "review_priority_high_count": high_count,
        "review_priority_medium_count": medium_count,
        "defer_untrusted_count": defer_count,
        "phase5_client_ready_count": phase5_client_ready,
        "phase5_client_review_required_count": phase5_review_required,
        "expert_review_queue_count": expert_review_queue_count,
        "review_reduction_vs_phase5": int(phase5_review_required - expert_review_queue_count),
        "review_state_counts": (
            predictions["review_state"].astype(str).value_counts().sort_index().astype(int).to_dict()
            if "review_state" in predictions.columns
            else {}
        ),
    }


def _build_review_pack_manifest(
    *,
    applied_policy: AppliedAbstentionPolicy,
    review_priority_high: pd.DataFrame,
    review_priority_medium: pd.DataFrame,
) -> dict[str, object]:
    if applied_policy.promotion_decision == "promote":
        next_action = "promote_to_phase10"
    elif applied_policy.promotion_decision == "hold_for_phase9":
        next_action = "hold_for_phase9"
    else:
        next_action = "recalibrate_again"
    return {
        "abstention_policy_name": applied_policy.policy_name,
        "promotion_decision": applied_policy.promotion_decision,
        "next_action": next_action,
        "recommended_high_priority_cap": 250,
        "recommended_medium_priority_cap": 500,
        "available_high_priority_rows": int(len(review_priority_high)),
        "available_medium_priority_rows": int(len(review_priority_medium)),
        "rationale": "Phase 8 minimizes expert dependence by limiting review to the narrowest uncertainty band.",
    }


def _resolve_inference_run_dir(
    *,
    config: TheoryInferenceConfig,
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


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_resolved_path(value: object, *, root: Path) -> Path | None:
    path_value = _optional_string(value)
    if path_value is None:
        return None
    return resolve_project_path(path_value, root=root)


def _relative_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())
