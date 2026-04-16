from __future__ import annotations

from ._placeholder import build_placeholder_handler

DESCRIPTION = "Train the classification models on the governed canonical datasets."
handle_command = build_placeholder_handler("train", DESCRIPTION)


def register(subparsers) -> None:
    parser = subparsers.add_parser(
        "train",
        help="Train classification models.",
        description=DESCRIPTION,
    )
    parser.set_defaults(handler=handle_command)
