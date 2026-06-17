from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from abstract_classifier.evaluation import compare_model_families
from abstract_classifier.training import load_theory_baseline_config


def test_compare_model_families_writes_phase7_bundle(
    project_root: Path,
    tmp_path: Path,
) -> None:
    trusted_source = pd.read_csv(
        project_root
        / "reports"
        / "tmp_phase6"
        / "trust_smoke"
        / "trusted_experiment_corpus.csv",
        encoding="utf-8",
    ).head(20)
    trusted_target = pd.read_csv(
        project_root
        / "reports"
        / "tmp_phase6"
        / "trust_smoke"
        / "trusted_production_corpus.csv",
        encoding="utf-8",
    ).head(20)

    trusted_experiment_path = tmp_path / "trusted_experiment.csv"
    trusted_production_path = tmp_path / "trusted_production.csv"
    trusted_source.to_csv(trusted_experiment_path, index=False, encoding="utf-8")
    trusted_target.to_csv(trusted_production_path, index=False, encoding="utf-8")

    config_path = tmp_path / "theory_experiments_test.toml"
    config_path.write_text(
        "\n".join(
            [
                'version = "test"',
                f'taxonomy_config = "{(project_root / "configs" / "taxonomy.toml").as_posix()}"',
                f'supervision_config = "{(project_root / "configs" / "supervision.toml").as_posix()}"',
                f'gold_artifact = "{(project_root / "reports" / "phase2_gold_supervision.csv").as_posix()}"',
                f'split_artifact = "{(project_root / "reports" / "phase2_split_assignments.csv").as_posix()}"',
                'default_text_variant = "title_abstract_plus_keywords"',
                f'default_output_root = "{(tmp_path / "runs").as_posix()}"',
                'model_family = "tfidf_svd_logreg"',
                'comparison_variants = ["abstract_only", "abstract_plus_keywords", "title_abstract_plus_keywords"]',
                'candidate_model_families = ["tfidf_char_wb_logreg", "tfidf_svd_logreg"]',
                f'baseline_anchor_run_dir = "{(project_root / "reports" / "phase3" / "phase5_full_train_keywords").as_posix()}"',
                f'baseline_anchor_predictions = "{(project_root / "reports" / "phase5" / "full_corpus_inference_keywords" / "predictions.csv").as_posix()}"',
                f'trusted_experiment_artifact = "{trusted_experiment_path.as_posix()}"',
                f'trusted_production_artifact = "{trusted_production_path.as_posix()}"',
                "",
                "[training]",
                "max_features = 4000",
                "ngram_min = 1",
                "ngram_max = 2",
                "min_df = 1",
                "max_iter = 1000",
                'class_weight = "balanced"',
                "random_state = 20260417",
                "char_ngram_min = 3",
                "char_ngram_max = 5",
                "svd_components = 64",
                'sentence_transformer_model_name = "sentence-transformers/all-MiniLM-L6-v2"',
                "sentence_batch_size = 16",
                "",
                "[evaluation]",
                'default_split = "test"',
                "",
                "[runtime]",
                'target_environment = "test"',
                'target_device = "cpu"',
                "runtime_budget_hours = 1.0",
                'wsl_distribution = "Ubuntu-24.04"',
            ]
        ),
        encoding="utf-8",
    )

    config = load_theory_baseline_config(config_path, root=project_root)
    artifacts = compare_model_families(
        config=config,
        output_dir=tmp_path / "benchmark",
        model_families=("tfidf_char_wb_logreg", "tfidf_svd_logreg"),
        root=project_root,
    )

    comparison = pd.read_csv(artifacts["comparison"], encoding="utf-8")
    per_class = pd.read_csv(artifacts["per_class"], encoding="utf-8")
    champion = json.loads(artifacts["champion"].read_text(encoding="utf-8"))

    assert artifacts["comparison"].exists()
    assert artifacts["per_class"].exists()
    assert artifacts["champion"].exists()
    assert {
        "run_id",
        "model_family",
        "macro_f1",
        "operational_median_prediction_margin",
        "trusted_production_artifact",
    } <= set(comparison.columns)
    assert set(comparison["model_family"]) >= {
        "tfidf_logreg",
        "tfidf_char_wb_logreg",
        "tfidf_svd_logreg",
    }
    assert {"run_id", "model_family", "canonical_id", "f1_score"} <= set(per_class.columns)
    assert champion["selected_model_family"] in {
        "tfidf_logreg",
        "tfidf_char_wb_logreg",
        "tfidf_svd_logreg",
    }
    assert comparison["output_dir"].notna().all()
    assert champion["trusted_production_artifact"].endswith("trusted_production.csv")
