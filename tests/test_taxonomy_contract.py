from __future__ import annotations

import pytest

from abstract_classifier.taxonomy import (
    EXPECTED_CLASS_IDS,
    build_taxonomy_inventory,
    load_taxonomy,
    normalize_label,
)


def test_taxonomy_config_matches_expected_arbor_order(project_root) -> None:
    taxonomy = load_taxonomy(project_root / "configs/taxonomy.toml")

    assert [item.identifier for item in taxonomy.classes] == list(EXPECTED_CLASS_IDS)
    assert [item.order for item in taxonomy.classes] == [1, 2, 3, 4, 5, 6]
    assert [item.label for item in taxonomy.classes] == [
        "Tipo 1 - Realismo fuerte",
        "Tipo 2 - Realismo moderado / critico",
        "Tipo 3 - Antirrealismo epistemologico",
        "Tipo 4 - Pragmatismo epistemologico",
        "Tipo 5 - Constructivismo moderado",
        "Tipo 6 - Constructivismo fuerte / relativismo",
    ]


def test_normalize_direct_label_preserves_original_label() -> None:
    result = normalize_label("Tipo 5 CM ")

    assert result.label_original == "Tipo 5 CM "
    assert result.label_canonica == "Tipo 5 - Constructivismo moderado"
    assert result.canonical_id == "tipo_5_constructivismo_moderado"
    assert result.mapping_status == "directo"
    assert result.mapping_notes
    assert result.review_required is False


@pytest.mark.parametrize("legacy_label", ["Tipo 2 RM", "Tipo 2 RC"])
def test_normalize_alias_labels_to_canonical_type_2(legacy_label: str) -> None:
    result = normalize_label(legacy_label)

    assert result.label_original == legacy_label
    assert result.label_canonica == "Tipo 2 - Realismo moderado / critico"
    assert result.canonical_id == "tipo_2_realismo_moderado_critico"
    assert result.mapping_status == "fusionado"
    assert result.review_required is False


@pytest.mark.parametrize("legacy_label", ["", "No"])
def test_blank_or_no_labels_stay_out_of_success_states(legacy_label: str) -> None:
    result = normalize_label(legacy_label)

    assert result.label_original == legacy_label
    assert result.label_canonica is None
    assert result.canonical_id is None
    assert result.mapping_status == "sin_etiqueta"
    assert result.review_required is True


@pytest.mark.parametrize("legacy_label", ["Tipo 6 RF", "Tipo 4 CM "])
def test_unresolved_legacy_labels_require_manual_review(legacy_label: str) -> None:
    result = normalize_label(legacy_label)

    assert result.label_original == legacy_label
    assert result.label_canonica is None
    assert result.canonical_id is None
    assert result.mapping_status == "revision_manual"
    assert result.review_required is True


def test_inventory_splits_direct_alias_and_review_required_rows() -> None:
    inventory = build_taxonomy_inventory()

    assert not inventory.direct_mappings.empty
    assert not inventory.alias_mappings.empty
    assert not inventory.review_rows.empty
    assert set(inventory.alias_mappings["canonical_id"]) == {
        "tipo_2_realismo_moderado_critico"
    }
    assert {"Tipo 6 RF", "No"}.issubset(set(inventory.review_rows["label_original"]))


def test_prepare_inventory_command_writes_markdown_report(
    cli_runner,
    tmp_path,
) -> None:
    output_path = tmp_path / "taxonomy_inventory.md"

    result = cli_runner(
        "prepare",
        "--inventory-output",
        str(output_path),
    )

    assert result.returncode == 0, result.stderr
    report_text = output_path.read_text(encoding="utf-8")
    assert "## Direct mappings" in report_text
    assert "## Alias mappings" in report_text
    assert "## Review-required rows" in report_text
    assert "tipo_2_realismo_moderado_critico" in report_text
    assert "Tipo 2 RM" in report_text
    assert "Tipo 6 RF" in report_text
