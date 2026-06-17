from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from abstract_classifier.corpus_trust import load_corpus_trust_config, run_corpus_trust


def test_run_corpus_trust_persists_views_and_manifest(tmp_path: Path) -> None:
    phase5_input = tmp_path / "phase5_input.csv"
    overlap_review = tmp_path / "overlap.csv"
    phase5_summary = tmp_path / "summary.json"
    config_path = tmp_path / "corpus_trust.toml"

    pd.DataFrame.from_records(
        [
            {
                "record_id": "keep:1",
                "source_dataset": "scopus_base",
                "source_sheet": "Base",
                "source_path": "fixture.xlsx",
                "source_role": "corpus",
                "source_system": "scopus",
                "title": "Keep me",
                "abstract": "This abstract contains enough words to remain in both trusted views with no exclusions at all.",
                "authors": "A Author",
                "doi": "10.1/keep",
                "doi_normalized": "10.1/keep",
                "journal": "Journal",
                "author_keywords": "science",
                "index_keywords": "",
                "references": "Ref 1",
                "year": 2020,
                "merge_cluster_size": 1,
                "merge_status": "unique",
            },
            {
                "record_id": "prod_only_drop:1",
                "source_dataset": "google_corpus",
                "source_sheet": "Sheet1",
                "source_path": "fixture.xlsx",
                "source_role": "corpus",
                "source_system": "google_scholar",
                "title": "Drop only from production",
                "abstract": "This abstract contains enough words to stay in the experiment view while still failing the stricter production metadata threshold.",
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
                "record_id": "drop:1",
                "source_dataset": "google_corpus",
                "source_sheet": "Sheet1",
                "source_path": "fixture.xlsx",
                "source_role": "corpus",
                "source_system": "google_scholar",
                "title": "Drop from both",
                "abstract": "short",
                "authors": "",
                "doi": "",
                "doi_normalized": "",
                "journal": "",
                "author_keywords": "",
                "index_keywords": "",
                "references": "",
                "year": None,
                "merge_cluster_size": 1,
                "merge_status": "unique",
            },
        ]
    ).to_csv(phase5_input, index=False, encoding="utf-8")
    pd.DataFrame.from_records(
        [
            {
                "left_record_id": "raw:left",
                "right_record_id": "raw:right",
                "left_winner_record_id": "prod_only_drop:1",
                "right_winner_record_id": "keep:1",
            }
        ]
    ).to_csv(overlap_review, index=False, encoding="utf-8")
    phase5_summary.write_text(
        json.dumps(
            {
                "inference_row_count": 3,
                "manual_overlap_review_count": 1,
                "exact_merge_decision_count": 0,
                "keyword_coverage": {"keyword_availability_rate": 1 / 3},
            }
        ),
        encoding="utf-8",
    )
    config_path.write_text(
        "\n".join(
            [
                'version = "test"',
                f'phase5_inference_input = "{phase5_input.as_posix()}"',
                f'phase5_overlap_review = "{overlap_review.as_posix()}"',
                f'phase5_summary = "{phase5_summary.as_posix()}"',
                f'default_output_root = "{(tmp_path / "out").as_posix()}"',
                "",
                "[rules]",
                "min_abstract_words = 10",
                "experiment_min_metadata_fields = 2",
                "production_min_metadata_fields = 3",
                "exclude_ambiguous_overlap = false",
                "production_requires_year = true",
            ]
        ),
        encoding="utf-8",
    )

    config = load_corpus_trust_config(config_path, root=tmp_path)
    artifacts = run_corpus_trust(
        config=config,
        run_id="phase6_test",
        output_dir=tmp_path / "artifacts",
        root=tmp_path,
    )

    assert artifacts.trust_profile_path.exists()
    assert artifacts.excluded_rows_path.exists()
    assert artifacts.trusted_experiment_path.exists()
    assert artifacts.trusted_production_path.exists()
    assert artifacts.summary_path.exists()
    assert artifacts.comparison_summary_path.exists()
    assert artifacts.manifest_path.exists()

    trusted_experiment = pd.read_csv(artifacts.trusted_experiment_path, encoding="utf-8")
    trusted_production = pd.read_csv(artifacts.trusted_production_path, encoding="utf-8")
    excluded_rows = pd.read_csv(artifacts.excluded_rows_path, encoding="utf-8")
    manifest = json.loads(artifacts.manifest_path.read_text(encoding="utf-8"))
    comparison = json.loads(
        artifacts.comparison_summary_path.read_text(encoding="utf-8")
    )

    assert {"record_id", "source_dataset", "source_sheet", "source_path", "source_role"}.issubset(
        trusted_experiment.columns
    )
    assert len(trusted_experiment) == 2
    assert len(trusted_production) == 1
    assert len(excluded_rows) == 2
    assert manifest["artifacts"]["trusted_experiment_corpus"] == "trusted_experiment_corpus.csv"
    assert comparison["phase6_trusted_production"]["row_count"] == 1
    assert comparison["delta_vs_phase5"]["production_exclusion_reason_counts"][
        "metadata_poor_production"
    ] == 2
