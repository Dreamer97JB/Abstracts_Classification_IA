from __future__ import annotations

from pathlib import Path

import pandas as pd

from abstract_classifier.splits import SPLIT_OUTPUT_COLUMNS, build_split_assignments


def make_candidate_row(
    *,
    record_id: str,
    label_canonica: str,
    include_in_gold: bool,
    doi_normalized: str = "",
    title_normalized: str = "",
    year: int | None = None,
) -> dict[str, object]:
    return {
        "record_id": record_id,
        "source_dataset": "seed",
        "source_sheet": "Clasificados",
        "title": "Title",
        "abstract": "This abstract contains enough words to stay inside the gold set.",
        "year": year,
        "doi": doi_normalized,
        "label_original": "Tipo 1 RF",
        "label_canonica": label_canonica,
        "canonical_id": "tipo_1_realismo_fuerte",
        "mapping_status": "directo",
        "mapping_notes": "direct",
        "review_required": False,
        "include_in_gold": include_in_gold,
        "title_normalized": title_normalized,
        "doi_normalized": doi_normalized,
        "abstract_hash": "a" * 64,
    }


def test_build_split_assignments_keeps_same_article_groups_together(
    project_root: Path,
) -> None:
    candidate_rows = pd.DataFrame.from_records(
        [
            make_candidate_row(
                record_id="seed:Clasificados:2",
                label_canonica="Tipo 1 - Realismo fuerte",
                include_in_gold=True,
                doi_normalized="10.1000/example-a",
                year=2020,
            ),
            make_candidate_row(
                record_id="muestras:Muestras:4",
                label_canonica="Tipo 1 - Realismo fuerte",
                include_in_gold=True,
                doi_normalized="10.1000/example-a",
                year=2021,
            ),
            make_candidate_row(
                record_id="seed:Clasificados:8",
                label_canonica="Tipo 1 - Realismo fuerte",
                include_in_gold=True,
                title_normalized="sociology of science practice",
                year=2022,
            ),
            make_candidate_row(
                record_id="seed:Clasificados:9",
                label_canonica="Tipo 1 - Realismo fuerte",
                include_in_gold=False,
                title_normalized="excluded row",
                year=2023,
            ),
        ]
    )

    split_rows = build_split_assignments(candidate_rows, root=project_root)

    assert list(split_rows.columns) == SPLIT_OUTPUT_COLUMNS
    assert set(split_rows["split_version"]) == {"phase2_v1"}
    assert set(split_rows["split_seed"]) == {20260416}
    assert "seed:Clasificados:9" not in set(split_rows["record_id"])

    duplicated_group = split_rows.loc[
        split_rows["same_article_group"] == "doi:10.1000/example-a"
    ]
    assert len(duplicated_group) == 2
    assert len(set(duplicated_group["split"])) == 1


def test_prepare_command_writes_candidate_gold_and_split_outputs(
    cli_runner,
    tmp_path: Path,
) -> None:
    candidate_output = tmp_path / "candidate.csv"
    gold_output = tmp_path / "gold.csv"
    split_output = tmp_path / "split.csv"
    excluded_output = tmp_path / "excluded.csv"

    result = cli_runner(
        "prepare",
        "--candidate-output",
        str(candidate_output),
        "--gold-output",
        str(gold_output),
        "--excluded-output",
        str(excluded_output),
        "--split-output",
        str(split_output),
    )

    assert result.returncode == 0, result.stderr
    assert candidate_output.exists()
    assert gold_output.exists()
    assert excluded_output.exists()
    assert split_output.exists()

    candidate_frame = pd.read_csv(candidate_output).fillna("")
    gold_frame = pd.read_csv(gold_output).fillna("")
    split_frame = pd.read_csv(split_output).fillna("")

    assert "include_in_gold" in candidate_frame.columns
    assert not gold_frame.empty
    assert list(split_frame.columns) == SPLIT_OUTPUT_COLUMNS
