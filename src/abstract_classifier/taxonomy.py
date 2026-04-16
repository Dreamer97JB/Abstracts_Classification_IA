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
DEFAULT_SUPERVISION_CONFIG = Path("configs/supervision.toml")
DEFAULT_TAXONOMY_INVENTORY = Path("reports/taxonomy_inventory.md")

EXPECTED_CLASS_IDS = (
    "tipo_1_realismo_fuerte",
    "tipo_2_realismo_moderado_critico",
    "tipo_3_antirrealismo_epistemologico",
    "tipo_4_pragmatismo_epistemologico",
    "tipo_5_constructivismo_moderado",
    "tipo_6_constructivismo_fuerte_relativismo",
)
ALLOWED_MAPPING_STATUSES = frozenset(
    {"directo", "fusionado", "revision_manual", "sin_etiqueta"}
)

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
class TheoryMappingRule:
    legacy_label: str
    mapping_status: str
    canonical_id: str | None
    mapping_notes: str
    review_required: bool

    @property
    def lookup_key(self) -> str:
        return normalize_lookup_key(self.legacy_label)


@dataclass(frozen=True)
class SupervisedSource:
    name: str
    source_dataset: str
    workbook_path: Path
    sheet_name: str
    label_column: str
    title_column: str
    abstract_column: str
    year_column: str
    doi_column: str
    training_bucket: str
    evaluation_bucket: str
    inference_bucket: str


@dataclass(frozen=True)
class RoutingBuckets:
    training_default_bucket: str
    evaluation_default_bucket: str
    inference_default_bucket: str


@dataclass(frozen=True)
class SupervisionPolicy:
    version: str
    taxonomy_config: str
    default_gold_source: str
    routing: RoutingBuckets
    sources: tuple[SupervisedSource, ...]
    theory_mappings: tuple[TheoryMappingRule, ...]

    def rule_by_lookup_key(self) -> dict[str, TheoryMappingRule]:
        lookup: dict[str, TheoryMappingRule] = {}
        for rule in self.theory_mappings:
            lookup[rule.lookup_key] = rule
        return lookup


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
class TaxonomyInventory:
    taxonomy: TaxonomyContract
    source_rows: pd.DataFrame
    direct_mappings: pd.DataFrame
    alias_mappings: pd.DataFrame
    review_rows: pd.DataFrame


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


def resolve_frame_column(columns: list[object], requested_column: str) -> str:
    requested_key = normalize_lookup_key(requested_column)
    for column in columns:
        if normalize_lookup_key(str(column)) == requested_key:
            return str(column)
    raise KeyError(f"Column `{requested_column}` not found in worksheet.")


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


def load_supervision_policy(
    path: str | Path = DEFAULT_SUPERVISION_CONFIG,
    root: Path | None = None,
) -> SupervisionPolicy:
    config_path = resolve_project_path(path, root=root)
    data = tomllib.loads(config_path.read_text(encoding="utf-8"))

    routing_data = data.get("routing", {})
    routing = RoutingBuckets(
        training_default_bucket=str(routing_data.get("training_default_bucket", "")),
        evaluation_default_bucket=str(
            routing_data.get("evaluation_default_bucket", "")
        ),
        inference_default_bucket=str(routing_data.get("inference_default_bucket", "")),
    )
    if not all(
        (
            routing.training_default_bucket,
            routing.evaluation_default_bucket,
            routing.inference_default_bucket,
        )
    ):
        raise ValueError("Supervision routing buckets must all be configured.")

    raw_sources = data.get("sources", [])
    if not raw_sources:
        raise ValueError("Supervision policy must declare supervised sources.")
    sources = tuple(
        SupervisedSource(
            name=str(item["name"]),
            source_dataset=str(item["source_dataset"]),
            workbook_path=Path(str(item["workbook_path"])),
            sheet_name=str(item["sheet_name"]),
            label_column=str(item["label_column"]),
            title_column=str(item["title_column"]),
            abstract_column=str(item["abstract_column"]),
            year_column=str(item["year_column"]),
            doi_column=str(item["doi_column"]),
            training_bucket=str(item["training_bucket"]),
            evaluation_bucket=str(item["evaluation_bucket"]),
            inference_bucket=str(item["inference_bucket"]),
        )
        for item in raw_sources
    )

    raw_mappings = data.get("theory_mappings", [])
    if not raw_mappings:
        raise ValueError("Supervision policy must declare theory mappings.")

    theory_mappings = tuple(
        _build_theory_mapping_rule(item) for item in raw_mappings
    )
    blank_rules = [rule for rule in theory_mappings if rule.lookup_key == ""]
    if len(blank_rules) != 1:
        raise ValueError("Supervision policy must define exactly one blank label rule.")

    lookup_keys = [rule.lookup_key for rule in theory_mappings]
    if len(lookup_keys) != len(set(lookup_keys)):
        raise ValueError("Supervision theory mappings must use unique lookup keys.")

    return SupervisionPolicy(
        version=str(data.get("version", "")),
        taxonomy_config=str(data.get("taxonomy_config", DEFAULT_TAXONOMY_CONFIG)),
        default_gold_source=str(data.get("default_gold_source", "")),
        routing=routing,
        sources=sources,
        theory_mappings=theory_mappings,
    )


def _build_theory_mapping_rule(data: dict[str, object]) -> TheoryMappingRule:
    mapping_status = str(data["mapping_status"])
    if mapping_status not in ALLOWED_MAPPING_STATUSES:
        raise ValueError(f"Unsupported theory mapping status: {mapping_status}")

    canonical_id = data.get("canonical_id")
    canonical_value = (
        str(canonical_id).strip()
        if canonical_id is not None and str(canonical_id).strip()
        else None
    )

    if mapping_status in {"directo", "fusionado"} and canonical_value is None:
        raise ValueError(
            "Direct and alias theory mappings must declare a canonical_id."
        )
    if mapping_status in {"revision_manual", "sin_etiqueta"} and canonical_value is not None:
        raise ValueError(
            "Review-only and no-label mappings must not declare a canonical_id."
        )

    return TheoryMappingRule(
        legacy_label=str(data.get("legacy_label", "")),
        mapping_status=mapping_status,
        canonical_id=canonical_value,
        mapping_notes=str(data.get("mapping_notes", "")),
        review_required=bool(data.get("review_required", False)),
    )


def _taxonomy_label_lookup(taxonomy: TaxonomyContract) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for taxonomy_class in taxonomy.classes:
        lookup[normalize_lookup_key(taxonomy_class.label)] = taxonomy_class.identifier
        lookup[normalize_lookup_key(taxonomy_class.article_label)] = taxonomy_class.identifier
    return lookup


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
    policy: SupervisionPolicy | None = None,
) -> TaxonomyNormalization:
    contract = taxonomy or load_taxonomy()
    supervision_policy = policy or load_supervision_policy()
    label_original = stringify_label(label)
    lookup_key = normalize_lookup_key(label_original.strip())

    configured_rules = supervision_policy.rule_by_lookup_key()
    if lookup_key in configured_rules:
        rule = configured_rules[lookup_key]
        taxonomy_class = (
            contract.class_by_id(rule.canonical_id)
            if rule.canonical_id is not None
            else None
        )
        return _normalization_result(
            label_original=label_original,
            taxonomy_class=taxonomy_class,
            mapping_status=rule.mapping_status,
            mapping_notes=rule.mapping_notes,
            review_required=rule.review_required,
        )

    taxonomy_lookup = _taxonomy_label_lookup(contract)
    if lookup_key in taxonomy_lookup:
        taxonomy_class = contract.class_by_id(taxonomy_lookup[lookup_key])
        return _normalization_result(
            label_original=label_original,
            taxonomy_class=taxonomy_class,
            mapping_status="directo",
            mapping_notes=(
                "Label already matches the canonical Arbor taxonomy contract."
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
    policy: SupervisionPolicy | None = None,
) -> list[TaxonomyNormalization]:
    contract = taxonomy or load_taxonomy()
    supervision_policy = policy or load_supervision_policy()
    return [
        normalize_label(label, taxonomy=contract, policy=supervision_policy)
        for label in labels
    ]


def load_supervised_label_rows(
    taxonomy: TaxonomyContract | None = None,
    root: Path | None = None,
    sources: tuple[SupervisedSource, ...] | None = None,
    policy: SupervisionPolicy | None = None,
) -> pd.DataFrame:
    contract = taxonomy or load_taxonomy(root=root)
    supervision_policy = policy or load_supervision_policy(root=root)
    active_sources = sources or supervision_policy.sources
    records: list[dict[str, Any]] = []

    for source in active_sources:
        workbook_path = resolve_project_path(source.workbook_path, root=root)
        frame = pd.read_excel(workbook_path, sheet_name=source.sheet_name)
        columns = list(frame.columns)

        label_column = resolve_frame_column(columns, source.label_column)
        title_column = resolve_frame_column(columns, source.title_column)

        for row_number, row in enumerate(frame.to_dict(orient="records"), start=2):
            normalization = normalize_label(
                row.get(label_column),
                taxonomy=contract,
                policy=supervision_policy,
            )
            record = {
                "source_dataset": source.source_dataset,
                "source_workbook": source.workbook_path.as_posix(),
                "source_sheet": source.sheet_name,
                "row_number": row_number,
                "title": stringify_label(row.get(title_column)).strip(),
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
    sources: tuple[SupervisedSource, ...] | None = None,
    policy: SupervisionPolicy | None = None,
) -> TaxonomyInventory:
    supervision_policy = policy or load_supervision_policy(root=root)
    contract = taxonomy or load_taxonomy(
        supervision_policy.taxonomy_config,
        root=root,
    )
    source_rows = load_supervised_label_rows(
        taxonomy=contract,
        root=root,
        sources=sources,
        policy=supervision_policy,
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
        lines.append(f"- `{taxonomy_class.identifier}`: `{taxonomy_class.label}`")
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
    supervision_path: str | Path = DEFAULT_SUPERVISION_CONFIG,
    root: Path | None = None,
) -> Path:
    project_root = root or ROOT
    supervision_policy = load_supervision_policy(supervision_path, root=project_root)
    inventory = build_taxonomy_inventory(
        taxonomy=load_taxonomy(taxonomy_path, root=project_root),
        root=project_root,
        policy=supervision_policy,
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
