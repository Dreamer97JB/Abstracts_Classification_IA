from __future__ import annotations

import re
import tomllib
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TAXONOMY_CONFIG = Path("configs/taxonomy.toml")
DEFAULT_TAXONOMY_INVENTORY = Path("reports/taxonomy_inventory.md")

EXPECTED_CLASS_IDS = (
    "tipo_1_realismo_fuerte",
    "tipo_2_realismo_moderado_critico",
    "tipo_3_antirrealismo_epistemologico",
    "tipo_4_pragmatismo_epistemologico",
    "tipo_5_constructivismo_moderado",
    "tipo_6_constructivismo_fuerte_relativismo",
)

DIRECT_LEGACY_LABELS = {
    "TIPO 1 RF": "tipo_1_realismo_fuerte",
    "TIPO 3 AE": "tipo_3_antirrealismo_epistemologico",
    "TIPO 4 PE": "tipo_4_pragmatismo_epistemologico",
    "TIPO 5 CM": "tipo_5_constructivismo_moderado",
    "TIPO 6 CF R": "tipo_6_constructivismo_fuerte_relativismo",
}

APPROVED_ALIAS_LABELS = {
    "TIPO 2 RM": "tipo_2_realismo_moderado_critico",
    "TIPO 2 RC": "tipo_2_realismo_moderado_critico",
}

NO_LABEL_KEYS = frozenset({"NO"})

_NON_ALNUM_PATTERN = re.compile(r"[^A-Z0-9]+")


@dataclass(frozen=True)
class CanonicalTaxonomyClass:
    order: int
    identifier: str
    label: str
    article_label: str


@dataclass(frozen=True)
class TaxonomyContract:
    version: str
    source_of_truth: str
    classes: tuple[CanonicalTaxonomyClass, ...]

    def class_by_id(self, identifier: str) -> CanonicalTaxonomyClass:
        for taxonomy_class in self.classes:
            if taxonomy_class.identifier == identifier:
                return taxonomy_class
        raise KeyError(f"Unknown taxonomy identifier: {identifier}")


@dataclass(frozen=True)
class TaxonomyNormalization:
    label_original: str
    label_canonica: str | None
    canonical_id: str | None
    mapping_status: str
    mapping_notes: str
    review_required: bool

    def as_record(self) -> dict[str, Any]:
        return {
            "label_original": self.label_original,
            "label_canonica": self.label_canonica,
            "canonical_id": self.canonical_id,
            "mapping_status": self.mapping_status,
            "mapping_notes": self.mapping_notes,
            "review_required": self.review_required,
        }


@dataclass(frozen=True)
class SupervisedSource:
    source_dataset: str
    workbook_path: Path
    sheet_name: str
    label_column: str
    title_column: str


@dataclass(frozen=True)
class TaxonomyInventory:
    taxonomy: TaxonomyContract
    source_rows: pd.DataFrame
    direct_mappings: pd.DataFrame
    alias_mappings: pd.DataFrame
    review_rows: pd.DataFrame


DEFAULT_SUPERVISED_SOURCES = (
    SupervisedSource(
        source_dataset="seed",
        workbook_path=Path("Seed/Seed.xlsx"),
        sheet_name="Clasificados",
        label_column="Clasificación",
        title_column="Title",
    ),
    SupervisedSource(
        source_dataset="muestras",
        workbook_path=Path("Database/Scopus_database.xlsx"),
        sheet_name="Muestras",
        label_column="Clasificación",
        title_column="Title",
    ),
)


def resolve_project_path(path: str | Path, root: Path | None = None) -> Path:
    project_root = root or ROOT
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = project_root / candidate
    return candidate.resolve()


def stringify_label(value: object) -> str:
    if value is None:
        return ""
    if pd.isna(value):
        return ""
    return str(value)


def normalize_lookup_key(value: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", value)
    ascii_text = ascii_text.encode("ascii", "ignore").decode("ascii")
    ascii_text = ascii_text.upper()
    return _NON_ALNUM_PATTERN.sub(" ", ascii_text).strip()


def load_taxonomy(
    path: str | Path = DEFAULT_TAXONOMY_CONFIG,
    root: Path | None = None,
) -> TaxonomyContract:
    config_path = resolve_project_path(path, root=root)
    data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    raw_classes = data.get("classes", [])

    if len(raw_classes) != len(EXPECTED_CLASS_IDS):
        raise ValueError(
            "Taxonomy config must define exactly "
            f"{len(EXPECTED_CLASS_IDS)} canonical classes."
        )

    classes = tuple(
        CanonicalTaxonomyClass(
            order=int(item["order"]),
            identifier=str(item["id"]),
            label=str(item["label"]),
            article_label=str(item.get("article_label", item["label"])),
        )
        for item in raw_classes
    )

    class_ids = tuple(item.identifier for item in classes)
    if class_ids != EXPECTED_CLASS_IDS:
        raise ValueError(
            "Taxonomy identifiers must match the fixed Arbor contract order."
        )

    class_orders = tuple(item.order for item in classes)
    if class_orders != tuple(range(1, len(EXPECTED_CLASS_IDS) + 1)):
        raise ValueError("Taxonomy class order must run sequentially from 1 to 6.")

    return TaxonomyContract(
        version=str(data.get("version", "")),
        source_of_truth=str(data.get("source_of_truth", "")),
        classes=classes,
    )


def _direct_label_lookup(taxonomy: TaxonomyContract) -> dict[str, str]:
    direct_lookup = {
        lookup_key: canonical_id
        for lookup_key, canonical_id in DIRECT_LEGACY_LABELS.items()
    }

    for taxonomy_class in taxonomy.classes:
        direct_lookup[
            normalize_lookup_key(taxonomy_class.label)
        ] = taxonomy_class.identifier
        direct_lookup[
            normalize_lookup_key(taxonomy_class.article_label)
        ] = taxonomy_class.identifier

    return direct_lookup


def _normalization_result(
    label_original: str,
    taxonomy_class: CanonicalTaxonomyClass | None,
    mapping_status: str,
    mapping_notes: str,
    review_required: bool,
) -> TaxonomyNormalization:
    return TaxonomyNormalization(
        label_original=label_original,
        label_canonica=taxonomy_class.label if taxonomy_class else None,
        canonical_id=taxonomy_class.identifier if taxonomy_class else None,
        mapping_status=mapping_status,
        mapping_notes=mapping_notes,
        review_required=review_required,
    )


def normalize_label(
    label: object,
    taxonomy: TaxonomyContract | None = None,
) -> TaxonomyNormalization:
    contract = taxonomy or load_taxonomy()
    label_original = stringify_label(label)
    lookup_key = normalize_lookup_key(label_original.strip())

    if not lookup_key:
        return _normalization_result(
            label_original=label_original,
            taxonomy_class=None,
            mapping_status="sin_etiqueta",
            mapping_notes=(
                "Blank legacy label; keep as review case and exclude from "
                "training until resolved."
            ),
            review_required=True,
        )

    if lookup_key in NO_LABEL_KEYS:
        return _normalization_result(
            label_original=label_original,
            taxonomy_class=None,
            mapping_status="sin_etiqueta",
            mapping_notes=(
                "Legacy label marks a non-labeled record; keep as review case "
                "instead of assigning a canonical class."
            ),
            review_required=True,
        )

    direct_lookup = _direct_label_lookup(contract)
    if lookup_key in direct_lookup:
        taxonomy_class = contract.class_by_id(direct_lookup[lookup_key])
        return _normalization_result(
            label_original=label_original,
            taxonomy_class=taxonomy_class,
            mapping_status="directo",
            mapping_notes=(
                "Legacy label matches the canonical Arbor taxonomy contract."
            ),
            review_required=False,
        )

    if lookup_key in APPROVED_ALIAS_LABELS:
        taxonomy_class = contract.class_by_id(APPROVED_ALIAS_LABELS[lookup_key])
        return _normalization_result(
            label_original=label_original,
            taxonomy_class=taxonomy_class,
            mapping_status="fusionado",
            mapping_notes=(
                "Approved alias policy merges legacy RM/RC labels into "
                "canonical Type 2."
            ),
            review_required=False,
        )

    return _normalization_result(
        label_original=label_original,
        taxonomy_class=None,
        mapping_status="revision_manual",
        mapping_notes=(
            "Legacy label has no approved canonical mapping; manual review is "
            "required before supervised use."
        ),
        review_required=True,
    )


def normalize_labels(
    labels: list[object],
    taxonomy: TaxonomyContract | None = None,
) -> list[TaxonomyNormalization]:
    contract = taxonomy or load_taxonomy()
    return [normalize_label(label, taxonomy=contract) for label in labels]


def load_supervised_label_rows(
    taxonomy: TaxonomyContract | None = None,
    root: Path | None = None,
    sources: tuple[SupervisedSource, ...] = DEFAULT_SUPERVISED_SOURCES,
) -> pd.DataFrame:
    contract = taxonomy or load_taxonomy(root=root)
    records: list[dict[str, Any]] = []

    for source in sources:
        workbook_path = resolve_project_path(source.workbook_path, root=root)
        frame = pd.read_excel(workbook_path, sheet_name=source.sheet_name)

        if source.label_column not in frame.columns:
            raise KeyError(
                f"Label column `{source.label_column}` not found in "
                f"{source.workbook_path}::{source.sheet_name}."
            )
        if source.title_column not in frame.columns:
            raise KeyError(
                f"Title column `{source.title_column}` not found in "
                f"{source.workbook_path}::{source.sheet_name}."
            )

        for row_number, row in enumerate(frame.to_dict(orient="records"), start=2):
            normalization = normalize_label(
                row.get(source.label_column),
                taxonomy=contract,
            )
            record = {
                "source_dataset": source.source_dataset,
                "source_workbook": source.workbook_path.as_posix(),
                "source_sheet": source.sheet_name,
                "row_number": row_number,
                "title": stringify_label(row.get(source.title_column)).strip(),
            }
            record.update(normalization.as_record())
            records.append(record)

    return pd.DataFrame.from_records(records)


def _summarize_rows(rows: pd.DataFrame, mapping_status: str) -> pd.DataFrame:
    filtered = rows.loc[rows["mapping_status"] == mapping_status].copy()
    if filtered.empty:
        return filtered

    summary = (
        filtered.groupby(
            [
                "source_dataset",
                "label_original",
                "canonical_id",
                "label_canonica",
                "mapping_status",
            ],
            dropna=False,
        )
        .size()
        .reset_index(name="count")
        .sort_values(
            by=["source_dataset", "count", "label_original"],
            ascending=[True, False, True],
        )
        .reset_index(drop=True)
    )
    return summary


def build_taxonomy_inventory(
    taxonomy: TaxonomyContract | None = None,
    root: Path | None = None,
    sources: tuple[SupervisedSource, ...] = DEFAULT_SUPERVISED_SOURCES,
) -> TaxonomyInventory:
    contract = taxonomy or load_taxonomy(root=root)
    source_rows = load_supervised_label_rows(
        taxonomy=contract,
        root=root,
        sources=sources,
    )

    review_rows = (
        source_rows.loc[
            source_rows["review_required"],
            [
                "source_dataset",
                "row_number",
                "title",
                "label_original",
                "mapping_status",
                "mapping_notes",
            ],
        ]
        .copy()
        .sort_values(by=["source_dataset", "row_number"])
        .reset_index(drop=True)
    )

    return TaxonomyInventory(
        taxonomy=contract,
        source_rows=source_rows,
        direct_mappings=_summarize_rows(source_rows, "directo"),
        alias_mappings=_summarize_rows(source_rows, "fusionado"),
        review_rows=review_rows,
    )


def _format_report_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        if not value:
            return "<BLANK>"
        return value.replace("|", "\\|").replace("\n", " ").strip() or "<BLANK>"
    return str(value).replace("|", "\\|")


def _markdown_table(frame: pd.DataFrame, columns: list[str]) -> list[str]:
    if frame.empty:
        return ["_None_"]

    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in frame.to_dict(orient="records"):
        values = [_format_report_value(row.get(column)) for column in columns]
        lines.append("| " + " | ".join(values) + " |")
    return lines


def render_taxonomy_inventory_report(inventory: TaxonomyInventory) -> str:
    lines: list[str] = []
    lines.append("# Taxonomy Inventory")
    lines.append("")
    lines.append(
        "Canonical taxonomy and legacy label mapping inventory for Phase 2 input."
    )
    lines.append("")
    lines.append(f"Source of truth: `{inventory.taxonomy.source_of_truth}`")
    lines.append("")
    lines.append("## Canonical taxonomy")
    lines.append("")
    for taxonomy_class in inventory.taxonomy.classes:
        lines.append(
            f"- `{taxonomy_class.identifier}`: `{taxonomy_class.label}`"
        )
    lines.append("")

    source_summary = (
        inventory.source_rows.groupby(
            ["source_dataset", "source_workbook", "source_sheet"],
            dropna=False,
        )
        .size()
        .reset_index(name="rows")
        .sort_values(by=["source_dataset"])
        .reset_index(drop=True)
    )

    lines.append("## Supervised sources")
    lines.append("")
    lines.extend(
        _markdown_table(
            source_summary,
            ["source_dataset", "source_workbook", "source_sheet", "rows"],
        )
    )
    lines.append("")

    lines.append("## Direct mappings")
    lines.append("")
    lines.extend(
        _markdown_table(
            inventory.direct_mappings,
            [
                "source_dataset",
                "label_original",
                "count",
                "canonical_id",
                "label_canonica",
            ],
        )
    )
    lines.append("")

    lines.append("## Alias mappings")
    lines.append("")
    lines.extend(
        _markdown_table(
            inventory.alias_mappings,
            [
                "source_dataset",
                "label_original",
                "count",
                "canonical_id",
                "label_canonica",
            ],
        )
    )
    lines.append("")

    lines.append("## Review-required rows")
    lines.append("")
    lines.extend(
        _markdown_table(
            inventory.review_rows,
            [
                "source_dataset",
                "row_number",
                "title",
                "label_original",
                "mapping_status",
                "mapping_notes",
            ],
        )
    )
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_taxonomy_inventory_report(
    output: str | Path = DEFAULT_TAXONOMY_INVENTORY,
    taxonomy_path: str | Path = DEFAULT_TAXONOMY_CONFIG,
    root: Path | None = None,
) -> Path:
    project_root = root or ROOT
    inventory = build_taxonomy_inventory(
        taxonomy=load_taxonomy(taxonomy_path, root=project_root),
        root=project_root,
    )

    output_path = Path(output)
    if not output_path.is_absolute():
        output_path = project_root / output_path
    output_path = output_path.resolve()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        render_taxonomy_inventory_report(inventory),
        encoding="utf-8",
    )
    return output_path
