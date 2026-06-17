from __future__ import annotations

import argparse
from pathlib import Path

from ..inference import load_theory_inference_config, run_batch_inference

ROOT = Path(__file__).resolve().parents[3]
DESCRIPTION = "Run governed batch inference over the selected client corpus."


def handle_command(args: argparse.Namespace) -> int:
    config = load_theory_inference_config(args.config, root=ROOT)
    artifacts = run_batch_inference(
        config=config,
        run_id=args.run_id,
        model_run_dir=args.model_run_dir,
        output_dir=args.output_dir,
        source_datasets=tuple(args.source_datasets) if args.source_datasets else None,
        row_limit=args.row_limit,
        root=ROOT,
    )
    print(f"Run directory: {artifacts.run_dir}")
    print(f"Manifest: {artifacts.manifest_path}")
    print(f"Predictions: {artifacts.predictions_path}")
    print(f"Low-confidence review: {artifacts.low_confidence_review_path}")
    print(f"Taxonomy-conflict review: {artifacts.taxonomy_conflict_review_path}")
    print(f"Review priority high: {artifacts.review_priority_high_path}")
    print(f"Review priority medium: {artifacts.review_priority_medium_path}")
    print(f"Review pack manifest: {artifacts.review_pack_manifest_path}")
    print(f"Production readiness summary: {artifacts.production_readiness_summary_path}")
    print(f"Overlap review: {artifacts.overlap_review_path}")
    return 0


def register(subparsers) -> None:
    parser = subparsers.add_parser(
        "predict",
        help="Run batch inference.",
        description=DESCRIPTION,
    )
    parser.add_argument(
        "--config",
        default="configs/theory_inference.toml",
        help="Path to the Phase 5 theory inference config TOML.",
    )
    parser.add_argument(
        "--run-id",
        required=True,
        help="Stable identifier for the persisted prediction run.",
    )
    parser.add_argument(
        "--model-run-dir",
        required=True,
        help="Directory containing a persisted Phase 3 trained model and run manifest.",
    )
    parser.add_argument(
        "--output-dir",
        help="Optional run directory. Defaults to the inference config output root plus run-id.",
    )
    parser.add_argument(
        "--source-datasets",
        nargs="+",
        help="Optional governed source_dataset values to score. Defaults to the inference config selection.",
    )
    parser.add_argument(
        "--row-limit",
        type=int,
        help="Optional per-source row limit for smoke runs and tests.",
    )
    parser.set_defaults(handler=handle_command)
