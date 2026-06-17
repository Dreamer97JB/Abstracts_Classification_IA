from __future__ import annotations

from pathlib import Path

import pandas as pd

from abstract_classifier.analytics_reporting import build_interactive_bundle
from abstract_classifier.bibliometrics import build_bibliometric_outputs, load_bibliometric_config


def test_interactive_bundle_writes_data_exports(project_root: Path, tmp_path: Path) -> None:
    config = load_bibliometric_config(root=project_root)
    frame = pd.DataFrame(
        [
            {
                "record_id": "r1",
                "title": "Knowledge networks",
                "abstract": "Science and networks",
                "authors": "Smith, J.; Brown, P.",
                "references": "Latour, B. (2005). Reassembling the social.",
                "author_keywords": "science; networks",
                "themes": "science | networks",
                "predicted_canonical_id": "tipo_1",
                "predicted_label_canonica": "Tipo 1",
            }
        ]
    )
    outputs = build_bibliometric_outputs(frame, config=config)

    index_path = build_interactive_bundle(
        outputs,
        output_dir=tmp_path / "interactive",
        config=config,
        root=project_root,
    )

    assert index_path.exists()
    assert (tmp_path / "interactive" / "data" / "descriptive_stats.json").exists()
    assert (tmp_path / "interactive" / "data" / "author_frequency.csv").exists()
    html = index_path.read_text(encoding="utf-8")
    assert "Scopus Interactive Analytics" in html
    assert "Descriptive profiles" in html
    assert "Corpus distributions" in html
    assert "Heatmaps" in html
    assert "Theme timeline" in html
