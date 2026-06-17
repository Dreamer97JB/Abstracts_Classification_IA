from __future__ import annotations

import argparse
from pathlib import Path

from ..evaluation import compare_model_families, compare_text_variants, evaluate_run
from ..text_variants import SUPPORTED_TEXT_VARIANTS
from ..training import SUPPORTED_MODEL_FAMILIES, load_theory_baseline_config

ROOT = Path(__file__).resolve().parents[3]
DESCRIPTION = "Evaluate a trained theory run or compare the governed text variants."


def handle_command(args: argparse.Namespace) -> int:
    config = load_theory_baseline_config(args.config, root=ROOT)

    if args.compare_variants:
        comparison_path = compare_text_variants(
            config=config,
            variants=tuple(args.compare_variants),
            output_dir=args.output_dir,
            split_name=args.split,
            root=ROOT,
        )
        print(f"Variant comparison: {comparison_path}")
        return 0

    if args.compare_model_families:
        artifacts = compare_model_families(
            config=config,
            model_families=tuple(args.compare_model_families),
            output_dir=args.output_dir,
            split_name=args.split,
            root=ROOT,
        )
        print(f"Experiment comparison: {artifacts['comparison']}")
        print(f"Per-class comparison: {artifacts['per_class']}")
        print(f"Champion summary: {artifacts['champion']}")
        return 0

    if not args.run_id:
        raise SystemExit(
            "`evaluate` requires --run-id unless --compare-variants or "
            "--compare-model-families is used."
        )

    artifacts = evaluate_run(
        config=config,
        run_id=args.run_id,
        output_dir=args.output_dir,
        split_name=args.split,
        root=ROOT,
    )
    print(f"Run directory: {artifacts['run_dir']}")
    print(f"Overall metrics: {artifacts['metrics_overall']}")
    print(f"Per-class metrics: {artifacts['metrics_per_class']}")
    print(f"Confusion matrix: {artifacts['confusion_matrix']}")
    print(f"Predictions: {artifacts['predictions']}")
    return 0


def register(subparsers) -> None:
    parser = subparsers.add_parser(
        "evaluate",
        help="Evaluate trained models.",
        description=DESCRIPTION,
    )
    parser.add_argument(
        "--config",
        default="configs/theory_baseline.toml",
        help="Path to the Phase 3 baseline config TOML.",
    )
    parser.add_argument(
        "--run-id",
        help="Identifier of an existing persisted training run.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Existing run directory for standard evaluation, or target directory for variant comparison.",
    )
    parser.add_argument(
        "--split",
        default="test",
        choices=("train", "val", "test", "all"),
        help="Which governed split to score.",
    )
    parser.add_argument(
        "--compare-variants",
        nargs="+",
        choices=SUPPORTED_TEXT_VARIANTS,
        help="Train and evaluate the requested text variants on the frozen split, then persist a comparison CSV.",
    )
    parser.add_argument(
        "--compare-model-families",
        nargs="+",
        choices=SUPPORTED_MODEL_FAMILIES,
        help="Train and evaluate the requested model families, then persist a Phase 7 comparison bundle.",
    )
    parser.set_defaults(handler=handle_command)
