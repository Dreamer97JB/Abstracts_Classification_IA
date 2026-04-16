from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .normalization import normalize_doi, normalize_title, normalize_year
from .taxonomy import (
    ROOT,
    SupervisionPolicy,
    TaxonomyContract,
    SupervisedSource,
    load_supervision_policy,
    load_taxonomy,
    normalize_label,
    resolve_frame_column,
    resolve_project_path,
    stringify_label,
)

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
THEORY_INTERNAL_COLUMNS = THEORY_OUTPUT_COLUMNS + [
    "title_normalized",
    "doi_normalized",
]


@dataclass(frozen=True)
class TheoryMappingOutputs:
    canonical_rows: pd.DataFrame
    review_rows: pd.DataFrame


def build_theory_mapping_outputs(
    *,
    root: Path | None = None,
    policy: SupervisionPolicy | None = None,
    taxonomy: TaxonomyContract | None = None,
) -> TheoryMappingOutputs:
    project_root = root or ROOT
    supervision_policy = policy or load_supervision_policy(root=project_root)
    contract = taxonomy or load_taxonomy(
        supervision_policy.taxonomy_config,
        root=project_root,
    )
    theory_rows = _assemble_theory_rows(
        supervision_policy.sources,
        root=project_root,
        policy=supervision_policy,
        taxonomy=contract,
    )
    canonical_rows = theory_rows.loc[:, THEORY_OUTPUT_COLUMNS].copy()
    review_rows = canonical_rows.loc[canonical_rows["review_required"]].reset_index(
        drop=True
    )
    return TheoryMappingOutputs(
        canonical_rows=canonical_rows,
        review_rows=review_rows,
    )


def _assemble_theory_rows(
    sources: tuple[SupervisedSource, ...],
    *,
    root: Path,
    policy: SupervisionPolicy,
    taxonomy: TaxonomyContract,
) -> pd.DataFrame:
    records: list[dict[str, object]] = []
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

            record = {
                "record_id": f"{source.source_dataset}:{source.sheet_name}:{row_number}",
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
                "title_normalized": normalize_title(title),
                "doi_normalized": normalize_doi(doi),
            }
            records.append(record)

    return pd.DataFrame.from_records(records, columns=THEORY_INTERNAL_COLUMNS)


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


def _write_frame(frame: pd.DataFrame, output: str | Path, *, root: Path | None) -> Path:
    project_root = root or ROOT
    output_path = Path(output)
    if not output_path.is_absolute():
        output_path = project_root / output_path
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False, encoding="utf-8")
    return output_path
