from __future__ import annotations

from pathlib import Path

import pandas as pd

from abstract_classifier.pseudo_label_merge import merge_prediction_csvs


def _row(rid: str, run: str, pred: str) -> dict:
    return {
        "record_id": rid,
        "model_run_id": run,
        "predicted_canonical_id": pred,
        "prediction_margin": 0.5,
        "calibrated_prediction_score": 0.8,
    }


def test_merge_prediction_csvs_concat_two_runs(tmp_path: Path) -> None:
    p = tmp_path / "a.csv"
    s = tmp_path / "b.csv"
    pd.DataFrame([_row("1", "run_a", "c1"), _row("2", "run_a", "c1")]).to_csv(p, index=False)
    pd.DataFrame([_row("1", "run_b", "c1"), _row("3", "run_b", "c2")]).to_csv(s, index=False)
    out = tmp_path / "merged.csv"
    stats = merge_prediction_csvs(
        primary_path=p,
        primary_model_run_id="run_a",
        secondary_path=s,
        secondary_model_run_id="run_b",
        output_path=out,
        intersect_only=False,
    )
    assert stats["primary_rows_written"] == 2
    assert stats["secondary_rows_written"] == 2
    assert stats["output_rows"] == 4
    m = pd.read_csv(out)
    assert set(m["model_run_id"].astype(str)) == {"run_a", "run_b"}


def test_merge_prediction_csvs_intersect_only(tmp_path: Path) -> None:
    p = tmp_path / "a.csv"
    s = tmp_path / "b.csv"
    pd.DataFrame([_row("1", "run_a", "c1"), _row("2", "run_a", "c1")]).to_csv(p, index=False)
    pd.DataFrame([_row("1", "run_b", "c1"), _row("3", "run_b", "c2")]).to_csv(s, index=False)
    out = tmp_path / "merged.csv"
    stats = merge_prediction_csvs(
        primary_path=p,
        primary_model_run_id="run_a",
        secondary_path=s,
        secondary_model_run_id="run_b",
        output_path=out,
        intersect_only=True,
    )
    assert stats["primary_rows_written"] == 1
    assert stats["secondary_rows_written"] == 1
    m = pd.read_csv(out)
    assert set(m["record_id"].astype(str)) == {"1"}
