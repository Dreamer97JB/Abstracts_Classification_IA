from __future__ import annotations

import argparse
from pathlib import Path

from ..analysis import run_analysis_bundle

ROOT = Path(__file__).resolve().parents[3]
DESCRIPTION = (
    "Run the governed Phase 4 methodology and theme analysis bundle over a classified artifact."
)


def handle_command(args: argparse.Namespace) -> int:
    artifacts = run_analysis_bundle(
        run_id=args.run_id,
        input_artifact=args.input_artifact,
        output_dir=args.output_dir,
        methodology_config_path=args.methodology_config,
        theme_config_path=args.theme_config,
        reviewed_methodology_artifact=args.reviewed_methodology_artifact,
        text_variant=args.text_variant,
        skip_methodology=args.skip_methodology,
        skip_themes=args.skip_themes,
        root=ROOT,
    )
    print(f"Run directory: {artifacts.run_dir}")
    print(f"Manifest: {artifacts.manifest_path}")
    if artifacts.methodology_artifacts:
        print(
            "Methodology assignments: "
            f"{artifacts.methodology_artifacts['assignments']}"
        )
        print(f"Methodology review queue: {artifacts.methodology_artifacts['review_queue']}")
    if artifacts.theme_artifacts:
        print(f"Theme assignments: {artifacts.theme_artifacts['assignments']}")
        print(f"Theme summary: {artifacts.theme_artifacts['summary']}")
    return 0


def register(subparsers) -> None:
    parser = subparsers.add_parser(
        "analyze",
        help="Run downstream analyses.",
        description=DESCRIPTION,
    )
    parser.add_argument(
        "--run-id",
        required=True,
        help="Stable identifier for the persisted analysis run.",
    )
    parser.add_argument(
        "--input-artifact",
        default="reports/phase2_gold_supervision.csv",
        help="CSV artifact to analyze. Must include at least record_id, title, and abstract.",
    )
    parser.add_argument(
        "--output-dir",
        help="Optional run directory. Defaults to the methodology config output root plus run-id.",
    )
    parser.add_argument(
        "--methodology-config",
        default="configs/methodology_baseline.toml",
        help="Path to the Phase 4 methodology baseline config TOML.",
    )
    parser.add_argument(
        "--theme-config",
        default="configs/theme_pipeline.toml",
        help="Path to the Phase 4 theme pipeline config TOML.",
    )
    parser.add_argument(
        "--reviewed-methodology-artifact",
        help="Optional reviewed methodology CSV keyed by record_id for evaluation.",
    )
    parser.add_argument(
        "--text-variant",
        choices=("abstract_only", "abstract_plus_keywords"),
        help="Override the methodology text variant for this analysis run.",
    )
    parser.add_argument(
        "--skip-methodology",
        action="store_true",
        help="Skip methodology inference and evaluation artifacts.",
    )
    parser.add_argument(
        "--skip-themes",
        action="store_true",
        help="Skip theme extraction artifacts.",
    )
    parser.set_defaults(handler=handle_command)
