from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class CanarySliceMetrics:
    rows: int
    auto_ready_count: int
    auto_ready_rate: float
    opposition_risk_count: int
    opposition_risk_rate: float
    opposition_risk_auto_classified: int
    needs_review_count: int
    insufficient_theory_signal_count: int
    out_of_scope_theory_count: int


def _load_gate_config(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _compute_metrics(predictions_path: Path) -> CanarySliceMetrics:
    frame = pd.read_csv(predictions_path)
    rows = int(len(frame))
    if rows == 0:
        raise ValueError(f"Predictions file is empty: {predictions_path}")

    auto_ready_mask = frame["delivery_tier"].astype(str) == "auto_ready"
    opposition_mask = frame["review_opposition_risk"].astype(bool)
    auto_classified_mask = frame["review_state"].astype(str) == "auto_classified"

    return CanarySliceMetrics(
        rows=rows,
        auto_ready_count=int(auto_ready_mask.sum()),
        auto_ready_rate=float(auto_ready_mask.mean()),
        opposition_risk_count=int(opposition_mask.sum()),
        opposition_risk_rate=float(opposition_mask.mean()),
        opposition_risk_auto_classified=int((opposition_mask & auto_classified_mask).sum()),
        needs_review_count=int((frame["review_state"].astype(str) == "needs_review").sum()),
        insufficient_theory_signal_count=int(
            (frame["review_state"].astype(str) == "insufficient_theory_signal").sum()
        ),
        out_of_scope_theory_count=int((frame["review_state"].astype(str) == "out_of_scope_theory").sum()),
    )


def _pp(value: float) -> float:
    return value * 100.0


def run_report(
    *,
    candidate_predictions: Path,
    champion_predictions: Path,
    gate_config: Path,
    output_dir: Path,
    label: str,
) -> dict:
    gate = _load_gate_config(gate_config)
    candidate = _compute_metrics(candidate_predictions)
    champion = _compute_metrics(champion_predictions)

    max_opp_auto = int(gate["gates"]["max_opposition_risk_auto_classified"])
    max_auto_drop_pp = float(gate["gates"]["max_auto_ready_rate_drop_pp"])

    auto_ready_drop_pp = _pp(champion.auto_ready_rate - candidate.auto_ready_rate)
    opposition_auto_pass = candidate.opposition_risk_auto_classified <= max_opp_auto
    auto_ready_pass = auto_ready_drop_pp <= max_auto_drop_pp

    decision = "pass" if (opposition_auto_pass and auto_ready_pass) else "fail"

    payload = {
        "label": label,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_predictions": str(candidate_predictions),
        "champion_predictions": str(champion_predictions),
        "gate_config": str(gate_config),
        "candidate": asdict(candidate),
        "champion": asdict(champion),
        "deltas": {
            "auto_ready_rate_pp_candidate_minus_champion": _pp(candidate.auto_ready_rate - champion.auto_ready_rate),
            "auto_ready_rate_drop_pp_champion_minus_candidate": auto_ready_drop_pp,
            "opposition_risk_rate_pp_candidate_minus_champion": _pp(
                candidate.opposition_risk_rate - champion.opposition_risk_rate
            ),
            "opposition_risk_auto_classified_candidate_minus_champion": (
                candidate.opposition_risk_auto_classified - champion.opposition_risk_auto_classified
            ),
        },
        "gates": {
            "opposition_risk_auto_classified_max": max_opp_auto,
            "auto_ready_rate_drop_pp_max": max_auto_drop_pp,
            "opposition_risk_auto_classified_pass": opposition_auto_pass,
            "auto_ready_rate_drop_pass": auto_ready_pass,
        },
        "decision": decision,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{label}_canary_report.json"
    md_path = output_dir / f"{label}_canary_report.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [
        f"# Canary Daily Report: {label}",
        "",
        f"- Decision: **{decision.upper()}**",
        f"- Generated (UTC): `{payload['generated_at_utc']}`",
        "",
        "## Candidate vs Champion",
        f"- Candidate auto_ready: {candidate.auto_ready_count}/{candidate.rows} ({_pp(candidate.auto_ready_rate):.2f}%)",
        f"- Champion auto_ready: {champion.auto_ready_count}/{champion.rows} ({_pp(champion.auto_ready_rate):.2f}%)",
        f"- Auto_ready drop (champion-candidate): {auto_ready_drop_pp:.2f} pp (max allowed {max_auto_drop_pp:.2f})",
        f"- Candidate opposition-risk: {candidate.opposition_risk_count}/{candidate.rows} ({_pp(candidate.opposition_risk_rate):.2f}%)",
        f"- Champion opposition-risk: {champion.opposition_risk_count}/{champion.rows} ({_pp(champion.opposition_risk_rate):.2f}%)",
        f"- Candidate opposition-risk auto-classified: {candidate.opposition_risk_auto_classified} (max allowed {max_opp_auto})",
        "",
        "## Gate Status",
        f"- opposition_risk_auto_classified_pass: {'PASS' if opposition_auto_pass else 'FAIL'}",
        f"- auto_ready_rate_drop_pass: {'PASS' if auto_ready_pass else 'FAIL'}",
    ]
    md_path.write_text("\n".join(md), encoding="utf-8")
    return {"json": str(json_path), "md": str(md_path), "decision": decision}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a daily canary report comparing candidate vs champion prediction bundles."
    )
    parser.add_argument("--candidate-predictions", required=True, help="Path to candidate predictions.csv")
    parser.add_argument("--champion-predictions", required=True, help="Path to champion predictions.csv")
    parser.add_argument(
        "--gate-config",
        default="reports/tmp_phase9/final_compare/CANARY_BASELINE_GATES.json",
        help="Path to canary gate JSON baseline.",
    )
    parser.add_argument(
        "--output-dir",
        default="reports/tmp_phase9/final_compare/canary_reports",
        help="Directory where daily report artifacts are written.",
    )
    parser.add_argument("--label", default="day1", help="Short report label, e.g. day1/day2/day3.")
    args = parser.parse_args()

    result = run_report(
        candidate_predictions=Path(args.candidate_predictions),
        champion_predictions=Path(args.champion_predictions),
        gate_config=Path(args.gate_config),
        output_dir=Path(args.output_dir),
        label=args.label,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
