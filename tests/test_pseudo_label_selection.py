from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from abstract_classifier.pseudo_labeling import (
    load_pseudo_label_settings,
    run_governed_pseudo_label_pipeline,
)


def _write_metrics(path: Path) -> None:
    rows = [
        {
            "canonical_id": "tipo_1_realismo_fuerte",
            "label_canonica": "T1",
            "precision": 0.5,
            "recall": 0.5,
            "f1_score": 0.0,
            "support": 1,
        },
        {
            "canonical_id": "tipo_5_constructivismo_moderado",
            "label_canonica": "T5",
            "precision": 0.5,
            "recall": 0.5,
            "f1_score": 0.5,
            "support": 2,
        },
    ]
    pd.DataFrame(rows).to_csv(path, index=False)


def test_pseudo_label_pipeline_smoke(tmp_path: Path) -> None:
    trusted = tmp_path / "trusted.csv"
    preds = tmp_path / "preds.csv"
    gold = tmp_path / "gold.csv"
    splits = tmp_path / "splits.csv"
    metrics = tmp_path / "metrics_per_class.csv"
    gate = tmp_path / "promotion_gate.json"
    gate.write_text("{}", encoding="utf-8")
    _write_metrics(metrics)

    pd.DataFrame(
        {
            "record_id": ["a", "b", "c"],
            "abstract": ["x " * 50, "y " * 50, "z " * 50],
        }
    ).to_csv(trusted, index=False)

    pd.DataFrame(
        {
        "record_id": ["seed:x", "a", "b", "d"],
        "split": ["train", "train", "val", "train"],
        }
    ).to_csv(splits, index=False)

    pd.DataFrame(
        {
            "record_id": ["seed:x"],
            "canonical_id": ["tipo_5_constructivismo_moderado"],
        }
    ).to_csv(gold, index=False)

    long_abs = ("word " * 120)[:2000]
    base_pred = {
        "record_id": ["a", "b", "c", "d"],
        "model_run_id": ["sentence_transformer_logreg_test"] * 4,
        "source_dataset": ["scopus_base", "google_corpus", "scopus_base", "scopus_base"],
        "delivery_tier": ["auto_ready"] * 4,
        "calibrated_prediction_score": [0.9, 0.9, 0.9, 0.9],
        "prediction_margin": [0.2, 0.2, 0.2, 0.2],
        "review_low_confidence": [False, False, False, False],
        "review_taxonomy_conflict": [False, False, False, False],
        "abstained": [False, False, False, False],
        "predicted_canonical_id": ["tipo_5_constructivismo_moderado"] * 4,
        "predicted_label_canonica": ["T5"] * 4,
        "second_predicted_canonical_id": ["tipo_5_constructivismo_moderado"] * 4,
        "abstract_word_count": [250, 250, 250, 250],
        "abstract": [long_abs, long_abs, long_abs, long_abs],
    }
    pd.DataFrame(base_pred).to_csv(preds, index=False)

    cfg = tmp_path / "pseudo.toml"
    cfg.write_text(
        "\n".join(
            [
                'version = "test"',
                f'trusted_source_artifact = "{trusted.as_posix()}"',
                f'prediction_artifact = "{preds.as_posix()}"',
                f'promotion_gate_artifact = "{gate.as_posix()}"',
                "preferred_source_order = [\"scopus_base\", \"google_corpus\"]",
                "minimum_abstract_words = 80",
                "minimum_abstract_characters = 400",
                "minimum_calibrated_prediction_score = 0.75",
                "minimum_prediction_margin = 0.12",
                "fallback_score_threshold = 0.82",
                "fallback_margin_threshold = 0.16",
                "weak_class_score_threshold = 0.88",
                "weak_class_margin_threshold = 0.20",
                "minimum_admitted_rows = 1",
                "max_global_class_share = 0.99",
                'pseudo_label_wave_id = "wave_test"',
                'teacher_run_id = "sentence_transformer_logreg_test"',
                f'gold_supervision_artifact = "{gold.as_posix()}"',
                f'split_artifact = "{splits.as_posix()}"',
                f'metrics_per_class_artifact = "{metrics.as_posix()}"',
            ]
        ),
        encoding="utf-8",
    )

    settings = load_pseudo_label_settings(cfg)
    out = tmp_path / "out"
    paths = run_governed_pseudo_label_pipeline(settings=settings, output_dir=out)

    admitted = pd.read_csv(paths["admitted"])
    rejected = pd.read_csv(paths["rejected"])
    candidates = pd.read_csv(paths["candidates"])
    assert "rejection_reason" in candidates.columns
    assert (candidates["record_id"].astype(str) == "d").any()
    assert (
        candidates.loc[candidates["record_id"].astype(str) == "d", "rejection_reason"].astype(str)
        == "outside_trusted_corpus"
    ).all()
    assert "rejection_reason" in rejected.columns

    gold_ids = set(pd.read_csv(gold)["record_id"].astype(str))
    if not admitted.empty:
        assert not admitted["record_id"].astype(str).isin(gold_ids).any()
        assert (admitted["delivery_tier"].astype(str).str.lower() == "auto_ready").all()

    policy = json.loads(paths["policy"].read_text(encoding="utf-8"))
    assert policy["pseudo_label_wave_id"] == "wave_test"
    assert policy["policy_version"] == "phase9_policy_v1"
    assert policy["teacher_run_id"] == "sentence_transformer_logreg_test"
    assert "final_status" in policy
    assert policy["admission_options"]["require_cross_model_agreement"] is False
    assert policy["admission_options"]["admission_top_k_per_class"] is None


def test_cross_model_agreement_rejects_mismatch(tmp_path: Path) -> None:
    trusted = tmp_path / "trusted.csv"
    preds = tmp_path / "preds.csv"
    gold = tmp_path / "gold.csv"
    splits = tmp_path / "splits.csv"
    metrics = tmp_path / "metrics_per_class.csv"
    gate = tmp_path / "promotion_gate.json"
    gate.write_text("{}", encoding="utf-8")
    _write_metrics(metrics)

    pd.DataFrame({"record_id": ["a", "b"], "abstract": ["w " * 50, "w " * 50]}).to_csv(
        trusted, index=False
    )
    pd.DataFrame({"record_id": ["a", "b", "gx"], "split": ["train", "train", "train"]}).to_csv(
        splits, index=False
    )
    pd.DataFrame(
        {"record_id": ["gx"], "canonical_id": ["tipo_5_constructivismo_moderado"]}
    ).to_csv(gold, index=False)

    long_abs = ("word " * 120)[:2000]
    primary = {
        "record_id": ["a", "b"],
        "model_run_id": ["champion"] * 2,
        "source_dataset": ["scopus_base", "scopus_base"],
        "delivery_tier": ["auto_ready"] * 2,
        "calibrated_prediction_score": [0.9, 0.9],
        "prediction_margin": [0.2, 0.2],
        "review_low_confidence": [False, False],
        "review_taxonomy_conflict": [False, False],
        "abstained": [False, False],
        "predicted_canonical_id": ["tipo_5_constructivismo_moderado", "tipo_5_constructivismo_moderado"],
        "predicted_label_canonica": ["T5", "T5"],
        "second_predicted_canonical_id": ["tipo_5_constructivismo_moderado"] * 2,
        "abstract_word_count": [250, 250],
        "abstract": [long_abs, long_abs],
    }
    secondary = {
        "record_id": ["a", "b"],
        "model_run_id": ["challenger"] * 2,
        "source_dataset": ["scopus_base", "scopus_base"],
        "delivery_tier": ["auto_ready"] * 2,
        "predicted_canonical_id": ["tipo_5_constructivismo_moderado", "tipo_1_realismo_fuerte"],
    }
    pri_df = pd.DataFrame(primary)
    sec_df = pd.DataFrame(secondary)
    pd.concat([pri_df, sec_df], ignore_index=True).to_csv(preds, index=False)

    cfg = tmp_path / "pseudo.toml"
    cfg.write_text(
        "\n".join(
            [
                'version = "test"',
                f'trusted_source_artifact = "{trusted.as_posix()}"',
                f'prediction_artifact = "{preds.as_posix()}"',
                f'promotion_gate_artifact = "{gate.as_posix()}"',
                'preferred_source_order = ["scopus_base"]',
                "minimum_abstract_words = 80",
                "minimum_abstract_characters = 400",
                "minimum_calibrated_prediction_score = 0.75",
                "minimum_prediction_margin = 0.12",
                "fallback_score_threshold = 0.82",
                "fallback_margin_threshold = 0.16",
                "weak_class_score_threshold = 0.88",
                "weak_class_margin_threshold = 0.20",
                "minimum_admitted_rows = 1",
                "max_global_class_share = 1.0",
                'pseudo_label_wave_id = "wave_x"',
                'teacher_run_id = "champion"',
                f'gold_supervision_artifact = "{gold.as_posix()}"',
                f'split_artifact = "{splits.as_posix()}"',
                f'metrics_per_class_artifact = "{metrics.as_posix()}"',
                "require_cross_model_agreement = true",
                'secondary_teacher_run_id = "challenger"',
            ]
        ),
        encoding="utf-8",
    )

    settings = load_pseudo_label_settings(cfg)
    out = tmp_path / "out"
    paths = run_governed_pseudo_label_pipeline(settings=settings, output_dir=out)
    admitted = pd.read_csv(paths["admitted"])
    cands = pd.read_csv(paths["candidates"])
    assert len(admitted) == 1
    assert (admitted["record_id"].astype(str) == "a").all()
    row_b = cands.loc[cands["record_id"].astype(str) == "b"].iloc[0]
    assert str(row_b["rejection_reason"]) == "cross_model_disagreement"


def test_admission_top_k_per_class(tmp_path: Path) -> None:
    trusted = tmp_path / "trusted.csv"
    preds = tmp_path / "preds.csv"
    gold = tmp_path / "gold.csv"
    splits = tmp_path / "splits.csv"
    metrics = tmp_path / "metrics_per_class.csv"
    gate = tmp_path / "promotion_gate.json"
    gate.write_text("{}", encoding="utf-8")
    _write_metrics(metrics)

    ids = [f"r{i}" for i in range(5)]
    all_ids = ids + ["gx"]
    pd.DataFrame({"record_id": all_ids, "abstract": ["w " * 50] * len(all_ids)}).to_csv(
        trusted, index=False
    )
    pd.DataFrame({"record_id": all_ids, "split": ["train"] * len(all_ids)}).to_csv(
        splits, index=False
    )
    pd.DataFrame(
        {"record_id": ["gx"], "canonical_id": ["tipo_5_constructivismo_moderado"]}
    ).to_csv(gold, index=False)

    long_abs = ("word " * 120)[:2000]
    base_pred = {
        "record_id": ids,
        "model_run_id": ["t"] * 5,
        "source_dataset": ["scopus_base"] * 5,
        "delivery_tier": ["auto_ready"] * 5,
        "calibrated_prediction_score": [0.95, 0.94, 0.93, 0.92, 0.91],
        "prediction_margin": [0.5, 0.4, 0.3, 0.2, 0.19],
        "review_low_confidence": [False] * 5,
        "review_taxonomy_conflict": [False] * 5,
        "abstained": [False] * 5,
        "predicted_canonical_id": ["tipo_5_constructivismo_moderado"] * 5,
        "predicted_label_canonica": ["T5"] * 5,
        "second_predicted_canonical_id": ["tipo_5_constructivismo_moderado"] * 5,
        "abstract_word_count": [250] * 5,
        "abstract": [long_abs] * 5,
    }
    pd.DataFrame(base_pred).to_csv(preds, index=False)

    cfg = tmp_path / "pseudo.toml"
    cfg.write_text(
        "\n".join(
            [
                'version = "test"',
                f'trusted_source_artifact = "{trusted.as_posix()}"',
                f'prediction_artifact = "{preds.as_posix()}"',
                f'promotion_gate_artifact = "{gate.as_posix()}"',
                'preferred_source_order = ["scopus_base"]',
                "minimum_abstract_words = 80",
                "minimum_abstract_characters = 400",
                "minimum_calibrated_prediction_score = 0.75",
                "minimum_prediction_margin = 0.12",
                "fallback_score_threshold = 0.82",
                "fallback_margin_threshold = 0.16",
                "weak_class_score_threshold = 0.88",
                "weak_class_margin_threshold = 0.20",
                "minimum_admitted_rows = 1",
                "max_global_class_share = 1.0",
                'pseudo_label_wave_id = "wave_k"',
                'teacher_run_id = "t"',
                f'gold_supervision_artifact = "{gold.as_posix()}"',
                f'split_artifact = "{splits.as_posix()}"',
                f'metrics_per_class_artifact = "{metrics.as_posix()}"',
                "admission_top_k_per_class = 2",
            ]
        ),
        encoding="utf-8",
    )

    settings = load_pseudo_label_settings(cfg)
    out = tmp_path / "out2"
    paths = run_governed_pseudo_label_pipeline(settings=settings, output_dir=out)
    admitted = pd.read_csv(paths["admitted"])
    assert len(admitted) == 2
    assert set(admitted["record_id"].astype(str)) == {"r0", "r1"}


def test_review_feedback_excludes_noncanonical_rows(tmp_path: Path) -> None:
    trusted = tmp_path / "trusted.csv"
    preds = tmp_path / "preds.csv"
    gold = tmp_path / "gold.csv"
    splits = tmp_path / "splits.csv"
    metrics = tmp_path / "metrics_per_class.csv"
    reviewed = tmp_path / "client_micro_reviewed.csv"
    gate = tmp_path / "promotion_gate.json"
    gate.write_text("{}", encoding="utf-8")
    _write_metrics(metrics)

    pd.DataFrame(
        {
            "record_id": ["a", "b", "c", "gx"],
            "abstract": ["w " * 50] * 4,
        }
    ).to_csv(trusted, index=False)
    pd.DataFrame({"record_id": ["a", "b", "c", "gx"], "split": ["train"] * 4}).to_csv(
        splits, index=False
    )
    pd.DataFrame(
        {"record_id": ["gx"], "canonical_id": ["tipo_5_constructivismo_moderado"]}
    ).to_csv(gold, index=False)
    reviewed.write_text(
        "\n".join(
            [
                "record_id;prediccion_modelo_id;prediccion_modelo_etiqueta;segunda_opcion_id;segunda_opcion_etiqueta;canonical_id_corregido;etiqueta_canonica_corregida;notas_revisor",
                "a;tipo_5_constructivismo_moderado;T5;;;;;No aplica debe limpiarse",
                "b;tipo_5_constructivismo_moderado;T5;;;;;insufficient_theory_signal",
            ]
        ),
        encoding="utf-8",
    )

    long_abs = ("word " * 120)[:2000]
    pd.DataFrame(
        {
            "record_id": ["a", "b", "c"],
            "model_run_id": ["sentence_transformer_logreg_test"] * 3,
            "source_dataset": ["scopus_base"] * 3,
            "delivery_tier": ["auto_ready"] * 3,
            "calibrated_prediction_score": [0.9, 0.9, 0.9],
            "prediction_margin": [0.2, 0.2, 0.2],
            "review_low_confidence": [False, False, False],
            "review_taxonomy_conflict": [False, False, False],
            "abstained": [False, False, False],
            "predicted_canonical_id": ["tipo_5_constructivismo_moderado"] * 3,
            "predicted_label_canonica": ["T5"] * 3,
            "second_predicted_canonical_id": ["tipo_5_constructivismo_moderado"] * 3,
            "abstract_word_count": [250, 250, 250],
            "abstract": [long_abs, long_abs, long_abs],
        }
    ).to_csv(preds, index=False)

    cfg = tmp_path / "pseudo.toml"
    cfg.write_text(
        "\n".join(
            [
                'version = "test"',
                f'trusted_source_artifact = "{trusted.as_posix()}"',
                f'prediction_artifact = "{preds.as_posix()}"',
                f'promotion_gate_artifact = "{gate.as_posix()}"',
                'preferred_source_order = ["scopus_base"]',
                "minimum_abstract_words = 80",
                "minimum_abstract_characters = 400",
                "minimum_calibrated_prediction_score = 0.75",
                "minimum_prediction_margin = 0.12",
                "fallback_score_threshold = 0.82",
                "fallback_margin_threshold = 0.16",
                "weak_class_score_threshold = 0.88",
                "weak_class_margin_threshold = 0.20",
                "minimum_admitted_rows = 1",
                "max_global_class_share = 1.0",
                'pseudo_label_wave_id = "wave_feedback"',
                'teacher_run_id = "sentence_transformer_logreg_test"',
                f'gold_supervision_artifact = "{gold.as_posix()}"',
                f'split_artifact = "{splits.as_posix()}"',
                f'metrics_per_class_artifact = "{metrics.as_posix()}"',
                f'client_review_feedback_artifact = "{reviewed.as_posix()}"',
                'excluded_review_outcomes = ["out_of_scope_theory", "insufficient_theory_signal"]',
                'admission_policy_version = "phase9_review_iteration_v1"',
            ]
        ),
        encoding="utf-8",
    )

    settings = load_pseudo_label_settings(cfg)
    out = tmp_path / "out_feedback"
    paths = run_governed_pseudo_label_pipeline(settings=settings, output_dir=out)
    admitted = pd.read_csv(paths["admitted"])
    candidates = pd.read_csv(paths["candidates"])
    noncanonical = pd.read_csv(paths["noncanonical_review"])
    policy = json.loads(paths["policy"].read_text(encoding="utf-8"))

    assert set(admitted["record_id"].astype(str)) == {"c"}
    reason_lookup = candidates.set_index("record_id")["rejection_reason"].astype(str)
    assert reason_lookup["a"] == "candidate_outlier_distributional"
    assert reason_lookup["b"] == "reviewed_insufficient_theory_signal"
    assert set(noncanonical["record_id"].astype(str)) == {"a", "b"}
    assert policy["policy_version"] == "phase9_review_iteration_v1"
    assert "candidate_outlier_distributional" in policy["rejection_state_vocabulary"]


def test_conformal_gate_rejects_non_singleton_safe_candidate(tmp_path: Path) -> None:
    trusted = tmp_path / "trusted.csv"
    preds = tmp_path / "preds.csv"
    gold = tmp_path / "gold.csv"
    splits = tmp_path / "splits.csv"
    metrics = tmp_path / "metrics_per_class.csv"
    gate = tmp_path / "promotion_gate.json"
    conformal_ref = tmp_path / "reference_predictions.csv"
    gate.write_text("{}", encoding="utf-8")
    _write_metrics(metrics)

    pd.DataFrame({"record_id": ["a", "gx"], "abstract": ["w " * 50, "w " * 50]}).to_csv(
        trusted, index=False
    )
    pd.DataFrame({"record_id": ["a", "gx"], "split": ["train", "train"]}).to_csv(
        splits, index=False
    )
    pd.DataFrame(
        {"record_id": ["gx"], "canonical_id": ["tipo_5_constructivismo_moderado"]}
    ).to_csv(gold, index=False)
    pd.DataFrame(
        {
            "canonical_id": ["tipo_1", "tipo_2", "tipo_3", "tipo_4"],
            "predicted_canonical_id": ["tipo_1", "tipo_2", "tipo_x", "tipo_4"],
            "prediction_score": [0.95, 0.80, 0.99, 0.60],
        }
    ).to_csv(conformal_ref, index=False)

    long_abs = ("word " * 120)[:2000]
    pd.DataFrame(
        {
            "record_id": ["a"],
            "model_run_id": ["sentence_transformer_logreg_test"],
            "source_dataset": ["scopus_base"],
            "delivery_tier": ["auto_ready"],
            "calibrated_prediction_score": [0.70],
            "prediction_margin": [0.20],
            "review_low_confidence": [False],
            "review_taxonomy_conflict": [False],
            "abstained": [False],
            "predicted_canonical_id": ["tipo_5_constructivismo_moderado"],
            "predicted_label_canonica": ["T5"],
            "second_predicted_canonical_id": ["tipo_5_constructivismo_moderado"],
            "abstract_word_count": [250],
            "abstract": [long_abs],
        }
    ).to_csv(preds, index=False)

    cfg = tmp_path / "pseudo.toml"
    cfg.write_text(
        "\n".join(
            [
                'version = "test"',
                f'trusted_source_artifact = "{trusted.as_posix()}"',
                f'prediction_artifact = "{preds.as_posix()}"',
                f'promotion_gate_artifact = "{gate.as_posix()}"',
                'preferred_source_order = ["scopus_base"]',
                "minimum_abstract_words = 80",
                "minimum_abstract_characters = 400",
                "minimum_calibrated_prediction_score = 0.60",
                "minimum_prediction_margin = 0.12",
                "fallback_score_threshold = 0.60",
                "fallback_margin_threshold = 0.12",
                "weak_class_score_threshold = 0.88",
                "weak_class_margin_threshold = 0.20",
                "minimum_admitted_rows = 1",
                "max_global_class_share = 1.0",
                'pseudo_label_wave_id = "wave_conformal"',
                'teacher_run_id = "sentence_transformer_logreg_test"',
                f'gold_supervision_artifact = "{gold.as_posix()}"',
                f'split_artifact = "{splits.as_posix()}"',
                f'metrics_per_class_artifact = "{metrics.as_posix()}"',
                "enable_conformal_gate = true",
                f'conformal_reference_predictions_artifact = "{conformal_ref.as_posix()}"',
                "conformal_alpha = 0.5",
                "conformal_minimum_correct_rows = 3",
            ]
        ),
        encoding="utf-8",
    )

    settings = load_pseudo_label_settings(cfg)
    out = tmp_path / "out_conformal"
    paths = run_governed_pseudo_label_pipeline(settings=settings, output_dir=out)
    admitted = pd.read_csv(paths["admitted"])
    candidates = pd.read_csv(paths["candidates"])
    conformal = pd.read_csv(paths["conformal"])
    policy = json.loads(paths["policy"].read_text(encoding="utf-8"))

    assert admitted.empty
    assert str(candidates.iloc[0]["rejection_reason"]) == "conformal_not_singleton_safe"
    assert bool(conformal.iloc[0]["conformal_accept"]) is False
    assert int(conformal.iloc[0]["conformal_prediction_set_size"]) == 2
    assert policy["raw_row_gate_admitted_count"] == 1
    assert policy["conformal_admitted_count"] == 0
    assert policy["conformal_policy"]["score_threshold"] == 0.8


def test_model_review_state_blocks_pseudo_label_admission(tmp_path: Path) -> None:
    trusted = tmp_path / "trusted.csv"
    preds = tmp_path / "preds.csv"
    gold = tmp_path / "gold.csv"
    splits = tmp_path / "splits.csv"
    metrics = tmp_path / "metrics_per_class.csv"
    gate = tmp_path / "promotion_gate.json"
    gate.write_text("{}", encoding="utf-8")
    _write_metrics(metrics)

    pd.DataFrame({"record_id": ["a", "b", "gx"], "abstract": ["w " * 50] * 3}).to_csv(
        trusted, index=False
    )
    pd.DataFrame({"record_id": ["a", "b", "gx"], "split": ["train"] * 3}).to_csv(
        splits, index=False
    )
    pd.DataFrame(
        {"record_id": ["gx"], "canonical_id": ["tipo_5_constructivismo_moderado"]}
    ).to_csv(gold, index=False)

    long_abs = ("word " * 120)[:2000]
    pd.DataFrame(
        {
            "record_id": ["a", "b"],
            "model_run_id": ["sentence_transformer_logreg_test"] * 2,
            "source_dataset": ["scopus_base"] * 2,
            "delivery_tier": ["auto_ready"] * 2,
            "calibrated_prediction_score": [0.9, 0.9],
            "prediction_margin": [0.2, 0.2],
            "review_low_confidence": [False, False],
            "review_taxonomy_conflict": [False, False],
            "abstained": [False, False],
            "review_state": ["out_of_scope_theory", "insufficient_theory_signal"],
            "predicted_canonical_id": ["tipo_5_constructivismo_moderado"] * 2,
            "predicted_label_canonica": ["T5"] * 2,
            "second_predicted_canonical_id": ["tipo_5_constructivismo_moderado"] * 2,
            "abstract_word_count": [250, 250],
            "abstract": [long_abs, long_abs],
        }
    ).to_csv(preds, index=False)

    cfg = tmp_path / "pseudo.toml"
    cfg.write_text(
        "\n".join(
            [
                'version = "test"',
                f'trusted_source_artifact = "{trusted.as_posix()}"',
                f'prediction_artifact = "{preds.as_posix()}"',
                f'promotion_gate_artifact = "{gate.as_posix()}"',
                'preferred_source_order = ["scopus_base"]',
                "minimum_abstract_words = 80",
                "minimum_abstract_characters = 400",
                "minimum_calibrated_prediction_score = 0.75",
                "minimum_prediction_margin = 0.12",
                "fallback_score_threshold = 0.82",
                "fallback_margin_threshold = 0.16",
                "weak_class_score_threshold = 0.88",
                "weak_class_margin_threshold = 0.20",
                "minimum_admitted_rows = 1",
                "max_global_class_share = 1.0",
                'pseudo_label_wave_id = "wave_state"',
                'teacher_run_id = "sentence_transformer_logreg_test"',
                f'gold_supervision_artifact = "{gold.as_posix()}"',
                f'split_artifact = "{splits.as_posix()}"',
                f'metrics_per_class_artifact = "{metrics.as_posix()}"',
            ]
        ),
        encoding="utf-8",
    )

    settings = load_pseudo_label_settings(cfg)
    out = tmp_path / "out_state"
    paths = run_governed_pseudo_label_pipeline(settings=settings, output_dir=out)
    candidates = pd.read_csv(paths["candidates"]).set_index("record_id")

    assert str(candidates.loc["a", "rejection_reason"]) == "predicted_out_of_scope_theory"
    assert str(candidates.loc["b", "rejection_reason"]) == "predicted_insufficient_theory_signal"


def test_weak_signal_artifacts_enrich_candidates(tmp_path: Path) -> None:
    trusted = tmp_path / "trusted.csv"
    preds = tmp_path / "preds.csv"
    gold = tmp_path / "gold.csv"
    splits = tmp_path / "splits.csv"
    metrics = tmp_path / "metrics_per_class.csv"
    gate = tmp_path / "promotion_gate.json"
    gate.write_text("{}", encoding="utf-8")
    _write_metrics(metrics)

    pd.DataFrame({"record_id": ["a", "gx"], "abstract": ["w " * 50, "w " * 50]}).to_csv(
        trusted, index=False
    )
    pd.DataFrame({"record_id": ["a", "gx"], "split": ["train", "train"]}).to_csv(
        splits, index=False
    )
    pd.DataFrame(
        {"record_id": ["gx"], "canonical_id": ["tipo_5_constructivismo_moderado"]}
    ).to_csv(gold, index=False)

    long_abs = ("word " * 120)[:2000]
    pd.DataFrame(
        {
            "record_id": ["a"],
            "model_run_id": ["sentence_transformer_logreg_test"],
            "source_dataset": ["scopus_base"],
            "delivery_tier": ["auto_ready"],
            "calibrated_prediction_score": [0.92],
            "prediction_margin": [0.22],
            "review_low_confidence": [False],
            "review_taxonomy_conflict": [False],
            "abstained": [False],
            "predicted_canonical_id": ["tipo_1_realismo_fuerte"],
            "predicted_label_canonica": ["T1"],
            "second_predicted_canonical_id": ["tipo_2_realismo_moderado_critico"],
            "abstract_word_count": [250],
            "abstract": [long_abs],
            "title": ["Critical realism and policy change"],
            "references": ["Bhaskar R., Example reference"],
            "author_keywords": [""],
            "index_keywords": [""],
        }
    ).to_csv(preds, index=False)

    cfg = tmp_path / "pseudo.toml"
    cfg.write_text(
        "\n".join(
            [
                'version = "test"',
                f'trusted_source_artifact = "{trusted.as_posix()}"',
                f'prediction_artifact = "{preds.as_posix()}"',
                f'promotion_gate_artifact = "{gate.as_posix()}"',
                'preferred_source_order = ["scopus_base"]',
                "minimum_abstract_words = 80",
                "minimum_abstract_characters = 400",
                "minimum_calibrated_prediction_score = 0.75",
                "minimum_prediction_margin = 0.12",
                "fallback_score_threshold = 0.82",
                "fallback_margin_threshold = 0.16",
                "weak_class_score_threshold = 0.88",
                "weak_class_margin_threshold = 0.20",
                "minimum_admitted_rows = 1",
                "max_global_class_share = 1.0",
                'pseudo_label_wave_id = "wave_weak_signal"',
                'teacher_run_id = "sentence_transformer_logreg_test"',
                f'gold_supervision_artifact = "{gold.as_posix()}"',
                f'split_artifact = "{splits.as_posix()}"',
                f'metrics_per_class_artifact = "{metrics.as_posix()}"',
            ]
        ),
        encoding="utf-8",
    )

    settings = load_pseudo_label_settings(cfg)
    out = tmp_path / "out_weak"
    paths = run_governed_pseudo_label_pipeline(settings=settings, output_dir=out)
    candidates = pd.read_csv(paths["candidates"])
    weak_signals = pd.read_csv(paths["weak_signals"])

    assert "weak_signal_majority_canonical_id" in candidates.columns
    assert "weak_signal_conflict" in candidates.columns
    assert candidates.loc[0, "weak_signal_majority_canonical_id"] == "tipo_2_realismo_moderado_critico"
    assert bool(candidates.loc[0, "weak_signal_conflict"]) is True
    assert set(weak_signals["record_id"].astype(str)) == {"a"}
