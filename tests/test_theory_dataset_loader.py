from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pandas as pd
import pytest

from abstract_classifier.training import load_theory_baseline_config, load_theory_dataset


def test_theory_dataset_loader_reuses_frozen_phase2_split(
    project_root: Path,
) -> None:
    config = load_theory_baseline_config(project_root / "configs" / "theory_baseline.toml")
    dataset = load_theory_dataset(config, root=project_root)

    assert dataset.split_version == "phase2_v1"
    assert dataset.split_seed == 20260416
    assert len(dataset.rows) == 157
    assert len(dataset.rows_for_split("train")) == 109
    assert len(dataset.rows_for_split("val")) == 24
    assert len(dataset.rows_for_split("test")) == 24
    assert dataset.label_order == (
        "tipo_1_realismo_fuerte",
        "tipo_2_realismo_moderado_critico",
        "tipo_3_antirrealismo_epistemologico",
        "tipo_4_pragmatismo_epistemologico",
        "tipo_5_constructivismo_moderado",
        "tipo_6_constructivismo_fuerte_relativismo",
    )


def test_theory_dataset_loader_rejects_missing_record_ids(
    project_root: Path,
    tmp_path: Path,
) -> None:
    config = load_theory_baseline_config(project_root / "configs" / "theory_baseline.toml")
    broken_gold_path = tmp_path / "broken_gold.csv"
    broken_gold = pd.read_csv(config.gold_artifact_path)
    broken_gold.loc[0, "record_id"] = ""
    broken_gold.to_csv(broken_gold_path, index=False, encoding="utf-8")

    broken_config = replace(config, gold_artifact_path=broken_gold_path)

    with pytest.raises(ValueError, match="missing record_id"):
        load_theory_dataset(broken_config, root=project_root)


def test_theory_dataset_loader_rejects_gold_split_mismatches(
    project_root: Path,
    tmp_path: Path,
) -> None:
    config = load_theory_baseline_config(project_root / "configs" / "theory_baseline.toml")
    broken_split_path = tmp_path / "broken_split.csv"
    broken_split = pd.read_csv(config.split_artifact_path).iloc[1:].copy()
    broken_split.to_csv(broken_split_path, index=False, encoding="utf-8")

    broken_config = replace(config, split_artifact_path=broken_split_path)

    with pytest.raises(ValueError, match="same record ids"):
        load_theory_dataset(broken_config, root=project_root)
