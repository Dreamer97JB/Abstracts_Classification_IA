from __future__ import annotations

import tomllib
from pathlib import Path

from ..contracts import SourceManifest, SourceRole, SourceSpec


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
