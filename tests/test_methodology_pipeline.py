from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from abstract_classifier.methodology_pipeline import (
    build_methodology_assignments,
    load_methodology_baseline_config,
    write_methodology_outputs,
)


def test_methodology_pipeline_assigns_hierarchy_and_review_states(project_root: Path) -> None:
    config = load_methodology_baseline_config(root=project_root)
    input_rows = pd.DataFrame.from_records(
        [
            {
                "record_id": "seed:Clasificados:2",
                "title": "Conceptual foundations of science communication",
                "abstract": "This theoretical paper develops a conceptual framework and literature review for science communication.",
            },
            {
                "record_id": "seed:Clasificados:3",
                "title": "Interview study of research collaboration",
                "abstract": "This empirical study uses interviews and digital ethnography to examine collaboration.",
            },
            {
                "record_id": "seed:Clasificados:4",
                "title": "Bibliometric patterns in sociology of science",
                "abstract": "This empirical study uses bibliometric and statistical modeling to analyze citation networks.",
            },
            {
                "record_id": "seed:Clasificados:5",
                "title": "Open questions in sociology of science",
                "abstract": "This paper reflects on open questions for future research.",
            },
            {
                "record_id": "seed:Clasificados:6",
                "title": "Mixed signals in empirical research",
                "abstract": "This empirical study combines interviews and survey modeling in one design.",
            },
        ]
    )
    text_metadata = pd.DataFrame.from_records(
        [
            {
                "record_id": "seed:Clasificados:2",
                "author_keywords": "",
                "index_keywords": "",
                "keywords_available": False,
            },
            {
                "record_id": "seed:Clasificados:3",
                "author_keywords": "digital ethnography",
                "index_keywords": "",
                "keywords_available": True,
            },
            {
                "record_id": "seed:Clasificados:4",
                "author_keywords": "bibliometrics; network analysis",
                "index_keywords": "",
                "keywords_available": True,
            },
            {
                "record_id": "seed:Clasificados:5",
                "author_keywords": "",
                "index_keywords": "",
                "keywords_available": False,
            },
            {
                "record_id": "seed:Clasificados:6",
                "author_keywords": "",
                "index_keywords": "",
                "keywords_available": False,
            },
        ]
    )

    assignments = build_methodology_assignments(
        input_rows,
        config=config,
        text_metadata=text_metadata,
        root=project_root,
    )

    assignment_map = assignments.set_index("record_id")
    assert assignment_map.loc["seed:Clasificados:2", "methodology_label"] == "no_empirico"
    assert assignment_map.loc["seed:Clasificados:3", "methodology_label"] == "empirico"
    assert assignment_map.loc["seed:Clasificados:3", "methodology_subtype"] == "cualitativo"
    assert assignment_map.loc["seed:Clasificados:4", "methodology_subtype"] == "cuantitativo"
    assert assignment_map.loc["seed:Clasificados:5", "methodology_label"] == "NN"
    assert not bool(
        assignment_map.loc["seed:Clasificados:5", "methodology_review_required"]
    )
    assert assignment_map.loc["seed:Clasificados:6", "methodology_label"] == "empirico"
    assert bool(
        assignment_map.loc["seed:Clasificados:6", "methodology_review_required"]
    )
    assert assignment_map.loc["seed:Clasificados:6", "methodology_review_reason"] == (
        "conflicting_cues"
    )


def test_methodology_pipeline_writes_optional_evaluation_bundle(
    project_root: Path,
    tmp_path: Path,
) -> None:
    config = load_methodology_baseline_config(root=project_root)
    input_rows = pd.DataFrame.from_records(
        [
            {
                "record_id": "seed:Clasificados:2",
                "title": "Conceptual science communication review",
                "abstract": "This theoretical paper develops a conceptual framework and literature review.",
            },
            {
                "record_id": "seed:Clasificados:3",
                "title": "Interview study of collaboration",
                "abstract": "This empirical study uses interviews and ethnography.",
            },
            {
                "record_id": "seed:Clasificados:4",
                "title": "Bibliometric patterns",
                "abstract": "This empirical study uses bibliometric and statistical modeling.",
            },
            {
                "record_id": "seed:Clasificados:5",
                "title": "Open questions",
                "abstract": "This paper reflects on open questions.",
            },
        ]
    )
    text_metadata = pd.DataFrame.from_records(
        [
            {
                "record_id": record_id,
                "author_keywords": "",
                "index_keywords": "",
                "keywords_available": False,
            }
            for record_id in input_rows["record_id"].tolist()
        ]
    )
    assignments = build_methodology_assignments(
        input_rows,
        config=config,
        text_metadata=text_metadata,
        root=project_root,
    )
    reviewed_labels = pd.DataFrame.from_records(
        [
            {
                "record_id": "seed:Clasificados:2",
                "methodology_label": "no_empirico",
                "methodology_subtype": "",
            },
            {
                "record_id": "seed:Clasificados:3",
                "methodology_label": "empirico",
                "methodology_subtype": "cualitativo",
            },
            {
                "record_id": "seed:Clasificados:4",
                "methodology_label": "empirico",
                "methodology_subtype": "cuantitativo",
            },
            {
                "record_id": "seed:Clasificados:5",
                "methodology_label": "NN",
                "methodology_subtype": "",
            },
        ]
    )

    artifacts = write_methodology_outputs(
        assignments,
        run_dir=tmp_path,
        reviewed_labels=reviewed_labels,
        root=project_root,
    )

    assert artifacts.assignments_path.exists()
    assert artifacts.review_queue_path.exists()
    assert artifacts.summary_path.exists()
    assert artifacts.metrics_paths["metrics_overall"].exists()
    assert artifacts.metrics_paths["metrics_per_class"].exists()
    assert artifacts.metrics_paths["confusion_matrix"].exists()
    assert artifacts.metrics_paths["review_predictions"].exists()
    assert artifacts.metrics_paths["subtype_metrics"].exists()
    assert artifacts.metrics_paths["subtype_confusion_matrix"].exists()

    summary = json.loads(artifacts.summary_path.read_text(encoding="utf-8"))
    assert summary["evaluation_status"] == "completed"
