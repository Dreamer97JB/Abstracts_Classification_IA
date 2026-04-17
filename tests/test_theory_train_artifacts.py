from __future__ import annotations

import json
from pathlib import Path


def test_train_command_persists_manifest_and_model_artifacts(
    cli_runner,
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "train_run"
    result = cli_runner(
        "train",
        "--config",
        "configs/theory_baseline.toml",
        "--run-id",
        "unit_train",
        "--output-dir",
        str(output_dir),
    )

    assert result.returncode == 0, result.stderr
    assert (output_dir / "model.joblib").exists()
    assert (output_dir / "run_manifest.json").exists()
    assert (output_dir / "keyword_coverage.json").exists()

    manifest = json.loads((output_dir / "run_manifest.json").read_text(encoding="utf-8"))

    assert manifest["run_id"] == "unit_train"
    assert manifest["text_variant"] == "abstract_only"
    assert manifest["split_version"] == "phase2_v1"
    assert manifest["inputs"]["gold_artifact"] == "reports/phase2_gold_supervision.csv"
    assert manifest["inputs"]["split_artifact"] == "reports/phase2_split_assignments.csv"
    assert manifest["artifacts"]["model"] == "model.joblib"
