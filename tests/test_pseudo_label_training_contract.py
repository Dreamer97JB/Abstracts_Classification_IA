from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from abstract_classifier.training import train_theory_gold_plus_pseudo


def test_gold_plus_pseudo_manifest_without_comparison_bundle(
    tmp_path: Path,
) -> None:
    """Fast contract: pseudo rows only augment train; manifest records weights."""
    repo = Path(__file__).resolve().parents[1]
    gold_path = repo / "reports" / "phase2_gold_supervision.csv"
    split_path = repo / "reports" / "phase2_split_assignments.csv"
    if not gold_path.exists() or not split_path.exists():
        return

    gold = pd.read_csv(gold_path)
    splits = pd.read_csv(split_path)
    train_ids = set(
        splits.loc[splits["split"].astype(str).str.lower() == "train", "record_id"].astype(str)
    )
    template = gold.loc[gold["record_id"].astype(str).isin(train_ids)].head(1).copy()
    pseudo_rows = []
    for idx in range(2):
        row = template.iloc[0].copy()
        rid = f"pseudo:test:{idx}"
        row["record_id"] = rid
        row["canonical_id"] = str(row["canonical_id"])
        row["label_canonica"] = row["label_canonica"]
        row["author_keywords"] = ""
        row["index_keywords"] = ""
        row["keywords_available"] = False
        pseudo_rows.append(row)
    pseudo_path = tmp_path / "pseudo_label_admitted.csv"
    pd.DataFrame(pseudo_rows).to_csv(pseudo_path, index=False)

    cfg = tmp_path / "theory_pseudo_label.toml"
    cfg.write_text(
        "\n".join(
            [
                'version = "test"',
                'pseudo_label_wave_id = "wave_01_conservative"',
                'teacher_run_id = "sentence_transformer_logreg_test"',
                'taxonomy_config = "configs/taxonomy.toml"',
                'supervision_config = "configs/supervision.toml"',
                f'gold_artifact = "{gold_path.as_posix()}"',
                f'split_artifact = "{split_path.as_posix()}"',
                'default_text_variant = "abstract_only"',
                'default_output_root = "' + tmp_path.as_posix().replace("\\", "/") + '"',
                'model_family = "tfidf_logreg"',
                'comparison_variants = ["abstract_only"]',
                'candidate_model_families = ["tfidf_logreg"]',
                "[training]",
                "max_features = 200",
                "ngram_min = 1",
                "ngram_max = 2",
                "min_df = 1",
                "max_iter = 200",
                'class_weight = "balanced"',
                "random_state = 42",
                "[evaluation]",
                'default_split = "test"',
                "required_retained_accuracy = 0.7",
                "required_coverage_rate = 0.15",
                "[runtime]",
                'target_environment = "local"',
                'target_device = "cpu"',
                "[pseudo_training]",
                'training_mode = "gold_plus_pseudo"',
                "gold_weight = 1.0",
                "pseudo_weight = 0.35",
                f'pseudo_admitted_csv = "{pseudo_path.as_posix()}"',
                'pseudo_policy_json = "' + (tmp_path / "policy.json").as_posix().replace("\\", "/") + '"',
            ]
        ),
        encoding="utf-8",
    )

    out = tmp_path / "train_run"
    artifacts = train_theory_gold_plus_pseudo(
        config_path=cfg,
        run_id="unit_pseudo_train",
        output_dir=out,
        text_variant="abstract_only",
        root=repo,
        emit_comparison_bundle=False,
    )

    manifest = json.loads(artifacts.manifest_path.read_text(encoding="utf-8"))
    pt = manifest["pseudo_label_training"]
    assert pt["gold_weight"] == 1.0
    assert pt["pseudo_weight"] == 0.35
    assert pt["pseudo_train_rows"] == 2
    assert pt["gold_train_rows"] >= 1

    tm_path = pseudo_path.parent / "pseudo_label_training_manifest.json"
    assert tm_path.exists()
    tm = json.loads(tm_path.read_text(encoding="utf-8"))
    assert tm["teacher_run_id"] == "sentence_transformer_logreg_test"
    assert "pseudo_label_wave_id" in tm
