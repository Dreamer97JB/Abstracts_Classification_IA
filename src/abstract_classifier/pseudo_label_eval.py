from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any

import pandas as pd

from .taxonomy import resolve_project_path


def _recall_map(metrics_per_class_path: Path) -> dict[str, float]:
    frame = pd.read_csv(metrics_per_class_path)
    return {
        str(row["canonical_id"]): float(row["recall"])
        for _, row in frame.iterrows()
    }


def persist_phase9_pseudo_label_bundle(
    *,
    root: Path,
    full_config_path: Path,
    challenger_run_dir: Path,
    bundle_dir: Path,
) -> None:
    """Write pseudo_label_comparison.csv and pseudo_label_promotion_gate.json (Phase 9)."""
    from .evaluation import evaluate_run
    from .inference import load_theory_inference_config, run_batch_inference
    from .training import load_run_manifest, load_theory_baseline_config

    project_root = root
    full = tomllib.loads(Path(full_config_path).read_text(encoding="utf-8"))
    config = load_theory_baseline_config(full_config_path, root=project_root)
    champion_dir = resolve_project_path(full["champion_run_dir"], root=project_root)
    promotion_gate_path = resolve_project_path(full["promotion_gate_artifact"], root=project_root)
    phase5_ref = resolve_project_path(full["phase5_predictions_reference"], root=project_root)
    pseudo_policy_path = resolve_project_path(
        full["pseudo_training"]["pseudo_policy_json"],
        root=project_root,
    )
    pseudo_policy = json.loads(pseudo_policy_path.read_text(encoding="utf-8"))

    manifest = load_run_manifest(challenger_run_dir)
    run_id = str(manifest["run_id"])

    evaluate_run(
        config=config,
        run_id=run_id,
        output_dir=challenger_run_dir,
        split_name="test",
        root=project_root,
    )

    inf = load_theory_inference_config(root=project_root)
    ch_pred_dir = bundle_dir / "champion_predict_smoke"
    new_pred_dir = bundle_dir / "challenger_predict_smoke"
    ch_pred_dir.mkdir(parents=True, exist_ok=True)
    new_pred_dir.mkdir(parents=True, exist_ok=True)

    run_batch_inference(
        config=inf,
        run_id="phase9_champion_trusted_smoke",
        model_run_dir=champion_dir,
        output_dir=ch_pred_dir,
        root=project_root,
    )
    run_batch_inference(
        config=inf,
        run_id="phase9_challenger_trusted_smoke",
        model_run_dir=challenger_run_dir,
        output_dir=new_pred_dir,
        root=project_root,
    )

    champ_overall_path = champion_dir / "metrics_overall.json"
    new_overall_path = challenger_run_dir / "metrics_overall.json"
    champ_overall = json.loads(champ_overall_path.read_text(encoding="utf-8"))
    new_overall = json.loads(new_overall_path.read_text(encoding="utf-8"))

    champ_recalls = _recall_map(champion_dir / "metrics_per_class.csv")
    new_recalls = _recall_map(challenger_run_dir / "metrics_per_class.csv")

    champ_prod = json.loads(
        (ch_pred_dir / "production_readiness_summary.json").read_text(encoding="utf-8")
    )
    new_prod = json.loads(
        (new_pred_dir / "production_readiness_summary.json").read_text(encoding="utf-8")
    )

    promotion_gate = json.loads(promotion_gate_path.read_text(encoding="utf-8"))

    label_ids = [entry["canonical_id"] for entry in champ_overall.get("label_order", [])]

    def row(
        overall: dict[str, Any],
        recalls: dict[str, float],
        prod: dict[str, Any],
        *,
        raw_gate_candidates: int | None = None,
        conformal_admitted_candidates: int | None = None,
    ) -> dict[str, Any]:
        base: dict[str, Any] = {
            "accuracy": float(overall["accuracy"]),
            "macro_f1": float(overall["macro_f1"]),
            "weighted_f1": float(overall["weighted_f1"]),
            "retained_accuracy_reference": float(promotion_gate.get("retained_accuracy", 0.0)),
            "auto_ready_count": int(prod.get("auto_ready_count", 0)),
            "expert_review_queue_count": int(prod.get("expert_review_queue_count", 0)),
            "review_reduction_vs_phase5": int(prod.get("review_reduction_vs_phase5", 0)),
            "raw_row_gate_admitted_count": raw_gate_candidates,
            "conformal_admitted_count": conformal_admitted_candidates,
        }
        for cid in label_ids:
            base[f"recall_{cid}"] = float(recalls.get(cid, 0.0))
        return base

    rows = [
        row(champ_overall, champ_recalls, champ_prod),
        row(
            new_overall,
            new_recalls,
            new_prod,
            raw_gate_candidates=int(pseudo_policy.get("raw_row_gate_admitted_count", 0)),
            conformal_admitted_candidates=int(pseudo_policy.get("conformal_admitted_count", 0)),
        ),
    ]
    for item, key in zip(rows, ("gold_only_champion", "gold_plus_pseudo_wave_01")):
        item["comparison_row"] = key
    comparison = pd.DataFrame(rows)
    comparison_path = bundle_dir / "pseudo_label_comparison.csv"
    comparison.to_csv(comparison_path, index=False)

    c0 = rows[0]
    c1 = rows[1]
    reasons: list[str] = []
    flags: list[str] = []
    if c1["macro_f1"] + 1e-12 < c0["macro_f1"]:
        flags.append("macro_f1_regression")
    if c1["weighted_f1"] + 1e-12 < c0["weighted_f1"]:
        flags.append("weighted_f1_regression")
    if c1["accuracy"] + 1e-12 < c0["accuracy"] - 0.01:
        flags.append("accuracy_regression_gt_1pct")
    prod_ok = (c1["auto_ready_count"] > c0["auto_ready_count"]) or (
        c1["expert_review_queue_count"] < c0["expert_review_queue_count"]
    )
    if not prod_ok:
        flags.append("production_review_not_improved")
    if (
        pseudo_policy.get("admission_options", {}).get("enable_conformal_gate")
        and int(pseudo_policy.get("raw_row_gate_admitted_count", 0)) > 0
        and int(pseudo_policy.get("conformal_admitted_count", 0)) == 0
    ):
        flags.append("conformal_wave_too_small")
    for cid in label_ids:
        if c1[f"recall_{cid}"] + 1e-12 < c0[f"recall_{cid}"] - 0.10:
            flags.append(f"recall_drop_{cid}")

    if not flags:
        decision = "promote_to_phase10"
        reasons.append("All promotion checks passed relative to sentence_transformer_logreg_test.")
        next_action = "Proceed to Phase 10 governed production re-run planning."
    elif "macro_f1_regression" in flags or "weighted_f1_regression" in flags:
        decision = "reject_pseudo_wave"
        reasons.append("Core test metrics regressed versus the Phase 7 champion.")
        next_action = "Discard this pseudo-label wave and revisit admission policy."
    elif "conformal_wave_too_small" in flags:
        decision = "hold_for_phase9_iteration"
        reasons.append("The conformal filter reduced the pseudo-label wave below usable size.")
        next_action = "Tune conformal alpha or upstream admission quality before retraining."
    else:
        decision = "hold_for_phase9_iteration"
        reasons.append("Mixed signals: investigate flagged dimensions before promotion.")
        next_action = "Tune pseudo admission or model head, then retrain."

    gate = {
        "promotion_decision": decision,
        "decision_reasons": reasons,
        "regression_flags": flags,
        "next_action": next_action,
        "champion_reference": "sentence_transformer_logreg_test",
        "comparison_artifact": comparison_path.name,
        "phase5_predictions_reference": str(phase5_ref),
        "raw_row_gate_admitted_count": int(pseudo_policy.get("raw_row_gate_admitted_count", 0)),
        "conformal_admitted_count": int(pseudo_policy.get("conformal_admitted_count", 0)),
    }
    (bundle_dir / "pseudo_label_promotion_gate.json").write_text(
        json.dumps(gate, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
