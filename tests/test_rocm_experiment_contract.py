from __future__ import annotations

from pathlib import Path

from abstract_classifier.training import load_theory_baseline_config


def test_theory_experiment_config_loads_phase7_contract(project_root: Path) -> None:
    config = load_theory_baseline_config(
        project_root / "configs" / "theory_experiments.toml"
    )

    assert config.version == "2"
    assert config.default_text_variant == "title_abstract_plus_keywords"
    assert config.model_family == "sentence_transformer_logreg"
    assert config.baseline_anchor_run_dir == (
        project_root / "reports" / "phase3" / "phase5_full_train_keywords"
    )
    assert config.baseline_anchor_predictions_path == (
        project_root
        / "reports"
        / "phase5"
        / "full_corpus_inference_keywords"
        / "predictions.csv"
    )
    assert config.trusted_experiment_artifact_path == (
        project_root
        / "reports"
        / "tmp_phase6"
        / "trust_smoke"
        / "trusted_experiment_corpus.csv"
    )
    assert config.trusted_production_artifact_path == (
        project_root
        / "reports"
        / "tmp_phase6"
        / "trust_smoke"
        / "trusted_production_corpus.csv"
    )
    assert config.runtime.target_environment == "wsl_rocm"
    assert config.runtime.target_device == "cuda"
    assert config.runtime.runtime_budget_hours == 5.0
    assert config.runtime.wsl_distribution == "Ubuntu-24.04"
    assert config.evaluation.required_retained_accuracy == 0.70
    assert config.evaluation.required_coverage_rate == 0.15
    assert config.candidate_model_families == (
        "tfidf_char_wb_logreg",
        "tfidf_svd_logreg",
        "sentence_transformer_logreg",
    )
    assert config.comparison_variants == (
        "abstract_only",
        "abstract_plus_keywords",
        "title_abstract_plus_keywords",
    )
