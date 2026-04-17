from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def test_evaluate_command_writes_metrics_bundle_with_taxonomy_order(
    cli_runner,
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "eval_run"
    train_result = cli_runner(
        "train",
        "--config",
        "configs/theory_baseline.toml",
        "--run-id",
        "eval_train",
        "--output-dir",
        str(output_dir),
    )
    assert train_result.returncode == 0, train_result.stderr

    evaluate_result = cli_runner(
        "evaluate",
        "--config",
        "configs/theory_baseline.toml",
        "--run-id",
        "eval_train",
        "--output-dir",
        str(output_dir),
    )

    assert evaluate_result.returncode == 0, evaluate_result.stderr

    overall_metrics = json.loads((output_dir / "metrics_overall.json").read_text(encoding="utf-8"))
    per_class_metrics = pd.read_csv(output_dir / "metrics_per_class.csv")
    confusion = pd.read_csv(output_dir / "confusion_matrix.csv", index_col=0)
    predictions = pd.read_csv(output_dir / "predictions.csv")

    assert overall_metrics["split"] == "test"
    assert overall_metrics["split_version"] == "phase2_v1"
    assert {"accuracy", "macro_f1", "weighted_f1"} <= set(overall_metrics)

    expected_order = [
        "tipo_1_realismo_fuerte",
        "tipo_2_realismo_moderado_critico",
        "tipo_3_antirrealismo_epistemologico",
        "tipo_4_pragmatismo_epistemologico",
        "tipo_5_constructivismo_moderado",
        "tipo_6_constructivismo_fuerte_relativismo",
    ]
    assert per_class_metrics["canonical_id"].tolist() == expected_order
    assert confusion.index.tolist() == expected_order
    assert confusion.columns.tolist() == expected_order
    assert {
        "record_id",
        "canonical_id",
        "predicted_canonical_id",
        "prediction_score",
        "text_variant",
    } <= set(predictions.columns)
