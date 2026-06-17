from __future__ import annotations

from pathlib import Path

import pytest

from abstract_classifier.methodology import (
    build_missing_methodology_assignment,
    load_methodology_contract,
    validate_methodology_assignment,
)


def test_methodology_contract_loads_expected_hierarchy(project_root: Path) -> None:
    contract = load_methodology_contract(project_root / "configs" / "methodology.toml")

    assert contract.version == "1"
    assert {branch.label for branch in contract.branches} == {
        "NN",
        "no_empirico",
        "empirico",
    }
    empirico = contract.branch_by_label("empirico")
    assert set(empirico.allowed_subtypes) == {"cualitativo", "cuantitativo"}


def test_methodology_validation_rejects_subtype_without_empirico() -> None:
    with pytest.raises(ValueError):
        validate_methodology_assignment(
            methodology_label="no_empirico",
            methodology_branch="no_empirico",
            methodology_subtype="cualitativo",
        )


def test_missing_methodology_assignment_stays_in_review_state() -> None:
    assignment = build_missing_methodology_assignment()

    assert assignment.methodology_label is None
    assert assignment.methodology_branch is None
    assert assignment.methodology_subtype is None
    assert assignment.methodology_review_required is True
    assert assignment.methodology_review_reason == "missing_source_columns"
