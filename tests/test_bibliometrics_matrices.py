from __future__ import annotations

from pathlib import Path

import pandas as pd

from abstract_classifier.bibliometrics import build_bibliometric_outputs, load_bibliometric_config


def test_bibliometrics_generates_matrix_percentages(project_root: Path) -> None:
    config = load_bibliometric_config(root=project_root)
    frame = pd.DataFrame(
        [
            {
                "record_id": "r1",
                "title": "Covid realism",
                "abstract": "Covid policy and realism",
                "authors": "Alpha, A.",
                "references": "Latour, B. (2005). Reassembling the social.",
                "author_keywords": "covid; policy",
                "index_keywords": "epistemology",
                "themes": "covid | policy",
                "predicted_canonical_id": "tipo_1",
                "predicted_label_canonica": "Tipo 1",
            },
            {
                "record_id": "r2",
                "title": "Covid constructivism",
                "abstract": "Covid and knowledge",
                "authors": "Beta, B.",
                "references": "Latour, B. (2005). Reassembling the social.",
                "author_keywords": "covid",
                "index_keywords": "knowledge",
                "themes": "covid",
                "predicted_canonical_id": "tipo_2",
                "predicted_label_canonica": "Tipo 2",
            },
        ]
    )

    outputs = build_bibliometric_outputs(frame, config=config)

    covid_theme = outputs.theme_label_matrix.loc[
        (outputs.theme_label_matrix["theme"] == "covid")
        & (outputs.theme_label_matrix["label_id"] == "tipo_1")
    ].iloc[0]
    latour_label = outputs.author_label_matrix.loc[
        (outputs.author_label_matrix["cited_author_display"] == "Latour, B")
        & (outputs.author_label_matrix["label_id"] == "tipo_1")
    ].iloc[0]

    assert round(float(covid_theme["share_within_theme"]), 3) == 0.5
    assert round(float(covid_theme["share_within_label"]), 3) == 1.0
    assert round(float(latour_label["share_within_author"]), 3) == 0.5
    assert round(float(latour_label["share_within_label"]), 3) == 1.0
    assert set(outputs.keyword_label_matrix["keyword_source"]) >= {
        "AUTHOR_KEYWORD",
        "INDEX_KEYWORD",
        "TFIDF_TERM",
    }


def test_bibliometrics_derives_themes_from_keywords_when_missing(project_root: Path) -> None:
    config = load_bibliometric_config(root=project_root)
    frame = pd.DataFrame(
        [
            {
                "record_id": "r1",
                "title": "STS and policy",
                "abstract": "Science policy and sociology",
                "authors": "Alpha, A.",
                "references": "Latour, B. (2005). Reassembling the social.",
                "author_keywords": "science policy; sts",
                "index_keywords": "human",
                "predicted_canonical_id": "tipo_1",
                "predicted_label_canonica": "Tipo 1",
            },
            {
                "record_id": "r2",
                "title": "STS methods",
                "abstract": "Methods in science policy",
                "authors": "Beta, B.",
                "references": "Latour, B. (2005). Reassembling the social.",
                "author_keywords": "science policy",
                "index_keywords": "article",
                "predicted_canonical_id": "tipo_2",
                "predicted_label_canonica": "Tipo 2",
            },
        ]
    )

    outputs = build_bibliometric_outputs(frame, config=config)

    assert not outputs.theme_label_matrix.empty
    assert "science policy" in set(outputs.theme_label_matrix["theme"])
    assert outputs.descriptive_stats["theme_assignment_summary"]["articles_with_derived_keyword_themes"] == 2
