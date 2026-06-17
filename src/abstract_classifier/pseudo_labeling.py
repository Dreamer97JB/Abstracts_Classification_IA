from __future__ import annotations

import json
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .client_micro_review import (
    REVIEW_OUTCOME_INSUFFICIENT,
    REVIEW_OUTCOME_OUT_OF_SCOPE,
    build_weak_signal_artifacts,
    load_client_micro_review_feedback,
)
from .evaluation import derive_conformal_admission_summary
from .taxonomy import ROOT, resolve_project_path


@dataclass(frozen=True)
class PseudoLabelTomlSettings:
    trusted_source_artifact: Path
    prediction_artifact: Path
    promotion_gate_artifact: Path
    preferred_source_order: tuple[str, ...]
    minimum_abstract_words: int
    minimum_abstract_characters: int
    minimum_calibrated_prediction_score: float
    minimum_prediction_margin: float
    fallback_score_threshold: float
    fallback_margin_threshold: float
    weak_class_score_threshold: float
    weak_class_margin_threshold: float
    minimum_admitted_rows: int
    max_global_class_share: float
    pseudo_label_wave_id: str
    teacher_run_id: str
    gold_supervision_artifact: Path
    split_artifact: Path
    metrics_per_class_artifact: Path
    # Optional 9E: second model must agree on predicted_canonical_id (same record_id).
    secondary_prediction_artifact: Path | None
    secondary_teacher_run_id: str | None
    require_cross_model_agreement: bool
    # Optional: restrict rows to these source_dataset values (empty = no filter).
    allowed_source_datasets: tuple[str, ...]
    # Optional 9F: after row-level admission, keep at most this many rows per predicted class.
    admission_top_k_per_class: int | None
    # Optional 09-03: reviewed client micro-pack with non-canonical outcomes.
    client_review_feedback_artifact: Path | None
    excluded_review_outcomes: tuple[str, ...]
    admission_policy_version: str
    enable_conformal_gate: bool
    conformal_reference_predictions_artifact: Path | None
    conformal_alpha: float
    conformal_minimum_correct_rows: int


def load_pseudo_label_settings(
    path: str | Path,
    *,
    root: Path | None = None,
) -> PseudoLabelTomlSettings:
    project_root = root or ROOT
    config_path = resolve_project_path(path, root=project_root)
    data = tomllib.loads(config_path.read_text(encoding="utf-8"))

    preferred = tuple(str(x) for x in data.get("preferred_source_order", []))
    if not preferred:
        raise ValueError("theory_pseudo_label.toml must declare preferred_source_order.")

    sec_art_raw = data.get("secondary_prediction_artifact")
    secondary_prediction_artifact = (
        resolve_project_path(sec_art_raw, root=project_root) if sec_art_raw else None
    )
    sec_run_raw = data.get("secondary_teacher_run_id")
    secondary_teacher_run_id = str(sec_run_raw).strip() if sec_run_raw else None
    require_cross = bool(data.get("require_cross_model_agreement", False))
    if require_cross and not secondary_teacher_run_id:
        raise ValueError(
            "require_cross_model_agreement is true but secondary_teacher_run_id is missing."
        )
    allowed_src = tuple(str(x).strip() for x in data.get("allowed_source_datasets", []) if str(x).strip())
    excluded_review_outcomes = tuple(
        str(x).strip() for x in data.get("excluded_review_outcomes", []) if str(x).strip()
    )
    top_k_raw = data.get("admission_top_k_per_class")
    admission_top_k: int | None
    if top_k_raw is None:
        admission_top_k = None
    else:
        tk = int(top_k_raw)
        admission_top_k = tk if tk > 0 else None
    review_art_raw = data.get("client_review_feedback_artifact")
    review_artifact = resolve_project_path(review_art_raw, root=project_root) if review_art_raw else None
    conformal_ref_raw = data.get("conformal_reference_predictions_artifact")
    conformal_ref_artifact = (
        resolve_project_path(conformal_ref_raw, root=project_root)
        if conformal_ref_raw
        else None
    )

    return PseudoLabelTomlSettings(
        trusted_source_artifact=resolve_project_path(
            data["trusted_source_artifact"], root=project_root
        ),
        prediction_artifact=resolve_project_path(data["prediction_artifact"], root=project_root),
        promotion_gate_artifact=resolve_project_path(
            data["promotion_gate_artifact"], root=project_root
        ),
        preferred_source_order=preferred,
        minimum_abstract_words=int(data["minimum_abstract_words"]),
        minimum_abstract_characters=int(data["minimum_abstract_characters"]),
        minimum_calibrated_prediction_score=float(data["minimum_calibrated_prediction_score"]),
        minimum_prediction_margin=float(data["minimum_prediction_margin"]),
        fallback_score_threshold=float(data["fallback_score_threshold"]),
        fallback_margin_threshold=float(data["fallback_margin_threshold"]),
        weak_class_score_threshold=float(data["weak_class_score_threshold"]),
        weak_class_margin_threshold=float(data["weak_class_margin_threshold"]),
        minimum_admitted_rows=int(data["minimum_admitted_rows"]),
        max_global_class_share=float(data["max_global_class_share"]),
        pseudo_label_wave_id=str(data["pseudo_label_wave_id"]),
        teacher_run_id=str(data["teacher_run_id"]),
        gold_supervision_artifact=resolve_project_path(
            data["gold_supervision_artifact"], root=project_root
        ),
        split_artifact=resolve_project_path(data["split_artifact"], root=project_root),
        metrics_per_class_artifact=resolve_project_path(
            data["metrics_per_class_artifact"], root=project_root
        ),
        secondary_prediction_artifact=secondary_prediction_artifact,
        secondary_teacher_run_id=secondary_teacher_run_id,
        require_cross_model_agreement=require_cross,
        allowed_source_datasets=allowed_src,
        admission_top_k_per_class=admission_top_k,
        client_review_feedback_artifact=review_artifact,
        excluded_review_outcomes=excluded_review_outcomes,
        admission_policy_version=str(data.get("admission_policy_version", "phase9_policy_v1")),
        enable_conformal_gate=bool(data.get("enable_conformal_gate", False)),
        conformal_reference_predictions_artifact=conformal_ref_artifact,
        conformal_alpha=float(data.get("conformal_alpha", 0.2)),
        conformal_minimum_correct_rows=int(data.get("conformal_minimum_correct_rows", 5)),
    )


def _as_bool(series: pd.Series) -> pd.Series:
    return series.astype(str).str.lower().isin(("true", "1", "yes"))


def _source_rank_frame(source: pd.Series, preferred: tuple[str, ...]) -> pd.Series:
    def rank_one(val: object) -> int:
        s = str(val).strip()
        if s in preferred:
            return preferred.index(s)
        return len(preferred) + 1

    return source.map(rank_one)


def run_governed_pseudo_label_pipeline(
    *,
    settings: PseudoLabelTomlSettings,
    output_dir: Path,
    prediction_artifact: Path | None = None,
    root: Path | None = None,
) -> dict[str, Path]:
    """Emit candidates / admitted / rejected plus quota summary and policy manifest."""
    project_root = root or ROOT
    output_dir = Path(output_dir)
    if not output_dir.is_absolute():
        output_dir = (project_root / output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    pred_path = prediction_artifact or settings.prediction_artifact
    predictions = pd.read_csv(pred_path)
    trusted = pd.read_csv(settings.trusted_source_artifact)
    gold = pd.read_csv(settings.gold_supervision_artifact)
    splits = pd.read_csv(settings.split_artifact)
    metrics_pc = pd.read_csv(settings.metrics_per_class_artifact)

    gold_ids = set(gold["record_id"].astype(str))
    trusted_ids = set(trusted["record_id"].astype(str))

    weak_classes = set(
        metrics_pc.loc[metrics_pc["f1_score"].astype(float) < 0.30, "canonical_id"]
        .astype(str)
        .tolist()
    )
    conformal_summary = None
    if settings.enable_conformal_gate:
        if settings.conformal_reference_predictions_artifact is None:
            raise ValueError(
                "enable_conformal_gate is true but conformal_reference_predictions_artifact is missing."
            )
        conformal_summary = derive_conformal_admission_summary(
            settings.conformal_reference_predictions_artifact,
            alpha=settings.conformal_alpha,
            minimum_required_correct_rows=settings.conformal_minimum_correct_rows,
        )

    teacher = settings.teacher_run_id
    pool = predictions.loc[predictions["model_run_id"].astype(str) == teacher].copy()
    if settings.allowed_source_datasets:
        pool = pool.loc[
            pool["source_dataset"].astype(str).isin(settings.allowed_source_datasets)
        ].copy()
    pool = pool.loc[~pool["record_id"].astype(str).isin(gold_ids)].copy()
    pool["teacher_run_id"] = teacher
    pool["in_trusted_corpus"] = pool["record_id"].astype(str).isin(trusted_ids)
    pool["review_outcome"] = ""
    weak_signal_summary, weak_signal_votes = build_weak_signal_artifacts(pool, root=project_root)
    pool = pool.merge(weak_signal_summary, on="record_id", how="left")
    pool["weak_signal_conflict"] = (
        pool["weak_signal_majority_canonical_id"].astype(str).ne("")
        & pool["predicted_canonical_id"].astype(str).ne(
            pool["weak_signal_majority_canonical_id"].astype(str)
        )
    )

    noncanonical_review_path = output_dir / "pseudo_label_noncanonical_review.csv"
    weak_signal_path = output_dir / "pseudo_label_weak_signals.csv"
    if settings.client_review_feedback_artifact is not None:
        review_feedback = load_client_micro_review_feedback(
            settings.client_review_feedback_artifact,
            root=project_root,
        )
        review_subset = review_feedback.loc[
            :, ["record_id", "review_outcome", "import_decision", "notas_revisor"]
        ].rename(
            columns={
                "review_outcome": "review_outcome_feedback",
                "import_decision": "review_import_decision",
                "notas_revisor": "review_notas_revisor",
            }
        )
        pool = pool.merge(review_subset, on="record_id", how="left")
        pool["review_outcome"] = pool["review_outcome_feedback"].fillna("")
        noncanonical_rows = pool.loc[
            pool["review_outcome"].astype(str).isin(
                (REVIEW_OUTCOME_OUT_OF_SCOPE, REVIEW_OUTCOME_INSUFFICIENT)
            )
        ].copy()
        noncanonical_rows.to_csv(noncanonical_review_path, index=False)
    else:
        pool["review_import_decision"] = ""
        pool["review_notas_revisor"] = ""
        pool["review_outcome_feedback"] = ""
        pd.DataFrame(
            columns=[
                "record_id",
                "review_outcome",
                "review_import_decision",
                "review_notas_revisor",
            ]
        ).to_csv(noncanonical_review_path, index=False)
    weak_signal_votes.to_csv(weak_signal_path, index=False)

    if settings.require_cross_model_agreement:
        sec_path = settings.secondary_prediction_artifact or pred_path
        sec_full = pd.read_csv(sec_path)
        if "predicted_canonical_id" not in sec_full.columns:
            raise ValueError(
                f"secondary predictions at {sec_path} must include predicted_canonical_id."
            )
        sec_run = str(settings.secondary_teacher_run_id)
        sec_sub = sec_full.loc[
            sec_full["model_run_id"].astype(str) == sec_run,
            ["record_id", "predicted_canonical_id"],
        ].rename(columns={"predicted_canonical_id": "cross_model_predicted_canonical_id"})
        sec_sub = sec_sub.drop_duplicates(subset=["record_id"])
        pool = pool.merge(sec_sub, on="record_id", how="left")

    rid = pool["record_id"].astype(str)
    outside = ~pool["in_trusted_corpus"]
    tax_conflict = _as_bool(pool["review_taxonomy_conflict"]) if "review_taxonomy_conflict" in pool.columns else pd.Series(False, index=pool.index)
    abstained = _as_bool(pool["abstained"]) if "abstained" in pool.columns else pd.Series(False, index=pool.index)
    tier = pool["delivery_tier"].astype(str).str.lower() if "delivery_tier" in pool.columns else pd.Series("", index=pool.index)
    not_auto = abstained | (tier != "auto_ready")

    abstract = pool["abstract"].fillna("").astype(str)
    if "abstract_word_count" in pool.columns:
        words = pool["abstract_word_count"].fillna(0).astype(int)
    else:
        words = abstract.str.split().str.len()
    thin = (words < settings.minimum_abstract_words) | (
        abstract.str.len() < settings.minimum_abstract_characters
    )

    score = pool["calibrated_prediction_score"].astype(float)
    margin = pool["prediction_margin"].astype(float)
    pred_label = pool["predicted_canonical_id"].astype(str)
    second = pool["second_predicted_canonical_id"] if "second_predicted_canonical_id" in pool.columns else pd.Series(np.nan, index=pool.index)
    agreement_ok = second.notna() & (pred_label == second.astype(str))

    low_conf = _as_bool(pool["review_low_confidence"]) if "review_low_confidence" in pool.columns else pd.Series(False, index=pool.index)
    excluded_review_outcomes = set(settings.excluded_review_outcomes)
    reviewed_outcome = pool["review_outcome"].astype(str)
    reviewed_out_of_scope = reviewed_outcome == REVIEW_OUTCOME_OUT_OF_SCOPE
    reviewed_insufficient = reviewed_outcome == REVIEW_OUTCOME_INSUFFICIENT
    reviewed_excluded = reviewed_outcome.isin(excluded_review_outcomes)
    model_review_state = pool["review_state"].astype(str) if "review_state" in pool.columns else pd.Series("", index=pool.index)
    model_out_of_scope = model_review_state == "out_of_scope_theory"
    model_insufficient = model_review_state == "insufficient_theory_signal"

    is_weak = pred_label.isin(weak_classes)
    need_score_std = settings.minimum_calibrated_prediction_score
    need_margin_std = settings.minimum_prediction_margin
    need_score_fb = settings.fallback_score_threshold
    need_margin_fb = settings.fallback_margin_threshold
    need_score_weak = settings.weak_class_score_threshold
    need_margin_weak = settings.weak_class_margin_threshold

    eff_score_need = np.where(
        is_weak,
        need_score_weak,
        np.where(agreement_ok, need_score_std, need_score_fb),
    )
    eff_margin_need = np.where(
        is_weak,
        need_margin_weak,
        np.where(agreement_ok, need_margin_std, need_margin_fb),
    )
    below_score = score < eff_score_need
    below_margin = margin < eff_margin_need
    weak_fail = is_weak & (below_score | below_margin)

    rejection = pd.Series(pd.NA, index=pool.index, dtype=object)
    rejection = rejection.mask(outside, "outside_trusted_corpus")
    rejection = rejection.mask(
        rejection.isna() & reviewed_out_of_scope,
        "candidate_outlier_distributional",
    )
    rejection = rejection.mask(
        rejection.isna() & reviewed_insufficient,
        "reviewed_insufficient_theory_signal",
    )
    rejection = rejection.mask(
        rejection.isna() & reviewed_excluded,
        "reviewed_noncanonical_exclusion",
    )
    rejection = rejection.mask(
        rejection.isna() & model_out_of_scope,
        "predicted_out_of_scope_theory",
    )
    rejection = rejection.mask(
        rejection.isna() & model_insufficient,
        "predicted_insufficient_theory_signal",
    )
    rejection = rejection.mask(rejection.isna() & tax_conflict, "taxonomy_conflict")
    rejection = rejection.mask(rejection.isna() & not_auto, "not_auto_ready")
    rejection = rejection.mask(rejection.isna() & thin, "thin_text")
    if settings.require_cross_model_agreement:
        sec_col = pool["cross_model_predicted_canonical_id"]
        cross_missing = sec_col.isna()
        cross_bad = sec_col.notna() & (sec_col.astype(str) != pred_label.astype(str))
        rejection = rejection.mask(rejection.isna() & cross_missing, "cross_model_missing")
        rejection = rejection.mask(rejection.isna() & cross_bad, "cross_model_disagreement")
    rejection = rejection.mask(rejection.isna() & weak_fail, "weak_class_guardrail")
    rejection = rejection.mask(rejection.isna() & low_conf, "below_score_threshold")
    rejection = rejection.mask(rejection.isna() & below_score & ~is_weak, "below_score_threshold")
    rejection = rejection.mask(rejection.isna() & below_margin & ~is_weak, "below_margin_threshold")

    pre_conformal_admitted_count = int(rejection.isna().sum())
    if conformal_summary is not None:
        conformal_nonconformity = 1.0 - score
        conformal_accept = score >= float(conformal_summary.score_threshold)
        pool["conformal_policy_name"] = conformal_summary.policy_name
        pool["conformal_alpha"] = conformal_summary.alpha
        pool["conformal_score_threshold"] = conformal_summary.score_threshold
        pool["conformal_nonconformity_threshold"] = conformal_summary.nonconformity_threshold
        pool["conformal_nonconformity_score"] = conformal_nonconformity.astype(float)
        pool["conformal_prediction_set_size"] = np.where(conformal_accept, 1, 2)
        pool["conformal_prediction_set_type"] = np.where(
            conformal_accept,
            "singleton_safe",
            "uncertain_multi",
        )
        pool["conformal_accept"] = conformal_accept
        rejection = rejection.mask(
            rejection.isna() & ~conformal_accept,
            "conformal_not_singleton_safe",
        )
    else:
        pool["conformal_policy_name"] = ""
        pool["conformal_alpha"] = np.nan
        pool["conformal_score_threshold"] = np.nan
        pool["conformal_nonconformity_threshold"] = np.nan
        pool["conformal_nonconformity_score"] = np.nan
        pool["conformal_prediction_set_size"] = np.nan
        pool["conformal_prediction_set_type"] = ""
        pool["conformal_accept"] = pd.NA

    pool["rejection_reason"] = rejection
    pool["admission_decision"] = np.where(rejection.isna(), "admitted", "rejected")
    pool["admission_reason"] = np.where(
        rejection.isna(),
        "passed_row_gates",
        rejection.astype(str),
    )

    candidate_cols = [
        "record_id",
        "teacher_run_id",
        "source_dataset",
        "delivery_tier",
        "calibrated_prediction_score",
        "prediction_margin",
        "in_trusted_corpus",
        "admission_decision",
        "admission_reason",
        "rejection_reason",
        "predicted_canonical_id",
        "predicted_label_canonica",
        "model_run_id",
        "review_outcome",
        "review_import_decision",
        "review_notas_revisor",
        "review_state",
        "ood_outlier_score",
        "ood_signal_flags",
        "weak_signal_vote_count",
        "weak_signal_distinct_rule_count",
        "weak_signal_majority_canonical_id",
        "weak_signal_majority_label",
        "weak_signal_conflict",
        "weak_signal_sources",
        "weak_signal_evidence",
        "review_low_confidence",
        "review_taxonomy_conflict",
        "abstained",
        "cross_model_predicted_canonical_id",
        "conformal_policy_name",
        "conformal_alpha",
        "conformal_score_threshold",
        "conformal_nonconformity_threshold",
        "conformal_nonconformity_score",
        "conformal_prediction_set_size",
        "conformal_prediction_set_type",
        "conformal_accept",
    ]
    present = [c for c in candidate_cols if c in pool.columns]
    candidates_path = output_dir / "pseudo_label_candidates.csv"
    export_cols = present + [c for c in ("abstract", "abstract_word_count") if c in pool.columns]
    pool.loc[:, [c for c in export_cols if c in pool.columns]].to_csv(candidates_path, index=False)
    conformal_path = output_dir / "pseudo_label_conformal_diagnostics.csv"
    conformal_cols = [
        "record_id",
        "predicted_canonical_id",
        "calibrated_prediction_score",
        "prediction_margin",
        "admission_decision",
        "rejection_reason",
        "conformal_policy_name",
        "conformal_alpha",
        "conformal_score_threshold",
        "conformal_nonconformity_threshold",
        "conformal_nonconformity_score",
        "conformal_prediction_set_size",
        "conformal_prediction_set_type",
        "conformal_accept",
    ]
    pool.loc[:, [c for c in conformal_cols if c in pool.columns]].to_csv(
        conformal_path,
        index=False,
    )

    rejected_path = output_dir / "pseudo_label_rejected.csv"
    pool.loc[pool["admission_decision"] == "rejected"].to_csv(rejected_path, index=False)

    admitted_pre = pool.loc[pool["admission_decision"] == "admitted"].copy()
    admitted_pre["source_rank"] = _source_rank_frame(
        admitted_pre["source_dataset"], settings.preferred_source_order
    )
    admitted_pre["weak_signal_supports_prediction"] = (
        admitted_pre["weak_signal_majority_canonical_id"].astype(str).ne("")
        & admitted_pre["weak_signal_majority_canonical_id"].astype(str).eq(
            admitted_pre["predicted_canonical_id"].astype(str)
        )
    )
    admitted_pre = admitted_pre.sort_values(
        by=[
            "source_rank",
            "weak_signal_supports_prediction",
            "prediction_margin",
            "calibrated_prediction_score",
        ],
        ascending=[True, False, False, False],
    )

    if settings.admission_top_k_per_class is not None and not admitted_pre.empty:
        k = int(settings.admission_top_k_per_class)
        trimmed_topk: list[pd.DataFrame] = []
        for _, grp in admitted_pre.groupby(
            admitted_pre["predicted_canonical_id"].astype(str), sort=False
        ):
            trimmed_topk.append(grp.head(k))
        admitted_pre = pd.concat(trimmed_topk, axis=0).sort_values(
            by=[
                "source_rank",
                "weak_signal_supports_prediction",
                "prediction_margin",
                "calibrated_prediction_score",
            ],
            ascending=[True, False, False, False],
        )

    gold_train = gold.merge(
        splits.loc[:, ["record_id", "split"]],
        on="record_id",
        how="inner",
    )
    gold_train = gold_train.loc[gold_train["split"].astype(str).str.lower() == "train"]
    gold_train_counts = gold_train.groupby("canonical_id").size().to_dict()

    quota_rows: list[dict[str, Any]] = []
    trimmed_parts: list[pd.DataFrame] = []
    if admitted_pre.empty:
        admitted = admitted_pre
        for cid in sorted(gold_train_counts.keys()):
            quota_rows.append(
                {
                    "canonical_id": cid,
                    "gold_train_count": int(gold_train_counts[cid]),
                    "candidate_count": 0,
                    "admitted_count": 0,
                    "trimmed_count": 0,
                }
            )
    else:
        for cid in admitted_pre["predicted_canonical_id"].astype(str).unique():
            cls_rows = admitted_pre.loc[admitted_pre["predicted_canonical_id"].astype(str) == cid]
            cap = min(120, 2 * int(gold_train_counts.get(cid, 0)))
            candidate_count = len(cls_rows)
            if cap <= 0:
                trimmed = cls_rows.iloc[0:0]
            else:
                trimmed = cls_rows.head(cap)
            trimmed_parts.append(trimmed)
            quota_rows.append(
                {
                    "canonical_id": cid,
                    "gold_train_count": int(gold_train_counts.get(cid, 0)),
                    "candidate_count": candidate_count,
                    "admitted_count": len(trimmed),
                    "trimmed_count": max(0, candidate_count - len(trimmed)),
                }
            )
        for cid, gcount in gold_train_counts.items():
            if cid not in admitted_pre["predicted_canonical_id"].astype(str).tolist():
                quota_rows.append(
                    {
                        "canonical_id": cid,
                        "gold_train_count": int(gcount),
                        "candidate_count": 0,
                        "admitted_count": 0,
                        "trimmed_count": 0,
                    }
                )
        admitted = pd.concat(trimmed_parts, axis=0).sort_values(
            by=[
                "source_rank",
                "weak_signal_supports_prediction",
                "prediction_margin",
                "calibrated_prediction_score",
            ],
            ascending=[True, False, False, False],
        )

    quota_path = output_dir / "pseudo_label_class_quota_summary.csv"
    pd.DataFrame(quota_rows).drop_duplicates(subset=["canonical_id"]).sort_values("canonical_id").to_csv(
        quota_path, index=False
    )

    max_share = settings.max_global_class_share
    if len(admitted) > 0:
        for _ in range(100_000):
            cls_counts = admitted.groupby(admitted["predicted_canonical_id"].astype(str)).size()
            share = cls_counts / len(admitted)
            over = share[share > max_share]
            if over.empty:
                break
            worst_cls = str(over.idxmax())
            cls_mask = admitted["predicted_canonical_id"].astype(str) == worst_cls
            cls_df = admitted.loc[cls_mask].sort_values(
                by=["source_rank", "prediction_margin", "calibrated_prediction_score"],
                ascending=[True, False, False],
            )
            drop_rid = str(cls_df.iloc[-1]["record_id"])
            admitted = admitted.loc[admitted["record_id"].astype(str) != drop_rid].copy()
        else:
            raise RuntimeError("Global class-share trimming did not converge.")

    trusted_key = trusted.drop_duplicates(subset=["record_id"]).set_index("record_id")
    admitted_path = output_dir / "pseudo_label_admitted.csv"
    if admitted.empty:
        pd.DataFrame(
            columns=[
                "record_id",
                "teacher_run_id",
                "source_dataset",
                "delivery_tier",
                "calibrated_prediction_score",
                "prediction_margin",
                "canonical_id",
                "label_canonica",
                "pseudo_label_wave_id",
                "supervision_source",
            ]
        ).to_csv(admitted_path, index=False)
    else:
        merged_rows: list[pd.Series] = []
        for _, row in admitted.iterrows():
            rid = str(row["record_id"])
            base = row.copy()
            if rid in trusted_key.index:
                trow = trusted_key.loc[rid]
                if isinstance(trow, pd.DataFrame):
                    trow = trow.iloc[0]
                for col in ("title", "year", "doi", "source_sheet", "journal", "authors"):
                    if col in trow.index and (col not in base.index or pd.isna(base.get(col))):
                        base[col] = trow[col]
            merged_rows.append(base)
        out_admitted = pd.DataFrame(merged_rows)
        out_admitted["canonical_id"] = out_admitted["predicted_canonical_id"].astype(str)
        out_admitted["label_canonica"] = out_admitted["predicted_label_canonica"]
        if "label_original" not in out_admitted.columns:
            out_admitted["label_original"] = out_admitted["label_canonica"]
        out_admitted["pseudo_label_wave_id"] = settings.pseudo_label_wave_id
        out_admitted["supervision_source"] = "pseudo_label"
        out_admitted.to_csv(admitted_path, index=False)

    final_status = (
        "ready_for_retraining"
        if len(admitted) >= settings.minimum_admitted_rows
        else "insufficient_safe_candidates"
    )
    post_conformal_admitted_count = int((pool["admission_decision"] == "admitted").sum())

    policy: dict[str, Any] = {
        "policy_version": settings.admission_policy_version,
        "pseudo_label_wave_id": settings.pseudo_label_wave_id,
        "teacher_run_id": settings.teacher_run_id,
        "minimum_admitted_rows": settings.minimum_admitted_rows,
        "preferred_source_order": list(settings.preferred_source_order),
        "thresholds": {
            "minimum_calibrated_prediction_score": settings.minimum_calibrated_prediction_score,
            "minimum_prediction_margin": settings.minimum_prediction_margin,
            "fallback_score_threshold": settings.fallback_score_threshold,
            "fallback_margin_threshold": settings.fallback_margin_threshold,
            "weak_class_score_threshold": settings.weak_class_score_threshold,
            "weak_class_margin_threshold": settings.weak_class_margin_threshold,
        },
        "max_global_class_share": settings.max_global_class_share,
        "final_status": final_status,
        "admitted_row_count": int(len(admitted)),
        "raw_row_gate_admitted_count": pre_conformal_admitted_count,
        "conformal_admitted_count": post_conformal_admitted_count,
        "promotion_gate_artifact": str(settings.promotion_gate_artifact),
        "prediction_artifact": str(pred_path),
        "trusted_source_artifact": str(settings.trusted_source_artifact),
        "admission_options": {
            "require_cross_model_agreement": settings.require_cross_model_agreement,
            "secondary_teacher_run_id": settings.secondary_teacher_run_id,
            "secondary_prediction_artifact": str(settings.secondary_prediction_artifact)
            if settings.secondary_prediction_artifact
            else None,
            "allowed_source_datasets": list(settings.allowed_source_datasets),
            "admission_top_k_per_class": settings.admission_top_k_per_class,
            "client_review_feedback_artifact": str(settings.client_review_feedback_artifact)
            if settings.client_review_feedback_artifact
            else None,
            "excluded_review_outcomes": list(settings.excluded_review_outcomes),
            "enable_conformal_gate": settings.enable_conformal_gate,
            "conformal_reference_predictions_artifact": str(
                settings.conformal_reference_predictions_artifact
            )
            if settings.conformal_reference_predictions_artifact
            else None,
            "conformal_alpha": settings.conformal_alpha,
            "conformal_minimum_correct_rows": settings.conformal_minimum_correct_rows,
        },
        "conformal_policy": (
            conformal_summary.to_dict() if conformal_summary is not None else None
        ),
        "rejection_state_vocabulary": [
            "outside_trusted_corpus",
            "candidate_outlier_distributional",
            "reviewed_insufficient_theory_signal",
            "reviewed_noncanonical_exclusion",
            "predicted_out_of_scope_theory",
            "predicted_insufficient_theory_signal",
            "taxonomy_conflict",
            "not_auto_ready",
            "thin_text",
            "cross_model_missing",
            "cross_model_disagreement",
            "weak_class_guardrail",
            "below_score_threshold",
            "below_margin_threshold",
            "conformal_not_singleton_safe",
            "weak_signal_conflict",
        ],
    }
    policy_path = output_dir / "pseudo_label_policy.json"
    policy_path.write_text(json.dumps(policy, indent=2, ensure_ascii=False), encoding="utf-8")

    return {
        "candidates": candidates_path,
        "admitted": admitted_path,
        "rejected": rejected_path,
        "policy": policy_path,
        "quota": quota_path,
        "noncanonical_review": noncanonical_review_path,
        "conformal": conformal_path,
        "weak_signals": weak_signal_path,
    }
