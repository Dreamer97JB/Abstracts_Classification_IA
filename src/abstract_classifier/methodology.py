from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

from .taxonomy import ROOT, resolve_project_path

DEFAULT_METHODOLOGY_CONFIG = Path("configs/methodology.toml")
METHODOLOGY_COLUMNS = [
    "methodology_label",
    "methodology_branch",
    "methodology_subtype",
    "methodology_review_required",
    "methodology_review_reason",
]


@dataclass(frozen=True)
class MethodologyBranch:
    label: str
    branch: str
    is_empirical: bool
    allowed_subtypes: tuple[str, ...]


@dataclass(frozen=True)
class MethodologyContract:
    version: str
    branches: tuple[MethodologyBranch, ...]
    review_reasons: dict[str, str]

    def branch_by_label(self, label: str) -> MethodologyBranch:
        for branch in self.branches:
            if branch.label == label:
                return branch
        raise KeyError(f"Unknown methodology label: {label}")

    def allowed_labels(self) -> set[str]:
        return {branch.label for branch in self.branches}


@dataclass(frozen=True)
class MethodologyAssignment:
    methodology_label: str | None
    methodology_branch: str | None
    methodology_subtype: str | None
    methodology_review_required: bool
    methodology_review_reason: str

    def as_record(self) -> dict[str, object]:
        return {
            "methodology_label": self.methodology_label or "",
            "methodology_branch": self.methodology_branch or "",
            "methodology_subtype": self.methodology_subtype or "",
            "methodology_review_required": self.methodology_review_required,
            "methodology_review_reason": self.methodology_review_reason,
        }


def load_methodology_contract(
    path: str | Path = DEFAULT_METHODOLOGY_CONFIG,
    *,
    root: Path | None = None,
) -> MethodologyContract:
    config_path = resolve_project_path(path, root=root)
    data = tomllib.loads(config_path.read_text(encoding="utf-8"))

    branches = tuple(
        MethodologyBranch(
            label=str(item["label"]),
            branch=str(item["branch"]),
            is_empirical=bool(item["is_empirical"]),
            allowed_subtypes=tuple(str(value) for value in item.get("allowed_subtypes", [])),
        )
        for item in data.get("branches", [])
    )
    if {branch.label for branch in branches} != {"NN", "no_empirico", "empirico"}:
        raise ValueError("Methodology contract must define NN, no_empirico, and empirico.")

    empirico = next(branch for branch in branches if branch.label == "empirico")
    if set(empirico.allowed_subtypes) != {"cualitativo", "cuantitativo"}:
        raise ValueError(
            "Empirical methodology branch must define cualitativo and cuantitativo."
        )

    review_reasons = {
        str(key): str(value)
        for key, value in data.get("review_reasons", {}).items()
    }
    if "missing_source_columns" not in review_reasons:
        raise ValueError(
            "Methodology contract must include a missing_source_columns review reason."
        )

    return MethodologyContract(
        version=str(data.get("version", "")),
        branches=branches,
        review_reasons=review_reasons,
    )


def validate_methodology_assignment(
    *,
    methodology_label: str | None,
    methodology_branch: str | None = None,
    methodology_subtype: str | None = None,
    methodology_review_required: bool = False,
    methodology_review_reason: str = "",
    contract: MethodologyContract | None = None,
) -> MethodologyAssignment:
    methodology_contract = contract or load_methodology_contract(root=ROOT)

    label = _clean_text(methodology_label)
    branch = _clean_text(methodology_branch) or label
    subtype = _clean_text(methodology_subtype)
    review_reason = _clean_text(methodology_review_reason) or ""

    if label is None and branch is None and subtype is None:
        return MethodologyAssignment(
            methodology_label=None,
            methodology_branch=None,
            methodology_subtype=None,
            methodology_review_required=methodology_review_required,
            methodology_review_reason=review_reason,
        )

    if label is None or branch is None:
        raise ValueError("Methodology label and branch must be provided together.")
    if label != branch:
        raise ValueError("Methodology label and branch must match in this contract.")
    if label not in methodology_contract.allowed_labels():
        raise ValueError(f"Unsupported methodology label: {label}")

    branch_spec = methodology_contract.branch_by_label(label)
    if subtype and not branch_spec.is_empirical:
        raise ValueError("Methodology subtype is only valid when the label is empirico.")
    if subtype and subtype not in branch_spec.allowed_subtypes:
        raise ValueError(f"Unsupported methodology subtype `{subtype}` for `{label}`.")

    if review_reason and review_reason not in methodology_contract.review_reasons.values():
        raise ValueError(f"Unsupported methodology review reason: {review_reason}")

    return MethodologyAssignment(
        methodology_label=label,
        methodology_branch=branch,
        methodology_subtype=subtype,
        methodology_review_required=methodology_review_required,
        methodology_review_reason=review_reason,
    )


def build_missing_methodology_assignment(
    contract: MethodologyContract | None = None,
) -> MethodologyAssignment:
    methodology_contract = contract or load_methodology_contract(root=ROOT)
    return MethodologyAssignment(
        methodology_label=None,
        methodology_branch=None,
        methodology_subtype=None,
        methodology_review_required=True,
        methodology_review_reason=methodology_contract.review_reasons[
            "missing_source_columns"
        ],
    )


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
