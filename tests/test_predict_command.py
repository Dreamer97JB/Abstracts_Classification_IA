from __future__ import annotations

from pathlib import Path

import pandas as pd


def test_predict_command_writes_phase5_inference_bundle(
    cli_runner,
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "predict_smoke"

    result = cli_runner(
        "predict",
        "--run-id",
        "smoke_phase5",
        "--model-run-dir",
        "reports/tmp_phase3/train_smoke",
        "--output-dir",
        str(output_dir),
        "--source-datasets",
        "scopus_base",
        "--row-limit",
        "20",
    )

    assert result.returncode == 0, result.stderr
    predictions_path = output_dir / "predictions.csv"
    low_confidence_path = output_dir / "low_confidence_review.csv"
    conflict_path = output_dir / "taxonomy_conflict_review.csv"
    insufficient_path = output_dir / "insufficient_theory_signal_review.csv"
    out_of_scope_path = output_dir / "out_of_scope_theory_review.csv"
    overlap_path = output_dir / "overlap_manual_review.csv"
    review_priority_high_path = output_dir / "review_priority_high.csv"
    review_priority_medium_path = output_dir / "review_priority_medium.csv"
    review_pack_manifest_path = output_dir / "review_pack_manifest.json"
    production_readiness_path = output_dir / "production_readiness_summary.json"

    assert predictions_path.exists()
    assert low_confidence_path.exists()
    assert conflict_path.exists()
    assert insufficient_path.exists()
    assert out_of_scope_path.exists()
    assert overlap_path.exists()
    assert review_priority_high_path.exists()
    assert review_priority_medium_path.exists()
    assert review_pack_manifest_path.exists()
    assert production_readiness_path.exists()

    predictions = pd.read_csv(predictions_path)
    assert {
        "predicted_canonical_id",
        "predicted_label_canonica",
        "prediction_score",
        "second_predicted_canonical_id",
        "second_prediction_score",
        "needs_review",
        "review_reason",
        "review_state",
        "ood_outlier_score",
        "ood_signal_flags",
        "model_run_id",
        "prediction_run_id",
        "calibrated_prediction_score",
        "review_opposition_risk",
        "abstention_policy_name",
        "delivery_tier",
        "abstained",
        "applied_score_threshold",
        "applied_margin_threshold",
    } <= set(predictions.columns)
    assert len(predictions) > 0
    assert set(predictions["delivery_tier"].unique()) <= {
        "auto_ready",
        "review_priority_high",
        "review_priority_medium",
        "defer_untrusted",
    }
    assert set(predictions["review_state"].unique()) <= {
        "auto_classified",
        "needs_review",
        "insufficient_theory_signal",
        "out_of_scope_theory",
    }
    if predictions["review_opposition_risk"].any():
        risky = predictions.loc[predictions["review_opposition_risk"]]
        assert (risky["review_state"] != "auto_classified").all()
