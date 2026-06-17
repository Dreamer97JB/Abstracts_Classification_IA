from __future__ import annotations

from pathlib import Path

import pandas as pd

from abstract_classifier.methodology import METHODOLOGY_COLUMNS
from abstract_classifier.supervision import build_candidate_supervision_outputs


def test_candidate_supervision_rows_include_methodology_review_columns(
    project_root: Path,
) -> None:
    outputs = build_candidate_supervision_outputs(root=project_root)
    candidate_rows = outputs.candidate_rows.fillna("")

    for column in METHODOLOGY_COLUMNS:
        assert column in candidate_rows.columns

    assert set(candidate_rows["methodology_label"]) == {""}
    assert set(candidate_rows["methodology_branch"]) == {""}
    assert set(candidate_rows["methodology_subtype"]) == {""}
    assert set(candidate_rows["methodology_review_required"]) == {True}
    assert set(candidate_rows["methodology_review_reason"]) == {
        "missing_source_columns"
    }


def test_prepare_command_writes_methodology_outputs(
    cli_runner,
    tmp_path: Path,
) -> None:
    methodology_output = tmp_path / "methodology.csv"
    methodology_review_output = tmp_path / "methodology_review.csv"

    result = cli_runner(
        "prepare",
        "--methodology-output",
        str(methodology_output),
        "--methodology-review-output",
        str(methodology_review_output),
    )

    assert result.returncode == 0, result.stderr
    assert methodology_output.exists()
    assert methodology_review_output.exists()

    methodology_frame = pd.read_csv(methodology_output).fillna("")
    methodology_review_frame = pd.read_csv(methodology_review_output).fillna("")

    for column in METHODOLOGY_COLUMNS:
        assert column in methodology_frame.columns
        assert column in methodology_review_frame.columns

    assert set(methodology_frame["methodology_label"]) == {""}
    assert set(methodology_review_frame["methodology_review_reason"]) == {
        "missing_source_columns"
    }
