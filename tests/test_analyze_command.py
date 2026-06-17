from __future__ import annotations

import json
from pathlib import Path


def test_analyze_command_writes_phase4_run_bundle(
    cli_runner,
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "analyze_smoke"

    result = cli_runner(
        "analyze",
        "--run-id",
        "smoke_phase4",
        "--output-dir",
        str(output_dir),
        "--input-artifact",
        "reports/phase2_gold_supervision.csv",
    )

    assert result.returncode == 0, result.stderr
    manifest_path = output_dir / "analysis_manifest.json"
    methodology_path = output_dir / "methodology_assignments.csv"
    theme_path = output_dir / "theme_assignments.csv"
    assert manifest_path.exists()
    assert methodology_path.exists()
    assert theme_path.exists()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["run_id"] == "smoke_phase4"
    assert manifest["methodology"]["artifacts"]["assignments"].endswith(
        "methodology_assignments.csv"
    )
    assert manifest["themes"]["artifacts"]["assignments"].endswith("theme_assignments.csv")


def test_analyze_command_writes_phase5_reporting_bundle(
    cli_runner,
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "analyze_reporting"

    result = cli_runner(
        "analyze",
        "--run-id",
        "smoke_phase5_reporting",
        "--output-dir",
        str(output_dir),
        "--input-artifact",
        "reports/phase2_gold_supervision.csv",
        "--enable-reporting",
    )

    assert result.returncode == 0, result.stderr
    client_results_path = output_dir / "client_results.csv"
    client_report_path = output_dir / "client_report.md"
    manifest_path = output_dir / "analysis_manifest.json"
    assert client_results_path.exists()
    assert client_report_path.exists()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["reporting"]["enabled"] is True
    assert manifest["reporting"]["artifacts"]["client_results"].endswith("client_results.csv")
