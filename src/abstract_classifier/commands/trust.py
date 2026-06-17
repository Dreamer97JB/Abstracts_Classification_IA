from __future__ import annotations

import argparse
from pathlib import Path

from ..corpus_trust import load_corpus_trust_config, run_corpus_trust

ROOT = Path(__file__).resolve().parents[3]
DESCRIPTION = (
    "Build Phase 6 corpus-trust artifacts, trusted views, and Phase 5 comparison summaries."
)


def handle_command(args: argparse.Namespace) -> int:
    config = load_corpus_trust_config(args.config, root=ROOT)
    artifacts = run_corpus_trust(
        config=config,
        run_id=args.run_id,
        output_dir=args.output_dir,
        root=ROOT,
    )
    print(f"Run directory: {artifacts.run_dir}")
    print(f"Manifest: {artifacts.manifest_path}")
    print(f"Trust profile: {artifacts.trust_profile_path}")
    print(f"Excluded rows: {artifacts.excluded_rows_path}")
    print(f"Trusted experiment corpus: {artifacts.trusted_experiment_path}")
    print(f"Trusted production corpus: {artifacts.trusted_production_path}")
    print(f"Comparison summary: {artifacts.comparison_summary_path}")
    return 0


def register(subparsers) -> None:
    parser = subparsers.add_parser(
        "trust",
        help="Run Phase 6 corpus trust hardening.",
        description=DESCRIPTION,
    )
    parser.add_argument(
        "--run-id",
        required=True,
        help="Stable identifier for the persisted trust run.",
    )
    parser.add_argument(
        "--config",
        default="configs/corpus_trust.toml",
        help="Path to the Phase 6 corpus trust config TOML.",
    )
    parser.add_argument(
        "--output-dir",
        help="Optional run directory. Defaults to the trust config output root plus run-id.",
    )
    parser.set_defaults(handler=handle_command)
