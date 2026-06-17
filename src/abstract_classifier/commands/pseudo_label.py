from __future__ import annotations

import argparse
from pathlib import Path

from ..pseudo_labeling import load_pseudo_label_settings, run_governed_pseudo_label_pipeline

ROOT = Path(__file__).resolve().parents[3]
DESCRIPTION = (
    "Select governed pseudo-label candidates from a prediction artifact using conservative admission rules."
)


def handle_command(args: argparse.Namespace) -> int:
    settings = load_pseudo_label_settings(args.config, root=ROOT)
    out = Path(args.output_dir)
    paths = run_governed_pseudo_label_pipeline(
        settings=settings,
        output_dir=out,
        prediction_artifact=Path(args.prediction_artifact).resolve()
        if args.prediction_artifact
        else None,
        root=ROOT,
    )
    print(f"Candidates: {paths['candidates']}")
    print(f"Admitted: {paths['admitted']}")
    print(f"Rejected: {paths['rejected']}")
    print(f"Policy: {paths['policy']}")
    print(f"Quota summary: {paths['quota']}")
    if "noncanonical_review" in paths:
        print(f"Noncanonical review: {paths['noncanonical_review']}")
    return 0


def register(subparsers) -> None:
    parser = subparsers.add_parser(
        "pseudo-label",
        help="Select governed pseudo-label candidates.",
        description=DESCRIPTION,
    )
    parser.add_argument(
        "--config",
        default="configs/theory_pseudo_label.toml",
        help="Path to theory_pseudo_label.toml.",
    )
    parser.add_argument(
        "--run-id",
        default="default",
        help="Logical run id (used only for logging in this wave).",
    )
    parser.add_argument(
        "--prediction-artifact",
        help="Override predictions CSV (defaults to config prediction_artifact).",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory for pseudo_label_*.csv and pseudo_label_policy.json.",
    )
    parser.set_defaults(handler=handle_command)
