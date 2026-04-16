"""Command registrars for the abstract classifier CLI."""

from __future__ import annotations

from . import analyze, audit, evaluate, predict, prepare, train

COMMAND_MODULES = (
    audit,
    prepare,
    train,
    evaluate,
    predict,
    analyze,
)

__all__ = ["COMMAND_MODULES"]
