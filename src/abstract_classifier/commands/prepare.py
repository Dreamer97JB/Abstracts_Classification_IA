from __future__ import annotations

import argparse
from pathlib import Path

from ..taxonomy import (
    DEFAULT_TAXONOMY_CONFIG,
    DEFAULT_TAXONOMY_INVENTORY,
    write_taxonomy_inventory_report,
)

ROOT = Path(__file__).resolve().parents[3]
DESCRIPTION = (
    "Prepare canonical corpus tables and taxonomy inventory artifacts from "
    "the raw workbook sources."
)


def handle_command(args: argparse.Namespace) -> int:
    output_path = write_taxonomy_inventory_report(
        output=args.inventory_output,
        taxonomy_path=args.taxonomy_config,
        root=ROOT,
    )
    print(f"Taxonomy inventory generated at: {output_path}")
    return 0


def register(subparsers) -> None:
    parser = subparsers.add_parser(
        "prepare",
        help="Prepare canonical corpus tables.",
        description=DESCRIPTION,
    )
    parser.add_argument(
        "--taxonomy-config",
        default=str(DEFAULT_TAXONOMY_CONFIG),
        help="Path to the canonical taxonomy TOML contract.",
    )
    parser.add_argument(
        "--inventory-output",
        default=str(DEFAULT_TAXONOMY_INVENTORY),
        help="Output path for the taxonomy inventory Markdown report.",
    )
    parser.set_defaults(handler=handle_command)
