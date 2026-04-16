from __future__ import annotations

from pathlib import Path

from abstract_classifier.contracts import NormalizedSourceRow
from abstract_classifier.io import load_normalized_rows
from abstract_classifier.io.sources import load_source_manifest


def test_source_manifest_declares_governed_client_sources(project_root: Path) -> None:
    manifest = load_source_manifest(project_root / "configs" / "sources.toml")

    assert manifest.version == 1
    assert manifest.lineage_fields == (
        "source_dataset",
        "source_sheet",
        "source_path",
        "source_role",
    )
    assert len(manifest.sources) == 4

    by_dataset = {source.source_dataset: source for source in manifest.sources}

    assert by_dataset["google_corpus"].sheet == "gschoolar_resultsPeriod_abs"
    assert by_dataset["google_corpus"].role == "corpus"

    assert by_dataset["scopus_base"].sheet == "Base"
    assert by_dataset["scopus_base"].role == "corpus"

    assert by_dataset["seed_gold"].sheet == "Clasificados"
    assert by_dataset["seed_gold"].role == "initial_gold"

    assert by_dataset["scopus_muestras"].sheet == "Muestras"
    assert by_dataset["scopus_muestras"].role == "aux_review"


def test_load_normalized_rows_emits_required_lineage_fields(project_root: Path) -> None:
    rows = load_normalized_rows(
        project_root / "configs" / "sources.toml",
        project_root=project_root,
        row_limit=1,
    )

    assert len(rows) == 4
    assert all(isinstance(row, NormalizedSourceRow) for row in rows)
    assert {row.source_dataset for row in rows} == {
        "google_corpus",
        "scopus_base",
        "seed_gold",
        "scopus_muestras",
    }

    for row in rows:
        assert row.source_sheet
        assert row.source_path.endswith(".xlsx")
        assert row.title_normalized
        assert isinstance(row.doi_normalized, str)
        assert isinstance(row.year, int)
