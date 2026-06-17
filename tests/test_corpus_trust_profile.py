from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from abstract_classifier.corpus_trust import (
    build_corpus_trust_profile,
    load_corpus_trust_config,
)


def _write_config(tmp_path: Path) -> Path:
    input_path = tmp_path / "phase5_input.csv"
    overlap_path = tmp_path / "overlap.csv"
    summary_path = tmp_path / "summary.json"
    config_path = tmp_path / "corpus_trust.toml"
    summary_path.write_text(
        json.dumps(
            {
                "inference_row_count": 4,
                "manual_overlap_review_count": 1,
                "exact_merge_decision_count": 0,
                "keyword_coverage": {"keyword_availability_rate": 0.5},
            }
        ),
        encoding="utf-8",
    )
    config_path.write_text(
        "\n".join(
            [
                'version = "test"',
                f'phase5_inference_input = "{input_path.as_posix()}"',
                f'phase5_overlap_review = "{overlap_path.as_posix()}"',
                f'phase5_summary = "{summary_path.as_posix()}"',
                f'default_output_root = "{(tmp_path / "out").as_posix()}"',
                "",
                "[rules]",
                "min_abstract_words = 10",
                "experiment_min_metadata_fields = 2",
                "production_min_metadata_fields = 3",
                "exclude_ambiguous_overlap = true",
                "production_requires_year = true",
            ]
        ),
        encoding="utf-8",
    )
    return config_path


def test_build_corpus_trust_profile_assigns_expected_statuses(tmp_path: Path) -> None:
    config = load_corpus_trust_config(_write_config(tmp_path), root=tmp_path)

    corpus_frame = pd.DataFrame.from_records(
        [
            {
                "record_id": "trusted:1",
                "source_dataset": "scopus_base",
                "source_sheet": "Base",
                "source_path": "fixture.xlsx",
                "source_role": "corpus",
                "source_system": "scopus",
                "title": "A fully described paper",
                "abstract": "This abstract contains enough words to pass the configured threshold cleanly today.",
                "authors": "A Author",
                "doi": "10.1/abc",
                "doi_normalized": "10.1/abc",
                "journal": "Journal",
                "author_keywords": "science; sociology",
                "index_keywords": "",
                "references": "Ref 1",
                "year": 2020,
                "merge_cluster_size": 1,
                "merge_status": "unique",
            },
            {
                "record_id": "thin:1",
                "source_dataset": "google_corpus",
                "source_sheet": "Sheet1",
                "source_path": "fixture.xlsx",
                "source_role": "corpus",
                "source_system": "google_scholar",
                "title": "Thin abstract paper",
                "abstract": "Too short",
                "authors": "A Author",
                "doi": "",
                "doi_normalized": "",
                "journal": "Journal",
                "author_keywords": "",
                "index_keywords": "",
                "references": "",
                "year": 2020,
                "merge_cluster_size": 1,
                "merge_status": "unique",
            },
            {
                "record_id": "soft:1",
                "source_dataset": "google_corpus",
                "source_sheet": "Sheet1",
                "source_path": "fixture.xlsx",
                "source_role": "corpus",
                "source_system": "google_scholar",
                "title": "Soft warning paper",
                "abstract": "This abstract has enough words to survive the experiment view but still lacks production metadata.",
                "authors": "",
                "doi": "",
                "doi_normalized": "",
                "journal": "Journal",
                "author_keywords": "",
                "index_keywords": "",
                "references": "",
                "year": 2020,
                "merge_cluster_size": 1,
                "merge_status": "unique",
            },
            {
                "record_id": "ambiguous:1",
                "source_dataset": "scopus_base",
                "source_sheet": "Base",
                "source_path": "fixture.xlsx",
                "source_role": "corpus",
                "source_system": "scopus",
                "title": "Ambiguous overlap paper",
                "abstract": "This abstract also has enough words but will be excluded because the overlap remains unresolved for trust purposes.",
                "authors": "B Author",
                "doi": "10.1/xyz",
                "doi_normalized": "10.1/xyz",
                "journal": "Journal",
                "author_keywords": "knowledge",
                "index_keywords": "",
                "references": "Ref 2",
                "year": 2021,
                "merge_cluster_size": 2,
                "merge_status": "exact_merged",
            },
        ]
    )
    overlap_review = pd.DataFrame.from_records(
        [
            {
                "left_record_id": "raw:left",
                "right_record_id": "raw:right",
                "left_winner_record_id": "ambiguous:1",
                "right_winner_record_id": "ambiguous:1",
            }
        ]
    )

    profile = build_corpus_trust_profile(
        corpus_frame,
        overlap_review,
        config=config,
    ).set_index("record_id")

    assert bool(profile.loc["trusted:1", "include_in_experiment"])
    assert bool(profile.loc["trusted:1", "include_in_production"])
    assert profile.loc["trusted:1", "trust_status"] == "trusted"

    assert not bool(profile.loc["thin:1", "include_in_experiment"])
    assert "abstract_too_thin" in profile.loc["thin:1", "experiment_exclusion_reason"]
    assert profile.loc["thin:1", "trust_status"] == "excluded"

    assert bool(profile.loc["soft:1", "include_in_experiment"])
    assert not bool(profile.loc["soft:1", "include_in_production"])
    assert profile.loc["soft:1", "production_exclusion_reason"] == "metadata_poor_production"
    assert profile.loc["soft:1", "trust_status"] == "review"

    assert not bool(profile.loc["ambiguous:1", "include_in_experiment"])
    assert "ambiguous_overlap_exposure" in profile.loc[
        "ambiguous:1", "experiment_exclusion_reason"
    ]
    assert bool(profile.loc["ambiguous:1", "large_merge_cluster"])
