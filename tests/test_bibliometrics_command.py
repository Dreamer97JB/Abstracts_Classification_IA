from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def test_bibliometrics_command_writes_task1_outputs(cli_runner, tmp_path: Path) -> None:
    input_path = tmp_path / "classified.csv"
    output_dir = tmp_path / "analytics"
    pd.DataFrame(
        [
            {
                "record_id": "r1",
                "title": "Knowledge networks",
                "abstract": "Science and networks",
                "authors": "Smith, J.; Brown, P.",
                "references": "Latour, B. (2005). Reassembling the social.; Merton, R. (1973). Sociology of science.",
                "author_keywords": "science; networks",
                "index_keywords": "bibliometrics",
                "themes": "science | networks",
                "predicted_canonical_id": "tipo_1",
                "predicted_label_canonica": "Tipo 1",
            }
        ]
    ).to_csv(input_path, index=False, encoding="utf-8")

    result = cli_runner(
        "bibliometrics",
        "--input-artifact",
        str(input_path),
        "--output-dir",
        str(output_dir),
    )

    assert result.returncode == 0, result.stderr
    assert (output_dir / "descriptive_stats.json").exists()
    assert (output_dir / "bibliometric_manifest.json").exists()
    assert (output_dir / "tables" / "parsed_references.csv").exists()
    assert (output_dir / "tables" / "author_frequency.csv").exists()
    assert (output_dir / "tables" / "cited_author_frequency.csv").exists()
    assert (output_dir / "tables" / "author_label_matrix.csv").exists()
    assert (output_dir / "tables" / "author_theme_matrix.csv").exists()
    assert (output_dir / "tables" / "theme_label_matrix.csv").exists()
    assert (output_dir / "tables" / "keyword_label_matrix.csv").exists()
    assert (output_dir / "networks" / "network_nodes.csv").exists()
    assert (output_dir / "networks" / "network_edges.csv").exists()
    assert (output_dir / "networks" / "co_citation_authors.graphml").exists()
    assert (output_dir / "scopus_analytics_report.md").exists()
    assert (output_dir / "scopus_analytics_report.html").exists()
    assert (output_dir / "interactive" / "index.html").exists()

    payload = json.loads((output_dir / "descriptive_stats.json").read_text(encoding="utf-8"))
    assert payload["total_articles"] == 1
    assert payload["articles_with_references"] == 1
