from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class SourceRole(StrEnum):
    """Allowed semantic roles for governed source datasets."""

    CORPUS = "corpus"
    INITIAL_GOLD = "initial_gold"
    AUX_REVIEW = "aux_review"


@dataclass(frozen=True, slots=True)
class SourceSpec:
    """One governed source entry from the source manifest."""

    source_dataset: str
    path: str
    sheet: str | None
    role: SourceRole
    source_type: str
    source_system: str
    lineage_workbook: str
    lineage_notes: str

    def resolve_path(self, project_root: Path) -> Path:
        path = Path(self.path)
        if path.is_absolute():
            return path
        return (project_root / path).resolve()


@dataclass(frozen=True, slots=True)
class SourceManifest:
    """Versioned collection of governed source specifications."""

    version: int
    lineage_fields: tuple[str, ...]
    sources: tuple[SourceSpec, ...]


@dataclass(frozen=True, slots=True)
class NormalizedSourceRow:
    """Normalized row representation used across overlap and audit steps."""

    record_id: str
    row_number: int
    source_dataset: str
    source_sheet: str | None
    source_path: str
    source_role: str
    source_system: str
    title: str
    authors: str
    doi: str
    abstract: str
    journal: str
    author_keywords: str
    index_keywords: str
    references: str
    label_original: str
    year: int | None
    title_normalized: str
    doi_normalized: str

    def to_dict(self) -> dict[str, object]:
        return {
            "record_id": self.record_id,
            "row_number": self.row_number,
            "source_dataset": self.source_dataset,
            "source_sheet": self.source_sheet or "",
            "source_path": self.source_path,
            "source_role": self.source_role,
            "source_system": self.source_system,
            "title": self.title,
            "authors": self.authors,
            "doi": self.doi,
            "abstract": self.abstract,
            "journal": self.journal,
            "author_keywords": self.author_keywords,
            "index_keywords": self.index_keywords,
            "references": self.references,
            "label_original": self.label_original,
            "year": self.year,
            "title_normalized": self.title_normalized,
            "doi_normalized": self.doi_normalized,
        }
