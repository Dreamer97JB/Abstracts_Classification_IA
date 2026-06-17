from __future__ import annotations

from pathlib import Path

import pandas as pd

from abstract_classifier.text_variants import (
    build_text_variant_frame,
    load_governed_text_metadata,
    summarize_keyword_coverage,
)
from abstract_classifier.training import load_theory_baseline_config, load_theory_dataset


def test_text_variants_preserve_seed_rows_and_enrich_muestras_when_keywords_exist(
    project_root: Path,
) -> None:
    config = load_theory_baseline_config(project_root / "configs" / "theory_baseline.toml")
    dataset = load_theory_dataset(config, root=project_root)
    metadata = load_governed_text_metadata(
        root=project_root,
        supervision_config_path=config.supervision_config_path,
    )

    abstract_only = build_text_variant_frame(
        dataset.rows,
        text_variant="abstract_only",
        text_metadata=metadata,
    )
    abstract_plus_keywords = build_text_variant_frame(
        dataset.rows,
        text_variant="abstract_plus_keywords",
        text_metadata=metadata,
    )
    title_abstract_plus_keywords = build_text_variant_frame(
        dataset.rows,
        text_variant="title_abstract_plus_keywords",
        text_metadata=metadata,
    )

    seed_row = abstract_plus_keywords.loc[abstract_plus_keywords["source_dataset"] == "seed"].iloc[0]
    title_seed_row = title_abstract_plus_keywords.loc[
        title_abstract_plus_keywords["source_dataset"] == "seed"
    ].iloc[0]
    assert not bool(seed_row["keywords_available"])
    assert seed_row["text_input"] == seed_row["abstract"]
    assert title_seed_row["text_input"] == (
        f"{title_seed_row['title']}\n\n{title_seed_row['abstract']}"
    )

    enriched_row = abstract_plus_keywords.loc[
        (abstract_plus_keywords["source_dataset"] == "muestras")
        & abstract_plus_keywords["keywords_available"]
    ].iloc[0]
    title_enriched_row = title_abstract_plus_keywords.loc[
        title_abstract_plus_keywords["record_id"] == enriched_row["record_id"]
    ].iloc[0]
    if enriched_row["author_keywords"]:
        assert enriched_row["author_keywords"] in enriched_row["text_input"]
    else:
        assert enriched_row["index_keywords"] in enriched_row["text_input"]
    assert title_enriched_row["text_input"].startswith(
        f"{title_enriched_row['title']}\n\n{title_enriched_row['abstract']}"
    )
    if title_enriched_row["author_keywords"]:
        assert title_enriched_row["author_keywords"] in title_enriched_row["text_input"]
    else:
        assert title_enriched_row["index_keywords"] in title_enriched_row["text_input"]

    abstract_only_summary = summarize_keyword_coverage(
        abstract_only,
        text_variant="abstract_only",
    )
    enriched_summary = summarize_keyword_coverage(
        abstract_plus_keywords,
        text_variant="abstract_plus_keywords",
    )
    title_enriched_summary = summarize_keyword_coverage(
        title_abstract_plus_keywords,
        text_variant="title_abstract_plus_keywords",
    )

    assert abstract_only_summary.keyword_coverage_rate == 0.0
    assert title_enriched_summary.keyword_coverage_rate == enriched_summary.keyword_coverage_rate
    seed_summaries = [
        item for item in enriched_summary.by_source_split if item["source_dataset"] == "seed"
    ]
    muestras_summaries = [
        item for item in enriched_summary.by_source_split if item["source_dataset"] == "muestras"
    ]
    assert all(item["keyword_rows_available"] == 0 for item in seed_summaries)
    assert any(item["keyword_rows_available"] > 0 for item in muestras_summaries)


def test_text_variants_accept_inline_keyword_metadata_without_external_join() -> None:
    dataset_rows = pd.DataFrame.from_records(
        [
            {
                "record_id": "corpus:row:1",
                "source_dataset": "scopus_base",
                "title": "Networks of science",
                "abstract": "Empirical science networks reveal collaboration patterns.",
                "author_keywords": "science networks; collaboration",
                "index_keywords": "",
                "keywords_available": True,
            },
            {
                "record_id": "corpus:row:2",
                "source_dataset": "google_corpus",
                "title": "Theory without keywords",
                "abstract": "A conceptual reflection on scientific realism.",
                "author_keywords": "",
                "index_keywords": "",
                "keywords_available": False,
            },
        ]
    )

    variant_rows = build_text_variant_frame(
        dataset_rows,
        text_variant="abstract_plus_keywords",
        text_metadata=None,
    )

    first_row = variant_rows.set_index("record_id").loc["corpus:row:1"]
    assert first_row["keywords_applied"]
    assert "science networks" in first_row["text_input"]

    second_row = variant_rows.set_index("record_id").loc["corpus:row:2"]
    assert not second_row["keywords_applied"]
    assert second_row["text_input"] == second_row["abstract"]


def test_title_abstract_plus_keywords_preserves_order_and_falls_back_cleanly() -> None:
    dataset_rows = pd.DataFrame.from_records(
        [
            {
                "record_id": "corpus:row:1",
                "source_dataset": "scopus_base",
                "title": "Scientific realism revisited",
                "abstract": "A study of realist commitments in practice.",
                "author_keywords": "realism; ontology",
                "index_keywords": "epistemology",
                "keywords_available": True,
            },
            {
                "record_id": "corpus:row:2",
                "source_dataset": "google_corpus",
                "title": "",
                "abstract": "Constructivist debates in sociology of science.",
                "author_keywords": "",
                "index_keywords": "",
                "keywords_available": False,
            },
        ]
    )

    variant_rows = build_text_variant_frame(
        dataset_rows,
        text_variant="title_abstract_plus_keywords",
        text_metadata=None,
    ).set_index("record_id")

    first_row = variant_rows.loc["corpus:row:1"]
    assert first_row["keywords_applied"]
    assert first_row["text_input"].startswith(
        "Scientific realism revisited\n\nA study of realist commitments in practice."
    )
    assert "Author Keywords: realism; ontology" in first_row["text_input"]
    assert "Index Keywords: epistemology" in first_row["text_input"]

    second_row = variant_rows.loc["corpus:row:2"]
    assert not second_row["keywords_applied"]
    assert second_row["text_input"] == second_row["abstract"]
