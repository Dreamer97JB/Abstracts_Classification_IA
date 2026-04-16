from __future__ import annotations

from ._placeholder import build_placeholder_handler

DESCRIPTION = "Run downstream analytical summaries over classified outputs."
handle_command = build_placeholder_handler("analyze", DESCRIPTION)


def register(subparsers) -> None:
    parser = subparsers.add_parser(
        "analyze",
        help="Run downstream analyses.",
        description=DESCRIPTION,
    )
    parser.set_defaults(handler=handle_command)
