from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

import pandas as pd

from ..contracts import NormalizedSourceRow, SourceManifest, SourceRole, SourceSpec
from ..normalization import normalize_doi, normalize_title, normalize_year

FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "title": ("Title",),
    "authors": ("Authors", "Author full names", "Autores"),
    "doi": ("DOI",),
    "abstract": ("Abstract",),
    "journal": ("Journal", "Source title"),
    "author_keywords": ("Author Keywords",),
    "index_keywords": ("Index Keywords",),
    "references": ("References",),
    "label_original": ("Clasificación",),
    "year": ("Year",),
}


def load_source_manifest(path: Path) -> SourceManifest:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    manifest_data = data.get("manifest", {})
    raw_sources = data.get("sources", [])
    sources = tuple(_build_source_spec(item) for item in raw_sources)
    lineage_fields = tuple(manifest_data.get("lineage_fields", ()))

    return SourceManifest(
        version=int(manifest_data.get("version", 1)),
        lineage_fields=lineage_fields,
        sources=sources,
    )


def _build_source_spec(data: dict[str, object]) -> SourceSpec:
    return SourceSpec(
        source_dataset=str(data["source_dataset"]),
        path=str(data["path"]),
        sheet=_optional_str(data.get("sheet")),
        role=SourceRole(str(data["role"])),
        source_type=str(data["source_type"]),
        source_system=str(data["source_system"]),
        lineage_workbook=str(data["lineage_workbook"]),
        lineage_notes=str(data["lineage_notes"]),
    )


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def load_normalized_rows(
    manifest_path: Path,
    *,
    project_root: Path | None = None,
    row_limit: int | None = None,
) -> list[NormalizedSourceRow]:
    manifest = load_source_manifest(manifest_path)
    root = project_root or manifest_path.resolve().parents[1]
    rows: list[NormalizedSourceRow] = []

    for source in manifest.sources:
        rows.extend(
            _load_source_rows(
                source,
                project_root=root,
                row_limit=row_limit,
            )
        )

    return rows


def _load_source_rows(
    source: SourceSpec,
    *,
    project_root: Path,
    row_limit: int | None,
) -> list[NormalizedSourceRow]:
    source_path = source.resolve_path(project_root)
    frame = _read_source_frame(source, source_path, row_limit=row_limit)
    rows: list[NormalizedSourceRow] = []

    for row_index, (_, series) in enumerate(frame.iterrows(), start=2):
        row = series.to_dict()
        title = _pick_string(row, "title")
        doi = _pick_string(row, "doi")
        authors = _pick_string(row, "authors")
        abstract = _pick_string(row, "abstract")
        journal = _pick_string(row, "journal")
        author_keywords = _pick_string(row, "author_keywords")
        index_keywords = _pick_string(row, "index_keywords")
        references = _pick_string(row, "references")
        label_original = _pick_string(row, "label_original")
        year = normalize_year(row.get("Year"))
        title_normalized = normalize_title(title)
        doi_normalized = normalize_doi(doi)
        record_id = f"{source.source_dataset}:{source.sheet or 'default'}:{row_index}"

        rows.append(
            NormalizedSourceRow(
                record_id=record_id,
                row_number=row_index,
                source_dataset=source.source_dataset,
                source_sheet=source.sheet,
                source_path=str(source_path.relative_to(project_root)),
                source_role=source.role.value,
                source_system=source.source_system,
                title=title,
                authors=authors,
                doi=doi,
                abstract=abstract,
                journal=journal,
                author_keywords=author_keywords,
                index_keywords=index_keywords,
                references=references,
                label_original=label_original,
                year=year,
                title_normalized=title_normalized,
                doi_normalized=doi_normalized,
            )
        )

    return rows


def _read_source_frame(
    source: SourceSpec,
    source_path: Path,
    *,
    row_limit: int | None,
) -> pd.DataFrame:
    if source.source_type != "workbook":
        raise ValueError(f"Unsupported source type: {source.source_type}")

    return pd.read_excel(
        source_path,
        sheet_name=source.sheet,
        nrows=row_limit,
    )


def _pick_string(row: dict[str, Any], field_name: str) -> str:
    for column in FIELD_ALIASES[field_name]:
        if column not in row:
            continue
        value = row[column]
        if pd.isna(value):
            continue
        text = str(value).strip()
        if text:
            return text
    return ""
