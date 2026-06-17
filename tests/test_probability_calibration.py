from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def test_calibrate_command_writes_phase8_bundle(
    cli_runner,
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "calibration_smoke"

    result = cli_runner(
        "calibrate",
        "--run-id",
        "smoke_phase8",
        "--model-run-dir",
        "reports/tmp_phase3/train_smoke",
        "--output-dir",
        str(output_dir),
    )

    assert result.returncode == 0, result.stderr

    reliability_table_path = output_dir / "reliability_table.csv"
    threshold_sweep_path = output_dir / "threshold_sweep.csv"
    promotion_gate_path = output_dir / "promotion_gate.json"
    calibration_summary_path = output_dir / "calibration_summary.json"
    manifest_path = output_dir / "calibration_manifest.json"
    imbalance_policy_comparison_path = output_dir / "imbalance_policy_comparison.csv"
    score_calibrator_path = output_dir / "score_calibrator.joblib"

    for artifact_path in (
        reliability_table_path,
        threshold_sweep_path,
        promotion_gate_path,
        calibration_summary_path,
        manifest_path,
        imbalance_policy_comparison_path,
        score_calibrator_path,
    ):
        assert artifact_path.exists(), artifact_path

    threshold_sweep = pd.read_csv(threshold_sweep_path)
    assert {
        "policy_name",
        "score_threshold",
        "margin_threshold",
        "coverage_rate",
        "retained_accuracy",
        "retained_macro_f1",
        "retained_weighted_f1",
    } <= set(threshold_sweep.columns)

    promotion_gate = json.loads(promotion_gate_path.read_text(encoding="utf-8"))
    assert {
        "promotion_decision",
        "decision_reasons",
        "recommended_policy_name",
        "required_retained_accuracy",
        "required_coverage_rate",
    } <= set(promotion_gate)

    calibration_summary = json.loads(
        calibration_summary_path.read_text(encoding="utf-8")
    )
    assert (
        calibration_summary["recommended_policy_name"]
        == promotion_gate["recommended_policy_name"]
    )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["artifacts"]["promotion_gate"] == "promotion_gate.json"
