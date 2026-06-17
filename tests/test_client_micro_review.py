from __future__ import annotations

from pathlib import Path

import pandas as pd

from abstract_classifier.client_micro_review import (
    REVIEW_OUTCOME_CANONICAL,
    REVIEW_OUTCOME_INSUFFICIENT,
    REVIEW_OUTCOME_OUT_OF_SCOPE,
    export_client_micro_review_pack,
    load_client_micro_review_feedback,
)


def test_export_client_micro_review_pack(tmp_path: Path) -> None:
    pred = tmp_path / "predictions.csv"
    pd.DataFrame(
        [
            {
                "record_id": "a1",
                "title": "Critical realism in policy analysis",
                "abstract": "A" * 100,
                "source_dataset": "s",
                "predicted_canonical_id": "tipo_1_realismo_fuerte",
                "predicted_label_canonica": "L1",
                "second_predicted_canonical_id": "tipo_2",
                "second_predicted_label_canonica": "L2",
                "references": "Bhaskar R., Example reference",
                "prediction_margin": 0.05,
                "calibrated_prediction_score": 0.4,
                "review_reason": "low_margin",
                "review_state": "needs_review",
                "ood_outlier_score": 0.42,
                "needs_review": True,
                "review_low_confidence": True,
                "review_taxonomy_conflict": False,
                "model_run_id": "m1",
            },
            {
                "record_id": "a2",
                "title": "Strong programme and relativism in science studies",
                "abstract": "B",
                "source_dataset": "s",
                "predicted_canonical_id": "tipo_3_antirrealismo_epistemologico",
                "predicted_label_canonica": "L3",
                "second_predicted_canonical_id": "",
                "second_predicted_label_canonica": "",
                "references": "Bloor D., Another reference",
                "prediction_margin": 0.01,
                "calibrated_prediction_score": 0.2,
                "review_reason": "conflict",
                "review_state": "out_of_scope_theory",
                "ood_outlier_score": 0.93,
                "needs_review": True,
                "review_low_confidence": False,
                "review_taxonomy_conflict": True,
                "model_run_id": "m1",
            },
        ]
    ).to_csv(pred, index=False, encoding="utf-8")

    out_dir = tmp_path / "pack"
    paths = export_client_micro_review_pack(
        predictions_path=pred,
        output_dir=out_dir,
        max_rows=10,
        model_run_id="m1",
        gold_supervision_path=None,
    )

    assert paths["csv"].exists()
    assert paths["instructions"].exists()
    assert paths["manifest"].exists()
    assert paths["weak_signal_summary"].exists()
    assert paths["weak_signal_votes"].exists()

    instr = paths["instructions"].read_text(encoding="utf-8")
    assert "tipo_1_realismo_fuerte" in instr
    assert "out_of_scope_theory" in instr
    assert "a2" in instr

    client = pd.read_csv(paths["csv"], encoding="utf-8")
    assert list(client["record_id"]) == ["a2", "a1"]
    assert {"review_state_modelo", "ood_score_modelo"} <= set(client.columns)
    assert {
        "weak_signal_mayoria_id",
        "weak_signal_mayoria_etiqueta",
        "weak_signal_conflicto",
        "weak_signal_evidencia",
        "motivo_seleccion_pack",
    } <= set(client.columns)
    assert client.loc[client["record_id"] == "a2", "review_state_modelo"].iloc[0] == "out_of_scope_theory"
    assert (
        client.loc[client["record_id"] == "a1", "weak_signal_mayoria_id"].iloc[0]
        == "tipo_2_realismo_moderado_critico"
    )
    assert bool(client.loc[client["record_id"] == "a1", "weak_signal_conflicto"].iloc[0]) is True
    assert "weak_signal_conflict" in client.loc[client["record_id"] == "a1", "motivo_seleccion_pack"].iloc[0]
    assert "canonical_id_corregido" in client.columns
    assert "etiqueta_canonica_corregida" in client.columns

    weak_votes = pd.read_csv(paths["weak_signal_votes"], encoding="utf-8")
    assert set(weak_votes["record_id"].astype(str)) == {"a1", "a2"}


def test_load_client_micro_review_feedback_normalizes_noncanonical_states(tmp_path: Path) -> None:
    reviewed = tmp_path / "client_micro_reviewed.csv"
    reviewed.write_text(
        "\n".join(
            [
                "record_id;prediccion_modelo_id;prediccion_modelo_etiqueta;segunda_opcion_id;segunda_opcion_etiqueta;canonical_id_corregido;etiqueta_canonica_corregida;notas_revisor",
                "r1;tipo_1_realismo_fuerte;L1;;;;;No aplica debe limpiarse",
                "r2;tipo_2_realismo_moderado_critico;L2;;;;;insufficient_theory_signal",
                "r3;tipo_5_constructivismo_moderado;L5;;;tipo_5_constructivismo_moderado;;OK modelo",
            ]
        ),
        encoding="utf-8",
    )

    feedback = load_client_micro_review_feedback(reviewed)
    lookup = feedback.set_index("record_id")
    assert lookup.loc["r1", "review_outcome"] == REVIEW_OUTCOME_OUT_OF_SCOPE
    assert lookup.loc["r2", "review_outcome"] == REVIEW_OUTCOME_INSUFFICIENT
    assert lookup.loc["r3", "review_outcome"] == REVIEW_OUTCOME_CANONICAL
    assert lookup.loc["r3", "etiqueta_canonica_corregida"] == "Tipo 5 - Constructivismo moderado"


def test_load_client_micro_review_feedback_accepts_model_placeholder_shortcuts(
    tmp_path: Path,
) -> None:
    reviewed = tmp_path / "client_micro_reviewed.csv"
    reviewed.write_text(
        "\n".join(
            [
                "record_id;prediccion_modelo_id;prediccion_modelo_etiqueta;segunda_opcion_id;segunda_opcion_etiqueta;canonical_id_corregido;etiqueta_canonica_corregida;notas_revisor",
                "r1;tipo_2_realismo_moderado_critico;Tipo 2 - Realismo moderado / critico;;;prediccion_modelo_id;prediccion_modelo_etiqueta;",
            ]
        ),
        encoding="utf-8",
    )

    feedback = load_client_micro_review_feedback(reviewed)
    row = feedback.iloc[0]
    assert row["canonical_id_corregido"] == "tipo_2_realismo_moderado_critico"
    assert row["etiqueta_canonica_corregida"] == "Tipo 2 - Realismo moderado / critico"
    assert row["review_outcome"] == REVIEW_OUTCOME_CANONICAL
