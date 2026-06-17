from __future__ import annotations

import argparse
from pathlib import Path

from ..evaluation import calibrate_run
from ..training import load_theory_baseline_config

ROOT = Path(__file__).resolve().parents[3]
DESCRIPTION = "Calibrate a trained theory model and persist the Phase 8 promotion gate bundle."


def handle_command(args: argparse.Namespace) -> int:
    config = load_theory_baseline_config(args.config, root=ROOT)
    artifacts = calibrate_run(
        config=config,
        run_id=args.run_id,
        model_run_dir=args.model_run_dir,
        output_dir=args.output_dir,
        root=ROOT,
    )
    print(f"Run directory: {artifacts.run_dir}")
    print(f"Manifest: {artifacts.manifest_path}")
    print(f"Reliability table: {artifacts.reliability_table_path}")
    print(f"Threshold sweep: {artifacts.threshold_sweep_path}")
    print(f"Promotion gate: {artifacts.promotion_gate_path}")
    print(f"Calibration summary: {artifacts.calibration_summary_path}")
    print(f"Imbalance comparison: {artifacts.imbalance_policy_comparison_path}")
    print(f"Score calibrator: {artifacts.score_calibrator_path}")
    return 0


def register(subparsers) -> None:
    parser = subparsers.add_parser(
        "calibrate",
        help="Calibrate a trained model and persist promotion artifacts.",
        description=DESCRIPTION,
    )
    parser.add_argument(
        "--config",
        default="configs/theory_experiments.toml",
        help="Path to the Phase 7/8 experiment config TOML.",
    )
    parser.add_argument(
        "--run-id",
        required=True,
        help="Stable identifier for the persisted calibration run.",
    )
    parser.add_argument(
        "--model-run-dir",
        required=True,
        help="Directory containing the trained model that should be calibrated.",
    )
    parser.add_argument(
        "--output-dir",
        help="Optional calibration run directory. Defaults to reports/tmp_phase8/<run-id>.",
    )
    parser.set_defaults(handler=handle_command)
