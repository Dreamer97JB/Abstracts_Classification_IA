from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from abstract_classifier.client_reporting import (
    build_client_reporting_bundle,
    load_client_reporting_config,
)


def test_client_reporting_bundle_writes_simplified_outputs(
    project_root: Path,
    tmp_path: Path,
) -> None:
    config = load_client_reporting_config(root=project_root)
    methodology_assignments = pd.DataFrame.from_records(
        [
            {
                "record_id": "corpus:1",
                "source_dataset": "scopus_base",
                "source_sheet": "Base",
                "title": "Knowledge networks in science",
                "year": 2020,
                "doi": "10.1000/one",
                "authors": "A Author; B Author",
                "journal": "Journal A",
                "predicted_canonical_id": "tipo_5_constructivismo_moderado",
                "predicted_label_canonica": "Tipo 5 - Constructivismo moderado",
                "prediction_score": 0.82,
                "second_predicted_canonical_id": "tipo_4_pragmatismo_epistemologico",
                "second_predicted_label_canonica": "Tipo 4 - Pragmatismo epistemologico",
                "second_prediction_score": 0.11,
                "prediction_margin": 0.71,
                "needs_review": False,
                "review_reason": "",
                "methodology_label": "empirico",
                "methodology_subtype": "cuantitativo",
                "methodology_review_required": False,
                "methodology_review_reason": "",
                "author_keywords": "knowledge networks; collaboration",
                "index_keywords": "",
                "references": "Smith J., Example reference; Jones M., Another reference",
                "model_run_id": "smoke_train",
                "prediction_run_id": "smoke_phase5",
            },
            {
                "record_id": "corpus:2",
                "source_dataset": "google_corpus",
                "source_sheet": "Base",
                "title": "Pragmatism and method",
                "year": 2021,
                "doi": "10.1000/two",
                "authors": "C Author, D Author",
                "journal": "Journal B",
                "predicted_canonical_id": "tipo_4_pragmatismo_epistemologico",
                "predicted_label_canonica": "Tipo 4 - Pragmatismo epistemologico",
                "prediction_score": 0.44,
                "second_predicted_canonical_id": "tipo_2_realismo_moderado_critico",
                "second_predicted_label_canonica": "Tipo 2 - Realismo moderado / critico",
                "second_prediction_score": 0.40,
                "prediction_margin": 0.04,
                "needs_review": True,
                "review_reason": "low_confidence | taxonomy_conflict",
                "methodology_label": "no_empirico",
                "methodology_subtype": "",
                "methodology_review_required": False,
                "methodology_review_reason": "",
                "author_keywords": "",
                "index_keywords": "pragmatism, epistemology",
                "references": "Taylor R., Reference note",
                "model_run_id": "smoke_train",
                "prediction_run_id": "smoke_phase5",
            },
        ]
    )
    theme_assignments = pd.DataFrame.from_records(
        [
            {
                "record_id": "corpus:1",
                "theme_rank": 1,
                "theme_label": "knowledge networks",
                "theme_source": "keyword",
                "predicted_label_canonica": "Tipo 5 - Constructivismo moderado",
            },
            {
                "record_id": "corpus:2",
                "theme_rank": 1,
                "theme_label": "epistemology",
                "theme_source": "keyword",
                "predicted_label_canonica": "Tipo 4 - Pragmatismo epistemologico",
            },
        ]
    )
    theme_summary = pd.DataFrame.from_records(
        [
            {
                "theme_label": "knowledge networks",
                "theme_source": "keyword",
                "record_count": 1,
                "assignment_count": 1,
            },
            {
                "theme_label": "epistemology",
                "theme_source": "keyword",
                "record_count": 1,
                "assignment_count": 1,
            },
        ]
    )

    artifacts = build_client_reporting_bundle(
        input_rows=methodology_assignments,
        methodology_assignments=methodology_assignments,
        theme_assignments=theme_assignments,
        theme_summary=theme_summary,
        run_dir=tmp_path,
        config=config,
        root=project_root,
        context={"analysis_run_id": "analysis_smoke", "input_artifact": "predictions.csv"},
    )

    assert artifacts.client_results_path.exists()
    assert artifacts.report_path.exists()
    client_results = pd.read_csv(artifacts.client_results_path)
    assert {
        "client_theory_label",
        "primary_theme",
        "client_review_required",
        "analysis_run_id",
    } <= set(client_results.columns)

    summary = json.loads(artifacts.summary_path.read_text(encoding="utf-8"))
    assert summary["row_count"] == 2
    assert summary["review_counts"]["client_review_required"] == 1
