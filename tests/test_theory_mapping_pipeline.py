from __future__ import annotations

from pathlib import Path

import pandas as pd

from abstract_classifier.supervision import (
    THEORY_OUTPUT_COLUMNS,
    build_theory_mapping_outputs,
)


def test_build_theory_mapping_outputs_emits_expected_columns(
    project_root: Path,
) -> None:
    outputs = build_theory_mapping_outputs(root=project_root)

    assert list(outputs.canonical_rows.columns) == THEORY_OUTPUT_COLUMNS
    assert list(outputs.review_rows.columns) == THEORY_OUTPUT_COLUMNS
    assert not outputs.canonical_rows.empty
    assert not outputs.review_rows.empty
    assert outputs.review_rows["review_required"].all()


def test_theory_mapping_outputs_keep_unresolved_rows_visible(
    project_root: Path,
) -> None:
    outputs = build_theory_mapping_outputs(root=project_root)
    grouped = (
        outputs.canonical_rows.assign(
            label_original_stripped=outputs.canonical_rows["label_original"].map(str.strip)
        )
        .groupby("label_original_stripped", dropna=False)["mapping_status"]
        .agg(lambda values: sorted(set(values)))
        .to_dict()
    )

    assert grouped["Tipo 2 RM"] == ["fusionado"]
    assert grouped["Tipo 2 RC"] == ["fusionado"]
    assert grouped["Tipo 6 CF - R"] == ["directo"]
    assert grouped["Tipo 6 RF"] == ["revision_manual"]
    assert grouped["Tipo 4 CM"] == ["revision_manual"]
    assert grouped["No"] == ["sin_etiqueta"]
    assert grouped[""] == ["sin_etiqueta"]


def test_prepare_command_writes_theory_and_review_outputs(
    cli_runner,
    tmp_path: Path,
) -> None:
    theory_output = tmp_path / "theory.csv"
    review_output = tmp_path / "theory_review.csv"

    result = cli_runner(
        "prepare",
        "--theory-output",
        str(theory_output),
        "--theory-review-output",
        str(review_output),
    )

    assert result.returncode == 0, result.stderr
    assert theory_output.exists()
    assert review_output.exists()

    theory_frame = pd.read_csv(theory_output).fillna("")
    review_frame = pd.read_csv(review_output).fillna("")

    assert list(theory_frame.columns) == THEORY_OUTPUT_COLUMNS
    assert list(review_frame.columns) == THEORY_OUTPUT_COLUMNS
    assert {"revision_manual", "sin_etiqueta"}.issuperset(
        set(review_frame["mapping_status"])
    )
