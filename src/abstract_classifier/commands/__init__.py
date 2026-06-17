"""Command registrars for the abstract classifier CLI."""

from __future__ import annotations

from . import (
    analyze,
    audit,
    bibliometrics,
    calibrate,
    evaluate,
    micro_review_pack,
    predict,
    prepare,
    pseudo_label,
    train,
    trust,
)

COMMAND_MODULES = (
    audit,
    prepare,
    train,
    evaluate,
    calibrate,
    predict,
    analyze,
    bibliometrics,
    trust,
    pseudo_label,
    micro_review_pack,
)

__all__ = ["COMMAND_MODULES"]
