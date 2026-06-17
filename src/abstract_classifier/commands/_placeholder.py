from __future__ import annotations

import argparse
from collections.abc import Callable

CommandHandler = Callable[[argparse.Namespace], int]


def build_placeholder_handler(command_name: str, description: str) -> CommandHandler:
    message = f"Command `{command_name}` is not implemented yet. {description}"

    def handler(_: argparse.Namespace) -> int:
        print(message)
        return 0

    return handler
