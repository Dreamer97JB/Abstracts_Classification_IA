from __future__ import annotations

from ._placeholder import build_placeholder_handler

DESCRIPTION = "Run batch inference over new abstracts with the trained models."
handle_command = build_placeholder_handler("predict", DESCRIPTION)


def register(subparsers) -> None:
    parser = subparsers.add_parser(
        "predict",
        help="Run batch inference.",
        description=DESCRIPTION,
    )
    parser.set_defaults(handler=handle_command)
