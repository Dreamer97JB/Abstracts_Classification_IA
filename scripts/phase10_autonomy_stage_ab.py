from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


OPPOSITION_PAIRS = {
    frozenset(("tipo_1_realismo_fuerte", "tipo_6_constructivismo_fuerte_relativismo")),
    frozenset(("tipo_1_realismo_fuerte", "tipo_5_constructivismo_moderado")),
    frozenset(("tipo_2_realismo_moderado_critico", "tipo_6_constructivismo_fuerte_relativismo")),
    frozenset(("tipo_2_realismo_moderado_critico", "tipo_5_constructivismo_moderado")),
}


def _is_opposition(left: str, right: str) -> bool:
    if not left or not right:
        return False
    return frozenset((left, right)) in OPPOSITION_PAIRS


def _to_bool(series: pd.Series) -> pd.Series:
    return (
        series.astype(str)
        .str.strip()
        .str.lower()
        .isin({"true", "1", "yes", "y", "si", "sí"})
    )


def run(
    champion_predictions: Path,
    challenger_predictions: Path,
    output_dir: Path,
    *,
    recoverable_min_calibrated: float = 0.35,
    recoverable_min_margin: float = 0.04,
    recoverable_max_margin: float = 0.18,
) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)

    champ = pd.read_csv(champion_predictions)
    challenger = pd.read_csv(challenger_predictions)

    challenger = challenger[["record_id", "predicted_canonical_id"]].rename(
        columns={"predicted_canonical_id": "challenger_predicted_canonical_id"}
    )
    frame = champ.merge(challenger, on="record_id", how="left")

    review_mask = _to_bool(frame["needs_review"]) if "needs_review" in frame.columns else pd.Series(False, index=frame.index)
    low_conf = _to_bool(frame["review_low_confidence"]) if "review_low_confidence" in frame.columns else pd.Series(False, index=frame.index)
    tax_conf = _to_bool(frame["review_taxonomy_conflict"]) if "review_taxonomy_conflict" in frame.columns else pd.Series(False, index=frame.index)
    opp_risk = _to_bool(frame["review_opposition_risk"]) if "review_opposition_risk" in frame.columns else pd.Series(False, index=frame.index)

    first_label = frame["predicted_canonical_id"].fillna("").astype(str)
    second_label = frame.get("second_predicted_canonical_id", pd.Series("", index=frame.index)).fillna("").astype(str)
    opposition_top2 = pd.Series(
        (_is_opposition(a, b) for a, b in zip(first_label, second_label)),
        index=frame.index,
    )

    cal = pd.to_numeric(frame.get("calibrated_prediction_score"), errors="coerce").fillna(0.0)
    margin = pd.to_numeric(frame.get("prediction_margin"), errors="coerce").fillna(0.0)

    high_risk_mask = review_mask & (opp_risk | opposition_top2 | tax_conf)
    nonrisk_review_mask = review_mask & (~high_risk_mask) & (~tax_conf) & (~opp_risk)
    recoverable_mask = nonrisk_review_mask & (cal >= 0.18)
    unresolved_mask = review_mask & (~high_risk_mask) & (~recoverable_mask)
    risky_auto_mask = (~review_mask) & (opp_risk | opposition_top2)

    frame["review_bucket"] = "auto_ok"
    frame.loc[risky_auto_mask, "review_bucket"] = "auto_opposition_hold"
    frame.loc[high_risk_mask, "review_bucket"] = "review_high_risk"
    frame.loc[recoverable_mask, "review_bucket"] = "review_recoverable"
    frame.loc[unresolved_mask, "review_bucket"] = "review_unresolved"

    agreement_mask = (
        recoverable_mask
        & frame["challenger_predicted_canonical_id"].fillna("").astype(str).eq(first_label)
    )
    margin_strong_mask = recoverable_mask & (~agreement_mask) & (cal >= 0.45) & (margin >= 0.06)

    frame["autonomy_resolution_method"] = "existing_auto_classified"
    frame.loc[review_mask, "autonomy_resolution_method"] = "manual_queue"
    frame.loc[risky_auto_mask, "autonomy_resolution_method"] = "opposition_hold"
    frame.loc[agreement_mask, "autonomy_resolution_method"] = "auto_agreement"
    frame.loc[margin_strong_mask, "autonomy_resolution_method"] = "auto_margin_recovery"

    frame["final_single_label_id"] = first_label
    frame["final_single_label"] = frame.get("predicted_label_canonica", first_label)
    frame["final_label_status"] = "final_auto"
    frame.loc[risky_auto_mask, "final_label_status"] = "review_required"
    frame.loc[review_mask, "final_label_status"] = "review_required"
    frame.loc[agreement_mask | margin_strong_mask, "final_label_status"] = "final_auto_recovered"

    frame["autonomy_opposition_risk"] = opposition_top2 | opp_risk

    split_cols = [
        "record_id",
        "title",
        "predicted_canonical_id",
        "second_predicted_canonical_id",
        "calibrated_prediction_score",
        "prediction_margin",
        "needs_review",
        "review_bucket",
        "review_reason",
    ]
    split_cols = [c for c in split_cols if c in frame.columns]
    review_split = frame[split_cols].copy()
    review_split.to_csv(output_dir / "review_split.csv", index=False, encoding="utf-8")

    autonomous_cols = [
        "record_id",
        "title",
        "predicted_canonical_id",
        "predicted_label_canonica",
        "second_predicted_canonical_id",
        "second_predicted_label_canonica",
        "calibrated_prediction_score",
        "prediction_margin",
        "review_bucket",
        "autonomy_resolution_method",
        "final_single_label_id",
        "final_single_label",
        "final_label_status",
        "autonomy_opposition_risk",
    ]
    autonomous_cols = [c for c in autonomous_cols if c in frame.columns]
    autonomous = frame[autonomous_cols].copy()
    autonomous.to_csv(output_dir / "client_results_autonomous_v1.csv", index=False, encoding="utf-8")

    metrics = {
        "total_rows": int(len(frame)),
        "review_rows_before": int(review_mask.sum()),
        "review_rows_before_rate": float(review_mask.mean()) if len(frame) else 0.0,
        "review_bucket_counts": frame["review_bucket"].value_counts(dropna=False).to_dict(),
        "recovered_auto_count": int((agreement_mask | margin_strong_mask).sum()),
        "remaining_review_count": int((frame["final_label_status"] == "review_required").sum()),
        "remaining_review_rate": float((frame["final_label_status"] == "review_required").mean()) if len(frame) else 0.0,
        "autonomy_resolution_method_counts": frame["autonomy_resolution_method"].value_counts(dropna=False).to_dict(),
        "auto_with_opposition_risk_count": int(
            (
                frame["final_label_status"].isin(["final_auto", "final_auto_recovered"])
                & frame["autonomy_opposition_risk"].astype(bool)
            ).sum()
        ),
    }
    (output_dir / "autonomy_stage_ab_metrics.json").write_text(
        json.dumps(metrics, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    report_lines = [
        "# Phase 10 Autonomy Stage A+B Report",
        "",
        f"- Total rows: {metrics['total_rows']}",
        f"- Review before: {metrics['review_rows_before']} ({metrics['review_rows_before_rate']:.2%})",
        f"- Recovered auto: {metrics['recovered_auto_count']}",
        f"- Remaining review: {metrics['remaining_review_count']} ({metrics['remaining_review_rate']:.2%})",
        f"- Auto with opposition risk: {metrics['auto_with_opposition_risk_count']}",
        "",
        "## Review Bucket Counts",
    ]
    for key, value in metrics["review_bucket_counts"].items():
        report_lines.append(f"- {key}: {value}")
    report_lines.append("")
    report_lines.append("## Resolution Methods")
    for key, value in metrics["autonomy_resolution_method_counts"].items():
        report_lines.append(f"- {key}: {value}")
    (output_dir / "AUTONOMY_STAGE_AB_REPORT.md").write_text(
        "\n".join(report_lines) + "\n",
        encoding="utf-8",
    )

    return metrics


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Phase 10 autonomy Stage A+B workflow.")
    parser.add_argument("--champion-predictions", required=True)
    parser.add_argument("--challenger-predictions", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    metrics = run(
        champion_predictions=Path(args.champion_predictions),
        challenger_predictions=Path(args.challenger_predictions),
        output_dir=Path(args.output_dir),
    )
    print(json.dumps(metrics, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
