from __future__ import annotations

import argparse
from typing import Sequence

from .commands import COMMAND_MODULES


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="abstract-classifier",
        description="Operational CLI for the abstract classification pipeline.",
    )
    subparsers = parser.add_subparsers(
        dest="command",
        metavar="command",
        required=True,
    )

    for module in COMMAND_MODULES:
        module.register(subparsers)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.error("No handler configured for the selected command.")
    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
