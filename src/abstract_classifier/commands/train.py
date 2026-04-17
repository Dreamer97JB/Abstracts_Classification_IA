from __future__ import annotations

import argparse
from pathlib import Path

from ..training import load_theory_baseline_config, train_theory_baseline

ROOT = Path(__file__).resolve().parents[3]
DESCRIPTION = "Train the governed baseline theory classifier on the fixed Phase 2 split."


def handle_command(args: argparse.Namespace) -> int:
    config = load_theory_baseline_config(args.config, root=ROOT)
    artifacts = train_theory_baseline(
        config=config,
        run_id=args.run_id,
        output_dir=args.output_dir,
        text_variant=args.text_variant,
        root=ROOT,
    )
    print(f"Run directory: {artifacts.run_dir}")
    print(f"Manifest: {artifacts.manifest_path}")
    print(f"Model: {artifacts.model_path}")
    print(f"Keyword coverage: {artifacts.keyword_coverage_path}")
    return 0


def register(subparsers) -> None:
    parser = subparsers.add_parser(
        "train",
        help="Train classification models.",
        description=DESCRIPTION,
    )
    parser.add_argument(
        "--config",
        default="configs/theory_baseline.toml",
        help="Path to the Phase 3 baseline config TOML.",
    )
    parser.add_argument(
        "--run-id",
        required=True,
        help="Stable identifier for the persisted training run.",
    )
    parser.add_argument(
        "--output-dir",
        help="Optional run directory. Defaults to the config output root plus run-id.",
    )
    parser.add_argument(
        "--text-variant",
        choices=("abstract_only", "abstract_plus_keywords"),
        help="Override the configured text variant for this run.",
    )
    parser.set_defaults(handler=handle_command)
