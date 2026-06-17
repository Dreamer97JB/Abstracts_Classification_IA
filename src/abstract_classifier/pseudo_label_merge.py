"""Merge two prediction CSV exports for Phase 9 cross-model agreement (9E)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

REQUIRED_COLUMNS = ("record_id", "model_run_id", "predicted_canonical_id")


def merge_prediction_csvs(
    *,
    primary_path: Path,
    primary_model_run_id: str,
    secondary_path: Path,
    secondary_model_run_id: str,
    output_path: Path,
    intersect_only: bool = False,
) -> dict[str, int]:
    """Keep one model_run_id slice from each file, align columns, write concatenated CSV."""
    primary = pd.read_csv(primary_path)
    secondary = pd.read_csv(secondary_path)
    for name, frame in (("primary", primary), ("secondary", secondary)):
        missing = [c for c in REQUIRED_COLUMNS if c not in frame.columns]
        if missing:
            raise ValueError(f"{name} predictions missing columns {missing}.")

    pid = str(primary_model_run_id).strip()
    sid = str(secondary_model_run_id).strip()
    p_rows = primary.loc[primary["model_run_id"].astype(str) == pid].copy()
    s_rows = secondary.loc[secondary["model_run_id"].astype(str) == sid].copy()
    if p_rows.empty:
        raise ValueError(f"No rows with model_run_id={pid!r} in {primary_path}.")
    if s_rows.empty:
        raise ValueError(f"No rows with model_run_id={sid!r} in {secondary_path}.")

    if intersect_only:
        p_ids = set(p_rows["record_id"].astype(str))
        s_ids = set(s_rows["record_id"].astype(str))
        inter = p_ids & s_ids
        p_rows = p_rows.loc[p_rows["record_id"].astype(str).isin(inter)].copy()
        s_rows = s_rows.loc[s_rows["record_id"].astype(str).isin(inter)].copy()

    all_cols = sorted(set(p_rows.columns) | set(s_rows.columns))
    p_rows = p_rows.reindex(columns=all_cols)
    s_rows = s_rows.reindex(columns=all_cols)
    merged = pd.concat([p_rows, s_rows], ignore_index=True)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(output_path, index=False)

    p_ids = set(primary.loc[primary["model_run_id"].astype(str) == pid, "record_id"].astype(str))
    s_ids = set(secondary.loc[secondary["model_run_id"].astype(str) == sid, "record_id"].astype(str))
    return {
        "primary_rows_written": int(len(p_rows)),
        "secondary_rows_written": int(len(s_rows)),
        "output_rows": int(len(merged)),
        "primary_record_ids": len(p_ids),
        "secondary_record_ids": len(s_ids),
        "record_id_intersection": len(p_ids & s_ids),
    }


def merge_prediction_csvs_cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Merge two prediction exports into one CSV for Phase 9 cross-model agreement (9E)."
    )
    parser.add_argument("--primary", type=Path, required=True)
    parser.add_argument("--primary-model-run-id", required=True)
    parser.add_argument("--secondary", type=Path, required=True)
    parser.add_argument("--secondary-model-run-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--intersect-only",
        action="store_true",
        help="Keep only record_id present in both runs.",
    )
    parser.add_argument("--manifest", type=Path, default=None)
    args = parser.parse_args(argv)

    stats = merge_prediction_csvs(
        primary_path=args.primary.resolve(),
        primary_model_run_id=args.primary_model_run_id,
        secondary_path=args.secondary.resolve(),
        secondary_model_run_id=args.secondary_model_run_id,
        output_path=args.output.resolve(),
        intersect_only=bool(args.intersect_only),
    )
    out: dict[str, Any] = {"output": str(args.output.resolve()), **stats}
    print(json.dumps(out, indent=2))
    if args.manifest:
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    return 0


def main() -> int:
    return merge_prediction_csvs_cli(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
