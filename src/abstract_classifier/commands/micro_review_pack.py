from __future__ import annotations

import argparse
from pathlib import Path

from ..client_micro_review import export_client_micro_review_pack

ROOT = Path(__file__).resolve().parents[3]
DESCRIPTION = (
    "Export a small client-facing CSV for manual theory label review (9J micro-review), "
    "plus Spanish instructions and a manifest."
)


def handle_command(args: argparse.Namespace) -> int:
    gold_path: Path | None = None
    if not args.no_gold_exclude and args.gold:
        gold_path = Path(args.gold).resolve()
    paths = export_client_micro_review_pack(
        predictions_path=Path(args.predictions).resolve(),
        output_dir=Path(args.output_dir).resolve(),
        max_rows=int(args.max_rows),
        model_run_id=str(args.model_run_id) if args.model_run_id else None,
        trusted_corpus_path=Path(args.trusted).resolve() if args.trusted else None,
        gold_supervision_path=gold_path,
        abstract_max_chars=int(args.abstract_max_chars),
        taxonomy_config_path=Path(args.taxonomy).resolve() if args.taxonomy else None,
    )
    print(f"Client CSV: {paths['csv']}")
    print(f"Instructions: {paths['instructions']}")
    print(f"Manifest: {paths['manifest']}")
    if "weak_signal_summary" in paths:
        print(f"Weak signal summary: {paths['weak_signal_summary']}")
    if "weak_signal_votes" in paths:
        print(f"Weak signal votes: {paths['weak_signal_votes']}")
    return 0


def register(subparsers) -> None:
    parser = subparsers.add_parser(
        "micro-review-pack",
        help="Export client micro-review CSV + instructions.",
        description=DESCRIPTION,
    )
    parser.add_argument(
        "--predictions",
        required=True,
        help="Path to predictions.csv from an inference run.",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory to write client_micro_review.csv and INSTRUCCIONES_REVISION_CLIENTE.md.",
    )
    parser.add_argument(
        "--max-rows",
        type=int,
        default=50,
        help="Maximum rows in the client pack (default 50).",
    )
    parser.add_argument(
        "--model-run-id",
        help="If set, keep only rows with this model_run_id.",
    )
    parser.add_argument(
        "--trusted",
        help="Optional trusted_corpus.csv path; only record_id present here are kept.",
    )
    parser.add_argument(
        "--gold",
        default=str(ROOT / "reports" / "phase2_gold_supervision.csv"),
        help="Gold supervision CSV; those record_id are excluded (default reports/phase2_gold_supervision.csv).",
    )
    parser.add_argument(
        "--no-gold-exclude",
        action="store_true",
        help="Do not exclude rows already in gold supervision.",
    )
    parser.add_argument(
        "--abstract-max-chars",
        type=int,
        default=8000,
        help="Truncate abstract text for spreadsheet safety (default 8000).",
    )
    parser.add_argument(
        "--taxonomy",
        help="Override taxonomy TOML (default configs/taxonomy.toml under repo root).",
    )
    parser.set_defaults(handler=handle_command)
