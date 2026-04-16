from __future__ import annotations

import pytest

from abstract_classifier.taxonomy import EXPECTED_CLASS_IDS, load_taxonomy, normalize_label


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
