from __future__ import annotations

from pathlib import Path

from abstract_classifier.supervision import (
    CANDIDATE_OUTPUT_COLUMNS,
    build_candidate_supervision_outputs,
)


def test_candidate_supervision_output_has_expected_contract(
    project_root: Path,
) -> None:
    outputs = build_candidate_supervision_outputs(root=project_root)

    assert list(outputs.candidate_rows.columns) == CANDIDATE_OUTPUT_COLUMNS
    assert not outputs.candidate_rows.empty
    assert not outputs.gold_rows.empty
    assert not outputs.excluded_rows.empty


def test_candidate_supervision_excludes_review_and_unlabeled_rows(
    project_root: Path,
) -> None:
    outputs = build_candidate_supervision_outputs(root=project_root)
    candidate_rows = outputs.candidate_rows

    revision_manual = candidate_rows["mapping_status"] == "revision_manual"
    sin_etiqueta = candidate_rows["mapping_status"] == "sin_etiqueta"

    assert not candidate_rows.loc[revision_manual, "include_in_gold"].any()
    assert not candidate_rows.loc[sin_etiqueta, "include_in_gold"].any()


def test_candidate_supervision_populates_abstract_hash_for_non_empty_abstracts(
    project_root: Path,
) -> None:
    outputs = build_candidate_supervision_outputs(root=project_root)
    candidate_rows = outputs.candidate_rows
    rows_with_abstract = candidate_rows["abstract"].map(str.strip) != ""

    assert rows_with_abstract.any()
    assert candidate_rows.loc[rows_with_abstract, "abstract_hash"].str.len().eq(64).all()
