from __future__ import annotations

from pathlib import Path

from abstract_classifier.training import load_theory_baseline_config


def test_theory_baseline_config_loads_expected_phase3_contract(
    project_root: Path,
) -> None:
    config = load_theory_baseline_config(project_root / "configs" / "theory_baseline.toml")

    assert config.version == "1"
    assert config.default_text_variant == "abstract_only"
    assert config.model_family == "tfidf_logreg"
    assert config.gold_artifact_path == project_root / "reports" / "phase2_gold_supervision.csv"
    assert config.split_artifact_path == project_root / "reports" / "phase2_split_assignments.csv"
    assert config.taxonomy_config_path == project_root / "configs" / "taxonomy.toml"
    assert config.supervision_config_path == project_root / "configs" / "supervision.toml"
    assert config.default_output_root == project_root / "reports" / "phase3"


def test_theory_baseline_config_declares_exact_variant_contract(
    project_root: Path,
) -> None:
    config = load_theory_baseline_config(project_root / "configs" / "theory_baseline.toml")

    assert config.comparison_variants == (
        "abstract_only",
        "abstract_plus_keywords",
        "title_abstract_plus_keywords",
    )
    assert config.training.random_state == 20260416
    assert config.evaluation.default_split == "test"
