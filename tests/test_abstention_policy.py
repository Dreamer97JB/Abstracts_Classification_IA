from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def test_predict_command_persists_abstention_artifacts(
    cli_runner,
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "predict_abstention_smoke"

    result = cli_runner(
        "predict",
        "--run-id",
        "smoke_phase8_predict",
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

    predictions = pd.read_csv(output_dir / "predictions.csv")
    assert {
        "calibrated_prediction_score",
        "delivery_tier",
        "abstained",
        "applied_score_threshold",
        "applied_margin_threshold",
        "abstention_mode",
    } <= set(predictions.columns)
    assert len(predictions) > 0

    production_readiness_summary = json.loads(
        (output_dir / "production_readiness_summary.json").read_text(encoding="utf-8")
    )
    assert {
        "auto_ready_count",
        "auto_ready_rate",
        "review_priority_high_count",
        "review_priority_medium_count",
        "defer_untrusted_count",
        "phase5_client_ready_count",
        "phase5_client_review_required_count",
        "review_reduction_vs_phase5",
    } <= set(production_readiness_summary)

    review_pack_manifest = json.loads(
        (output_dir / "review_pack_manifest.json").read_text(encoding="utf-8")
    )
    assert review_pack_manifest["recommended_high_priority_cap"] == 250
    assert review_pack_manifest["recommended_medium_priority_cap"] == 500
