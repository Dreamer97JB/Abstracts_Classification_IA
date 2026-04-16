from __future__ import annotations

from ._placeholder import build_placeholder_handler

DESCRIPTION = "Evaluate trained models against the canonical validation assets."
handle_command = build_placeholder_handler("evaluate", DESCRIPTION)


def register(subparsers) -> None:
    parser = subparsers.add_parser(
        "evaluate",
        help="Evaluate trained models.",
        description=DESCRIPTION,
    )
    parser.set_defaults(handler=handle_command)
