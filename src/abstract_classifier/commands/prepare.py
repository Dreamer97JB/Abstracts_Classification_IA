from __future__ import annotations

import argparse
from pathlib import Path

from ..splits import write_split_assignments
from ..supervision import (
    build_candidate_supervision_outputs,
    write_candidate_rows,
    write_excluded_rows,
    write_gold_rows,
    write_theory_mapping_rows,
    write_theory_review_rows,
)
from ..taxonomy import (
    DEFAULT_SUPERVISION_CONFIG,
    DEFAULT_TAXONOMY_CONFIG,
    DEFAULT_TAXONOMY_INVENTORY,
    load_supervision_policy,
    load_taxonomy,
    write_taxonomy_inventory_report,
)

ROOT = Path(__file__).resolve().parents[3]
DESCRIPTION = (
    "Prepare canonical corpus tables and taxonomy inventory artifacts from "
    "the raw workbook sources."
)


def handle_command(args: argparse.Namespace) -> int:
    supervision_policy = load_supervision_policy(args.supervision_config, root=ROOT)
    taxonomy = load_taxonomy(args.taxonomy_config, root=ROOT)
    output_path = write_taxonomy_inventory_report(
        output=args.inventory_output,
        taxonomy_path=args.taxonomy_config,
        supervision_path=args.supervision_config,
        root=ROOT,
    )
    print(f"Taxonomy inventory generated at: {output_path}")

    if args.theory_output:
        theory_path = write_theory_mapping_rows(
            args.theory_output,
            root=ROOT,
            policy=supervision_policy,
            taxonomy=taxonomy,
        )
        print(f"Theory mappings generated at: {theory_path}")

    if args.theory_review_output:
        theory_review_path = write_theory_review_rows(
            args.theory_review_output,
            root=ROOT,
            policy=supervision_policy,
            taxonomy=taxonomy,
        )
        print(f"Theory review rows generated at: {theory_review_path}")

    candidate_outputs = None
    if args.candidate_output:
        candidate_path = write_candidate_rows(
            args.candidate_output,
            root=ROOT,
            policy=supervision_policy,
            taxonomy=taxonomy,
        )
        print(f"Candidate supervision rows generated at: {candidate_path}")
    if args.gold_output or args.excluded_output or args.split_output:
        candidate_outputs = build_candidate_supervision_outputs(
            root=ROOT,
            policy=supervision_policy,
            taxonomy=taxonomy,
        )

    if args.gold_output:
        gold_path = write_gold_rows(
            args.gold_output,
            root=ROOT,
            policy=supervision_policy,
            taxonomy=taxonomy,
        )
        print(f"Gold supervision rows generated at: {gold_path}")

    if args.excluded_output:
        excluded_path = write_excluded_rows(
            args.excluded_output,
            root=ROOT,
            policy=supervision_policy,
            taxonomy=taxonomy,
        )
        print(f"Excluded supervision rows generated at: {excluded_path}")

    if args.split_output:
        if candidate_outputs is None:
            candidate_outputs = build_candidate_supervision_outputs(
                root=ROOT,
                policy=supervision_policy,
                taxonomy=taxonomy,
            )
        split_path = write_split_assignments(
            candidate_outputs.candidate_rows,
            args.split_output,
            root=ROOT,
            policy=supervision_policy,
        )
        print(f"Split assignments generated at: {split_path}")

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
        "--supervision-config",
        default=str(DEFAULT_SUPERVISION_CONFIG),
        help="Path to the supervision policy TOML contract.",
    )
    parser.add_argument(
        "--inventory-output",
        default=str(DEFAULT_TAXONOMY_INVENTORY),
        help="Output path for the taxonomy inventory Markdown report.",
    )
    parser.add_argument(
        "--theory-output",
        help="Optional output path for the canonical supervised theory CSV.",
    )
    parser.add_argument(
        "--theory-review-output",
        help="Optional output path for unresolved theory review CSV rows.",
    )
    parser.add_argument(
        "--candidate-output",
        help="Optional output path for the candidate supervision CSV.",
    )
    parser.add_argument(
        "--gold-output",
        help="Optional output path for the gold supervision CSV.",
    )
    parser.add_argument(
        "--excluded-output",
        help="Optional output path for excluded supervision rows.",
    )
    parser.add_argument(
        "--split-output",
        help="Optional output path for split assignment CSV rows.",
    )
    parser.set_defaults(handler=handle_command)
