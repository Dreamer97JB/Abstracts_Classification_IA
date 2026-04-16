from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .methodology import (
    METHODOLOGY_COLUMNS,
    MethodologyContract,
    build_missing_methodology_assignment,
    load_methodology_contract,
)
from .normalization import normalize_doi, normalize_title, normalize_year
from .taxonomy import (
    ROOT,
    SupervisionPolicy,
    SupervisedSource,
    TaxonomyContract,
    load_supervision_policy,
    load_taxonomy,
    normalize_label,
    resolve_frame_column,
    resolve_project_path,
    stringify_label,
)

_WORD_RE = re.compile(r"\w+")

THEORY_OUTPUT_COLUMNS = [
    "record_id",
    "source_dataset",
    "source_sheet",
    "title",
    "abstract",
    "year",
    "doi",
    "label_original",
    "label_canonica",
    "canonical_id",
    "mapping_status",
    "mapping_notes",
    "review_required",
]
BASE_CANDIDATE_OUTPUT_COLUMNS = THEORY_OUTPUT_COLUMNS + [
    "include_in_gold",
    "title_normalized",
    "doi_normalized",
    "abstract_hash",
]
CANDIDATE_OUTPUT_COLUMNS = BASE_CANDIDATE_OUTPUT_COLUMNS + METHODOLOGY_COLUMNS
METHODOLOGY_OUTPUT_COLUMNS = [
    "record_id",
    "source_dataset",
    "source_sheet",
    "title",
    "abstract",
    "year",
    "doi",
] + METHODOLOGY_COLUMNS
EXCLUDED_OUTPUT_COLUMNS = CANDIDATE_OUTPUT_COLUMNS + ["gold_exclusion_reason"]
_INTERNAL_COLUMNS = EXCLUDED_OUTPUT_COLUMNS + ["same_article_group"]


@dataclass(frozen=True)
class TheoryMappingOutputs:
    canonical_rows: pd.DataFrame
    review_rows: pd.DataFrame


@dataclass(frozen=True)
class CandidateSupervisionOutputs:
    candidate_rows: pd.DataFrame
    gold_rows: pd.DataFrame
    excluded_rows: pd.DataFrame


def build_theory_mapping_outputs(
    *,
    root: Path | None = None,
    policy: SupervisionPolicy | None = None,
    taxonomy: TaxonomyContract | None = None,
) -> TheoryMappingOutputs:
    theory_rows = _build_internal_supervision_rows(
        root=root,
        policy=policy,
        taxonomy=taxonomy,
        methodology_contract=None,
    )
    canonical_rows = theory_rows.loc[:, THEORY_OUTPUT_COLUMNS].copy()
    review_rows = canonical_rows.loc[canonical_rows["review_required"]].reset_index(
        drop=True
    )
    return TheoryMappingOutputs(
        canonical_rows=canonical_rows,
        review_rows=review_rows,
    )


def build_candidate_supervision_outputs(
    *,
    root: Path | None = None,
    policy: SupervisionPolicy | None = None,
    taxonomy: TaxonomyContract | None = None,
    methodology_contract: MethodologyContract | None = None,
) -> CandidateSupervisionOutputs:
    candidate_rows = _build_internal_supervision_rows(
        root=root,
        policy=policy,
        taxonomy=taxonomy,
        methodology_contract=methodology_contract,
    )
    candidate_output = candidate_rows.loc[:, CANDIDATE_OUTPUT_COLUMNS].copy()
    gold_rows = candidate_output.loc[candidate_output["include_in_gold"]].reset_index(
        drop=True
    )
    excluded_rows = candidate_rows.loc[
        ~candidate_rows["include_in_gold"],
        EXCLUDED_OUTPUT_COLUMNS,
    ].reset_index(drop=True)
    return CandidateSupervisionOutputs(
        candidate_rows=candidate_output,
        gold_rows=gold_rows,
        excluded_rows=excluded_rows,
    )


def build_methodology_outputs(
    *,
    root: Path | None = None,
    policy: SupervisionPolicy | None = None,
    taxonomy: TaxonomyContract | None = None,
    methodology_contract: MethodologyContract | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    candidate_outputs = build_candidate_supervision_outputs(
        root=root,
        policy=policy,
        taxonomy=taxonomy,
        methodology_contract=methodology_contract,
    )
    methodology_rows = candidate_outputs.candidate_rows.loc[
        :,
        METHODOLOGY_OUTPUT_COLUMNS,
    ].copy()
    methodology_review_rows = methodology_rows.loc[
        methodology_rows["methodology_review_required"]
    ].reset_index(drop=True)
    return methodology_rows, methodology_review_rows


def _build_internal_supervision_rows(
    *,
    root: Path | None,
    policy: SupervisionPolicy | None,
    taxonomy: TaxonomyContract | None,
    methodology_contract: MethodologyContract | None,
) -> pd.DataFrame:
    project_root = root or ROOT
    supervision_policy = policy or load_supervision_policy(root=project_root)
    contract = taxonomy or load_taxonomy(
        supervision_policy.taxonomy_config,
        root=project_root,
    )
    methodology = methodology_contract or load_methodology_contract(root=project_root)
    base_rows = _assemble_source_rows(
        supervision_policy.sources,
        root=project_root,
        policy=supervision_policy,
        taxonomy=contract,
        methodology_contract=methodology,
    )
    return _apply_gold_inclusion_rules(base_rows, policy=supervision_policy)


def _assemble_source_rows(
    sources: tuple[SupervisedSource, ...],
    *,
    root: Path,
    policy: SupervisionPolicy,
    taxonomy: TaxonomyContract,
    methodology_contract: MethodologyContract,
) -> pd.DataFrame:
    records: list[dict[str, object]] = []
    missing_methodology = build_missing_methodology_assignment(methodology_contract)

    for source in sources:
        workbook_path = resolve_project_path(source.workbook_path, root=root)
        frame = pd.read_excel(workbook_path, sheet_name=source.sheet_name)
        columns = list(frame.columns)

        label_column = resolve_frame_column(columns, source.label_column)
        title_column = resolve_frame_column(columns, source.title_column)
        abstract_column = _optional_frame_column(columns, source.abstract_column)
        year_column = _optional_frame_column(columns, source.year_column)
        doi_column = _optional_frame_column(columns, source.doi_column)

        for row_number, row in enumerate(frame.to_dict(orient="records"), start=2):
            record_id = f"{source.source_dataset}:{source.sheet_name}:{row_number}"
            title = stringify_label(row.get(title_column)).strip()
            abstract = (
                stringify_label(row.get(abstract_column)).strip()
                if abstract_column is not None
                else ""
            )
            doi = (
                stringify_label(row.get(doi_column)).strip()
                if doi_column is not None
                else ""
            )
            year = normalize_year(row.get(year_column)) if year_column is not None else None
            normalization = normalize_label(
                row.get(label_column),
                taxonomy=taxonomy,
                policy=policy,
            )
            title_normalized = normalize_title(title)
            doi_normalized = normalize_doi(doi)
            same_article_group = _same_article_group_key(
                record_id=record_id,
                doi_normalized=doi_normalized,
                title_normalized=title_normalized,
                year=year,
            )

            records.append(
                {
                    "record_id": record_id,
                    "source_dataset": source.source_dataset,
                    "source_sheet": source.sheet_name,
                    "title": title,
                    "abstract": abstract,
                    "year": year,
                    "doi": doi,
                    "label_original": normalization.label_original,
                    "label_canonica": normalization.label_canonica,
                    "canonical_id": normalization.canonical_id,
                    "mapping_status": normalization.mapping_status,
                    "mapping_notes": normalization.mapping_notes,
                    "review_required": normalization.review_required,
                    "include_in_gold": False,
                    "title_normalized": title_normalized,
                    "doi_normalized": doi_normalized,
                    "abstract_hash": _abstract_hash(abstract),
                    "methodology_label": missing_methodology.methodology_label or "",
                    "methodology_branch": missing_methodology.methodology_branch or "",
                    "methodology_subtype": missing_methodology.methodology_subtype or "",
                    "methodology_review_required": missing_methodology.methodology_review_required,
                    "methodology_review_reason": missing_methodology.methodology_review_reason,
                    "gold_exclusion_reason": "",
                    "same_article_group": same_article_group,
                }
            )

    return pd.DataFrame.from_records(records, columns=_INTERNAL_COLUMNS)


def _apply_gold_inclusion_rules(
    rows: pd.DataFrame,
    *,
    policy: SupervisionPolicy,
) -> pd.DataFrame:
    candidate_rows = rows.copy()
    candidate_rows["include_in_gold"] = True
    candidate_rows["gold_exclusion_reason"] = ""

    missing_title = candidate_rows["title"].map(lambda value: not value.strip())
    too_thin_abstract = candidate_rows["abstract"].map(
        lambda value: _abstract_word_count(value) < policy.quality.min_abstract_words
    )
    review_required = candidate_rows["review_required"]
    unresolved_status = candidate_rows["mapping_status"].isin(
        {"revision_manual", "sin_etiqueta"}
    )

    candidate_rows.loc[missing_title, "include_in_gold"] = False
    candidate_rows.loc[missing_title, "gold_exclusion_reason"] = "missing_title"

    candidate_rows.loc[too_thin_abstract, "include_in_gold"] = False
    candidate_rows.loc[
        too_thin_abstract & ~missing_title,
        "gold_exclusion_reason",
    ] = "abstract_too_thin"

    candidate_rows.loc[review_required | unresolved_status, "include_in_gold"] = False
    candidate_rows.loc[
        unresolved_status,
        "gold_exclusion_reason",
    ] = candidate_rows.loc[unresolved_status, "mapping_status"]

    conflict_groups = _find_duplicate_conflict_groups(candidate_rows)
    if conflict_groups:
        conflict_mask = candidate_rows["same_article_group"].isin(conflict_groups)
        candidate_rows.loc[conflict_mask, "include_in_gold"] = False
        candidate_rows.loc[
            conflict_mask,
            "gold_exclusion_reason",
        ] = "duplicate_conflict"

    return candidate_rows


def _find_duplicate_conflict_groups(rows: pd.DataFrame) -> set[str]:
    eligible = rows.loc[
        rows["include_in_gold"]
        & rows["same_article_group"].str.startswith(("doi:", "title_year:"))
    ]
    if eligible.empty:
        return set()

    conflict_groups: set[str] = set()
    for group_key, group in eligible.groupby("same_article_group", dropna=False):
        canonical_ids = {
            value
            for value in group["canonical_id"].tolist()
            if isinstance(value, str) and value
        }
        if len(canonical_ids) > 1:
            conflict_groups.add(str(group_key))
    return conflict_groups


def _same_article_group_key(
    *,
    record_id: str,
    doi_normalized: str,
    title_normalized: str,
    year: int | None,
) -> str:
    if doi_normalized:
        return f"doi:{doi_normalized}"
    if title_normalized and year is not None:
        return f"title_year:{title_normalized}:{year}"
    return f"record:{record_id}"


def _abstract_word_count(value: str) -> int:
    return len(_WORD_RE.findall(value))


def _abstract_hash(value: str) -> str:
    text = value.strip()
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _optional_frame_column(columns: list[object], requested_column: str) -> str | None:
    try:
        return resolve_frame_column(columns, requested_column)
    except KeyError:
        return None


def write_theory_mapping_rows(
    output: str | Path,
    *,
    root: Path | None = None,
    policy: SupervisionPolicy | None = None,
    taxonomy: TaxonomyContract | None = None,
) -> Path:
    outputs = build_theory_mapping_outputs(
        root=root,
        policy=policy,
        taxonomy=taxonomy,
    )
    return _write_frame(outputs.canonical_rows, output, root=root)


def write_theory_review_rows(
    output: str | Path,
    *,
    root: Path | None = None,
    policy: SupervisionPolicy | None = None,
    taxonomy: TaxonomyContract | None = None,
) -> Path:
    outputs = build_theory_mapping_outputs(
        root=root,
        policy=policy,
        taxonomy=taxonomy,
    )
    return _write_frame(outputs.review_rows, output, root=root)


def write_candidate_rows(
    output: str | Path,
    *,
    root: Path | None = None,
    policy: SupervisionPolicy | None = None,
    taxonomy: TaxonomyContract | None = None,
    methodology_contract: MethodologyContract | None = None,
) -> Path:
    outputs = build_candidate_supervision_outputs(
        root=root,
        policy=policy,
        taxonomy=taxonomy,
        methodology_contract=methodology_contract,
    )
    return _write_frame(outputs.candidate_rows, output, root=root)


def write_gold_rows(
    output: str | Path,
    *,
    root: Path | None = None,
    policy: SupervisionPolicy | None = None,
    taxonomy: TaxonomyContract | None = None,
    methodology_contract: MethodologyContract | None = None,
) -> Path:
    outputs = build_candidate_supervision_outputs(
        root=root,
        policy=policy,
        taxonomy=taxonomy,
        methodology_contract=methodology_contract,
    )
    return _write_frame(outputs.gold_rows, output, root=root)


def write_excluded_rows(
    output: str | Path,
    *,
    root: Path | None = None,
    policy: SupervisionPolicy | None = None,
    taxonomy: TaxonomyContract | None = None,
    methodology_contract: MethodologyContract | None = None,
) -> Path:
    outputs = build_candidate_supervision_outputs(
        root=root,
        policy=policy,
        taxonomy=taxonomy,
        methodology_contract=methodology_contract,
    )
    return _write_frame(outputs.excluded_rows, output, root=root)


def write_methodology_rows(
    output: str | Path,
    *,
    root: Path | None = None,
    policy: SupervisionPolicy | None = None,
    taxonomy: TaxonomyContract | None = None,
    methodology_contract: MethodologyContract | None = None,
) -> Path:
    methodology_rows, _ = build_methodology_outputs(
        root=root,
        policy=policy,
        taxonomy=taxonomy,
        methodology_contract=methodology_contract,
    )
    return _write_frame(methodology_rows, output, root=root)


def write_methodology_review_rows(
    output: str | Path,
    *,
    root: Path | None = None,
    policy: SupervisionPolicy | None = None,
    taxonomy: TaxonomyContract | None = None,
    methodology_contract: MethodologyContract | None = None,
) -> Path:
    _, methodology_review_rows = build_methodology_outputs(
        root=root,
        policy=policy,
        taxonomy=taxonomy,
        methodology_contract=methodology_contract,
    )
    return _write_frame(methodology_review_rows, output, root=root)


def _write_frame(frame: pd.DataFrame, output: str | Path, *, root: Path | None) -> Path:
    project_root = root or ROOT
    output_path = Path(output)
    if not output_path.is_absolute():
        output_path = project_root / output_path
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False, encoding="utf-8")
    return output_path
