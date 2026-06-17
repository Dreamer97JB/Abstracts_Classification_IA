from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from abstract_classifier.bibliometrics import build_bibliometric_outputs, load_bibliometric_config
from abstract_classifier.network_analysis import build_network_outputs, export_network_files


def _sample_outputs(project_root: Path):
    config = load_bibliometric_config(root=project_root)
    frame = pd.DataFrame(
        [
            {
                "record_id": "r1",
                "title": "Knowledge networks",
                "abstract": "Science and collaboration",
                "authors": "Smith, J.; Brown, P.",
                "references": "Latour, B. (2005). Reassembling the social.; Merton, R. (1973). Sociology of science.",
                "themes": "science | collaboration",
                "predicted_canonical_id": "tipo_1",
                "predicted_label_canonica": "Tipo 1",
            },
            {
                "record_id": "r2",
                "title": "Actor network",
                "abstract": "Networks and methods",
                "authors": "Smith, J.; Clark, T.",
                "references": "Latour, B. (2005). Reassembling the social.; Bloor, D. (1991). Knowledge and social imagery.",
                "themes": "networks",
                "predicted_canonical_id": "tipo_2",
                "predicted_label_canonica": "Tipo 2",
            },
            {
                "record_id": "r3",
                "title": "Critical realism",
                "abstract": "Causality and realism",
                "authors": "Stone, R.; Clark, T.",
                "references": "Merton, R. (1973). Sociology of science.; Bloor, D. (1991). Knowledge and social imagery.",
                "themes": "realism",
                "predicted_canonical_id": "tipo_1",
                "predicted_label_canonica": "Tipo 1",
            },
        ]
    )
    bibliometric_outputs = build_bibliometric_outputs(frame, config=config)
    network_outputs = build_network_outputs(bibliometric_outputs, config=config)
    return config, bibliometric_outputs, network_outputs


def test_network_analysis_builds_expected_edge_types(project_root: Path) -> None:
    _config, _bibliometric_outputs, network_outputs = _sample_outputs(project_root)

    assert set(network_outputs.edges["edge_type"]) >= {
        "ARTICLE_CITES_AUTHOR",
        "CO_CITED_AUTHOR",
        "CO_AUTHOR",
        "ARTICLE_BIBLIOGRAPHIC_COUPLING",
    }

    cocited = network_outputs.edges.loc[
        network_outputs.edges["edge_type"] == "CO_CITED_AUTHOR"
    ]
    assert not cocited.empty
    latour_merton = cocited.loc[
        cocited["source_records"].astype(str).str.contains("r1")
    ]
    assert not latour_merton.empty


def test_network_analysis_exports_graph_files(project_root: Path, tmp_path: Path) -> None:
    config, _bibliometric_outputs, network_outputs = _sample_outputs(project_root)

    written = export_network_files(
        network_outputs,
        output_dir=tmp_path / "networks",
        config=config,
        root=project_root,
    )

    assert written.nodes_path.exists()
    assert written.edges_path.exists()
    assert written.cocitation_graphml_path.exists()
    assert written.coauthor_graphml_path.exists()
    assert written.coupling_graphml_path.exists()
    assert written.cocitation_html_path.exists()
    assert written.coauthor_html_path.exists()
    assert written.coupling_html_path.exists()

    metadata = json.loads(written.metadata_path.read_text(encoding="utf-8"))
    assert metadata["cocitation_edges"] >= 1

