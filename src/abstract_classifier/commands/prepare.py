from __future__ import annotations

from ._placeholder import build_placeholder_handler

DESCRIPTION = "Prepare canonical corpus tables from the raw workbook sources."
handle_command = build_placeholder_handler("prepare", DESCRIPTION)


def register(subparsers) -> None:
    parser = subparsers.add_parser(
        "prepare",
        help="Prepare canonical corpus tables.",
        description=DESCRIPTION,
    )
    parser.set_defaults(handler=handle_command)
