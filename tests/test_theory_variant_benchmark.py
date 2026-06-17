from __future__ import annotations

from pathlib import Path

import pandas as pd


def test_variant_benchmark_writes_flat_comparison_artifact(
    cli_runner,
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "variant_compare"
    result = cli_runner(
        "evaluate",
        "--config",
        "configs/theory_baseline.toml",
        "--compare-variants",
        "abstract_only",
        "abstract_plus_keywords",
        "title_abstract_plus_keywords",
        "--output-dir",
        str(output_dir),
    )

    assert result.returncode == 0, result.stderr

    comparison = pd.read_csv(output_dir / "variant_comparison.csv")
    assert set(comparison["text_variant"]) == {
        "abstract_only",
        "abstract_plus_keywords",
        "title_abstract_plus_keywords",
    }
    assert {
        "run_id",
        "text_variant",
        "split",
        "split_version",
        "accuracy",
        "macro_f1",
        "weighted_f1",
        "keyword_coverage_rate",
    } <= set(comparison.columns)
    assert set(comparison["split_version"]) == {"phase2_v1"}
    assert (output_dir / "abstract_only" / "run_manifest.json").exists()
    assert (output_dir / "abstract_plus_keywords" / "metrics_overall.json").exists()
    assert (output_dir / "title_abstract_plus_keywords" / "metrics_overall.json").exists()
