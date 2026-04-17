from __future__ import annotations

from pathlib import Path

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

    seed_row = abstract_plus_keywords.loc[abstract_plus_keywords["source_dataset"] == "seed"].iloc[0]
    assert not bool(seed_row["keywords_available"])
    assert seed_row["text_input"] == seed_row["abstract"]

    enriched_row = abstract_plus_keywords.loc[
        (abstract_plus_keywords["source_dataset"] == "muestras")
        & abstract_plus_keywords["keywords_available"]
    ].iloc[0]
    if enriched_row["author_keywords"]:
        assert enriched_row["author_keywords"] in enriched_row["text_input"]
    else:
        assert enriched_row["index_keywords"] in enriched_row["text_input"]

    abstract_only_summary = summarize_keyword_coverage(
        abstract_only,
        text_variant="abstract_only",
    )
    enriched_summary = summarize_keyword_coverage(
        abstract_plus_keywords,
        text_variant="abstract_plus_keywords",
    )

    assert abstract_only_summary.keyword_coverage_rate == 0.0
    seed_summaries = [
        item for item in enriched_summary.by_source_split if item["source_dataset"] == "seed"
    ]
    muestras_summaries = [
        item for item in enriched_summary.by_source_split if item["source_dataset"] == "muestras"
    ]
    assert all(item["keyword_rows_available"] == 0 for item in seed_summaries)
    assert any(item["keyword_rows_available"] > 0 for item in muestras_summaries)
