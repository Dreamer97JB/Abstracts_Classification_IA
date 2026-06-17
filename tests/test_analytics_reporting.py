from __future__ import annotations

from pathlib import Path

import pandas as pd

from abstract_classifier.analytics_reporting import build_analytics_report
from abstract_classifier.bibliometrics import build_bibliometric_outputs, load_bibliometric_config
from abstract_classifier.network_analysis import build_network_outputs, export_network_files


def _sample_bibliometric_outputs(project_root: Path):
    config = load_bibliometric_config(root=project_root)
    frame = pd.DataFrame(
        [
            {
                "record_id": "r1",
                "title": "Covid realism",
                "abstract": "Covid policy and realism",
                "authors": "Alpha, A.; Beta, B.",
                "references": "Latour, B. (2005). Reassembling the social.",
                "author_keywords": "covid; policy",
                "index_keywords": "epistemology",
                "themes": "covid | policy",
                "predicted_canonical_id": "tipo_1",
                "predicted_label_canonica": "Tipo 1",
            }
        ]
    )
    outputs = build_bibliometric_outputs(frame, config=config)
    return config, outputs


def test_analytics_reporting_writes_reports_without_networks(project_root: Path, tmp_path: Path) -> None:
    config, outputs = _sample_bibliometric_outputs(project_root)

    written = build_analytics_report(
        outputs,
        output_dir=tmp_path / "analytics",
        config=config,
        root=project_root,
    )

    assert written.markdown_path.exists()
    assert written.html_path.exists()
    assert written.interactive_index_path.exists()

    markdown = written.markdown_path.read_text(encoding="utf-8")
    html = written.html_path.read_text(encoding="utf-8")
    interactive = written.interactive_index_path.read_text(encoding="utf-8")

    assert "## 8. Networks" in markdown
    assert "Numeric descriptive profiles" in markdown
    assert "Network outputs are not available" in markdown
    assert "Scopus Interactive Analytics" in interactive
    assert "Descriptive profiles" in interactive
    assert "Heatmaps" in interactive
    assert "Temporal evolution" in interactive
    assert "Network outputs are not available" in interactive
    assert "<html" in html.lower()


def test_analytics_reporting_integrates_network_outputs(project_root: Path, tmp_path: Path) -> None:
    config, outputs = _sample_bibliometric_outputs(project_root)
    network_outputs = build_network_outputs(outputs, config=config)
    network_written = export_network_files(
        network_outputs,
        output_dir=tmp_path / "analytics" / "networks",
        config=config,
        root=project_root,
    )

    written = build_analytics_report(
        outputs,
        output_dir=tmp_path / "analytics",
        config=config,
        network_artifacts=network_outputs,
        network_run_artifacts=network_written,
        root=project_root,
    )

    interactive = written.interactive_index_path.read_text(encoding="utf-8")
    assert "Co-citation preview" in interactive
    assert "Theme coverage sources" in interactive
