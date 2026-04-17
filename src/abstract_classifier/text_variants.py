from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .taxonomy import ROOT, load_supervision_policy, resolve_frame_column, stringify_label

TEXT_VARIANT_ABSTRACT_ONLY = "abstract_only"
TEXT_VARIANT_ABSTRACT_PLUS_KEYWORDS = "abstract_plus_keywords"
SUPPORTED_TEXT_VARIANTS = (
    TEXT_VARIANT_ABSTRACT_ONLY,
    TEXT_VARIANT_ABSTRACT_PLUS_KEYWORDS,
)

_AUTHOR_KEYWORDS_COLUMN = "Author Keywords"
_INDEX_KEYWORDS_COLUMN = "Index Keywords"


@dataclass(frozen=True)
class KeywordCoverageSummary:
    text_variant: str
    row_count: int
    keyword_rows_available: int
    keyword_rows_enriched: int
    keyword_availability_rate: float
    keyword_coverage_rate: float
    by_source_split: tuple[dict[str, object], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "text_variant": self.text_variant,
            "row_count": self.row_count,
            "keyword_rows_available": self.keyword_rows_available,
            "keyword_rows_enriched": self.keyword_rows_enriched,
            "keyword_availability_rate": self.keyword_availability_rate,
            "keyword_coverage_rate": self.keyword_coverage_rate,
            "by_source_split": list(self.by_source_split),
        }


def validate_text_variant(text_variant: str) -> str:
    normalized = text_variant.strip()
    if normalized not in SUPPORTED_TEXT_VARIANTS:
        raise ValueError(
            f"Unsupported text variant `{text_variant}`. "
            f"Expected one of: {', '.join(SUPPORTED_TEXT_VARIANTS)}."
        )
    return normalized


def load_governed_text_metadata(
    *,
    root: Path | None = None,
    supervision_config_path: str | Path = "configs/supervision.toml",
) -> pd.DataFrame:
    project_root = root or ROOT
    supervision_policy = load_supervision_policy(
        supervision_config_path,
        root=project_root,
    )
    records: list[dict[str, object]] = []

    for source in supervision_policy.sources:
        workbook_path = (project_root / source.workbook_path).resolve()
        frame = pd.read_excel(workbook_path, sheet_name=source.sheet_name)
        columns = list(frame.columns)
        author_keywords_column = _optional_frame_column(columns, _AUTHOR_KEYWORDS_COLUMN)
        index_keywords_column = _optional_frame_column(columns, _INDEX_KEYWORDS_COLUMN)

        for row_number, row in enumerate(frame.to_dict(orient="records"), start=2):
            author_keywords = (
                stringify_label(row.get(author_keywords_column)).strip()
                if author_keywords_column is not None
                else ""
            )
            index_keywords = (
                stringify_label(row.get(index_keywords_column)).strip()
                if index_keywords_column is not None
                else ""
            )
            records.append(
                {
                    "record_id": f"{source.source_dataset}:{source.sheet_name}:{row_number}",
                    "source_dataset": source.source_dataset,
                    "source_sheet": source.sheet_name,
                    "author_keywords": author_keywords,
                    "index_keywords": index_keywords,
                    "keywords_available": bool(author_keywords or index_keywords),
                }
            )

    metadata = pd.DataFrame.from_records(
        records,
        columns=[
            "record_id",
            "source_dataset",
            "source_sheet",
            "author_keywords",
            "index_keywords",
            "keywords_available",
        ],
    )
    if metadata["record_id"].duplicated().any():
        duplicates = metadata.loc[metadata["record_id"].duplicated(), "record_id"].tolist()
        raise ValueError(f"Duplicate governed text metadata record ids found: {duplicates[:5]}")
    return metadata


def build_text_variant_frame(
    dataset_rows: pd.DataFrame,
    *,
    text_variant: str,
    text_metadata: pd.DataFrame,
) -> pd.DataFrame:
    variant_name = validate_text_variant(text_variant)
    merged = dataset_rows.merge(
        text_metadata.loc[
            :,
            ["record_id", "author_keywords", "index_keywords", "keywords_available"],
        ],
        on="record_id",
        how="left",
        validate="one_to_one",
    )
    missing_metadata = merged["keywords_available"].isna()
    if missing_metadata.any():
        missing_ids = merged.loc[missing_metadata, "record_id"].tolist()
        raise ValueError(
            "Missing governed text metadata for record ids: "
            f"{missing_ids[:5]}"
        )

    merged["author_keywords"] = merged["author_keywords"].fillna("")
    merged["index_keywords"] = merged["index_keywords"].fillna("")
    merged["keywords_available"] = merged["keywords_available"].astype(bool)
    merged["keywords_applied"] = False

    if variant_name == TEXT_VARIANT_ABSTRACT_ONLY:
        merged["text_input"] = merged["abstract"].fillna("").map(str)
        return merged

    merged["keywords_applied"] = merged["keywords_available"]
    merged["text_input"] = merged.apply(_compose_keyword_enriched_text, axis=1)
    return merged


def summarize_keyword_coverage(
    variant_rows: pd.DataFrame,
    *,
    text_variant: str,
) -> KeywordCoverageSummary:
    variant_name = validate_text_variant(text_variant)
    row_count = int(len(variant_rows))
    available_rows = int(variant_rows["keywords_available"].sum())
    enriched_rows = int(variant_rows["keywords_applied"].sum())
    availability_rate = 0.0 if row_count == 0 else available_rows / row_count
    coverage_rate = 0.0 if row_count == 0 else enriched_rows / row_count

    summary_rows = (
        variant_rows.groupby(["source_dataset", "split"], dropna=False)
        .agg(
            row_count=("record_id", "size"),
            keyword_rows_available=("keywords_available", "sum"),
            keyword_rows_enriched=("keywords_applied", "sum"),
        )
        .reset_index()
    )
    by_source_split: list[dict[str, object]] = []
    for row in summary_rows.to_dict(orient="records"):
        split_row_count = int(row["row_count"])
        split_available = int(row["keyword_rows_available"])
        split_enriched = int(row["keyword_rows_enriched"])
        by_source_split.append(
            {
                "source_dataset": str(row["source_dataset"]),
                "split": str(row["split"]),
                "row_count": split_row_count,
                "keyword_rows_available": split_available,
                "keyword_rows_enriched": split_enriched,
                "keyword_availability_rate": (
                    0.0 if split_row_count == 0 else split_available / split_row_count
                ),
                "keyword_coverage_rate": (
                    0.0 if split_row_count == 0 else split_enriched / split_row_count
                ),
            }
        )

    return KeywordCoverageSummary(
        text_variant=variant_name,
        row_count=row_count,
        keyword_rows_available=available_rows,
        keyword_rows_enriched=enriched_rows,
        keyword_availability_rate=availability_rate,
        keyword_coverage_rate=coverage_rate,
        by_source_split=tuple(by_source_split),
    )


def _optional_frame_column(columns: list[object], requested_column: str) -> str | None:
    try:
        return resolve_frame_column(columns, requested_column)
    except KeyError:
        return None


def _compose_keyword_enriched_text(row: pd.Series) -> str:
    abstract = stringify_label(row.get("abstract")).strip()
    author_keywords = stringify_label(row.get("author_keywords")).strip()
    index_keywords = stringify_label(row.get("index_keywords")).strip()

    parts = [abstract] if abstract else []
    keyword_sections: list[str] = []
    if author_keywords:
        keyword_sections.append(f"Author Keywords: {author_keywords}")
    if index_keywords:
        keyword_sections.append(f"Index Keywords: {index_keywords}")
    if keyword_sections:
        parts.append(" | ".join(keyword_sections))
    return "\n\n".join(parts)
