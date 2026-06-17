from __future__ import annotations

from pathlib import Path

import pandas as pd

from abstract_classifier.bibliometrics import (
    build_author_frequency,
    build_bibliometric_outputs,
    extract_cited_authors,
    load_bibliometric_config,
    parse_references,
    resolve_bibliometric_columns,
)


def test_bibliometrics_separates_corpus_vs_cited_author_metrics(project_root: Path) -> None:
    config = load_bibliometric_config(root=project_root)
    frame = pd.DataFrame(
        [
            {
                "record_id": "r1",
                "title": "Paper 1",
                "abstract": "Theory and science",
                "authors": "Smith, J.; Brown, P.",
                "references": "Latour, B. (2005). Reassembling the social.; Merton, R. (1973). Sociology of science.",
                "predicted_canonical_id": "tipo_1",
                "predicted_label_canonica": "Tipo 1",
            },
            {
                "record_id": "r2",
                "title": "Paper 2",
                "abstract": "Science studies",
                "authors": "Smith, J.; Clark, T.",
                "references": "Latour, B. (2005). Reassembling the social.",
                "predicted_canonical_id": "tipo_2",
                "predicted_label_canonica": "Tipo 2",
            },
        ]
    )

    outputs = build_bibliometric_outputs(frame, config=config)

    smith = outputs.corpus_author_frequency.loc[
        outputs.corpus_author_frequency["author_display"] == "Smith, J."
    ].iloc[0]
    latour = outputs.cited_author_frequency.loc[
        outputs.cited_author_frequency["author_display"] == "Latour, B"
    ].iloc[0]

    assert smith["corpus_author_count"] == 2
    assert smith["article_count"] == 2
    assert latour["cited_author_count"] == 2
    assert latour["article_citation_coverage"] == 2


def test_build_author_frequency_handles_empty_frames() -> None:
    empty = build_author_frequency(pd.DataFrame(), mention_source="CITED_AUTHOR")

    assert list(empty.columns) == [
        "author_key",
        "author_display",
        "cited_author_count",
        "article_citation_coverage",
    ]
