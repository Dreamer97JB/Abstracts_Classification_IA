from __future__ import annotations

from pathlib import Path

import pandas as pd

from abstract_classifier.theme_analysis import build_theme_outputs, load_theme_pipeline_config


def test_theme_analysis_prefers_keywords_and_falls_back_to_tfidf(
    project_root: Path,
) -> None:
    config = load_theme_pipeline_config(root=project_root)
    input_rows = pd.DataFrame.from_records(
        [
            {
                "record_id": "seed:Clasificados:2",
                "source_dataset": "seed",
                "source_sheet": "Clasificados",
                "title": "Science communication in a pandemic",
                "abstract": "This article reviews science communication during the pandemic.",
                "canonical_id": "tipo_4_pragmatismo_epistemologico",
                "label_canonica": "Tipo 4 - Pragmatismo epistemologico",
            },
            {
                "record_id": "seed:Clasificados:3",
                "source_dataset": "seed",
                "source_sheet": "Clasificados",
                "title": "Scientometric models of citation networks",
                "abstract": "Citation networks and bibliometric modeling reveal scientific collaboration patterns.",
                "canonical_id": "tipo_2_realismo_moderado_critico",
                "label_canonica": "Tipo 2 - Realismo moderado / critico",
            },
        ]
    )
    text_metadata = pd.DataFrame.from_records(
        [
            {
                "record_id": "seed:Clasificados:2",
                "author_keywords": "science communication; covid-19",
                "index_keywords": "",
                "keywords_available": True,
            },
            {
                "record_id": "seed:Clasificados:3",
                "author_keywords": "",
                "index_keywords": "",
                "keywords_available": False,
            },
        ]
    )

    assignments, summary = build_theme_outputs(
        input_rows,
        config=config,
        text_metadata=text_metadata,
        root=project_root,
    )

    keyword_rows = assignments.loc[assignments["record_id"] == "seed:Clasificados:2"]
    assert "science communication" in keyword_rows["theme_label"].tolist()
    assert set(keyword_rows["theme_source"]) == {"keyword"}

    fallback_rows = assignments.loc[assignments["record_id"] == "seed:Clasificados:3"]
    assert not fallback_rows.empty
    assert set(fallback_rows["theme_source"]) == {"tfidf"}
    assert summary["record_count"].sum() >= 2
