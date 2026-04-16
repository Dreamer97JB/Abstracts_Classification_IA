from __future__ import annotations

from pathlib import Path

from abstract_classifier.taxonomy import load_supervision_policy


def test_supervision_policy_loads_candidate_sources_and_routing(
    project_root: Path,
) -> None:
    policy = load_supervision_policy(project_root / "configs" / "supervision.toml")

    assert policy.version == "1"
    assert policy.default_gold_source == "seed"
    assert policy.routing.training_default_bucket == "candidate_gold"
    assert policy.routing.evaluation_default_bucket == "manual_review"
    assert policy.routing.inference_default_bucket == "not_for_inference"
    assert policy.quality.min_abstract_words == 20
    assert policy.split_defaults.version == "phase2_v1"
    assert policy.split_defaults.seed == 20260416

    by_name = {source.name: source for source in policy.sources}
    assert set(by_name) == {"seed", "muestras"}
    assert by_name["seed"].source_dataset == "seed"
    assert by_name["seed"].sheet_name == "Clasificados"
    assert by_name["muestras"].source_dataset == "muestras"
    assert by_name["muestras"].sheet_name == "Muestras"


def test_supervision_policy_contains_direct_alias_and_review_rules(
    project_root: Path,
) -> None:
    policy = load_supervision_policy(project_root / "configs" / "supervision.toml")
    by_label = {rule.legacy_label: rule for rule in policy.theory_mappings}

    assert by_label["Tipo 2 RM"].mapping_status == "fusionado"
    assert by_label["Tipo 2 RM"].canonical_id == "tipo_2_realismo_moderado_critico"
    assert by_label["Tipo 2 RC"].mapping_status == "fusionado"
    assert by_label["Tipo 6 RF"].mapping_status == "revision_manual"
    assert by_label["Tipo 4 CM"].mapping_status == "revision_manual"
    assert by_label["No"].mapping_status == "sin_etiqueta"
    assert by_label[""].mapping_status == "sin_etiqueta"
    assert by_label["Tipo 6 CF - R"].mapping_status == "directo"
