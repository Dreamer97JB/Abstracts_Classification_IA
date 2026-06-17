from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from ..bibliometrics import (
    build_bibliometric_outputs,
    load_saved_bibliometric_outputs,
    load_bibliometric_config,
    write_bibliometric_outputs,
)
from ..analytics_reporting import build_analytics_report
from ..network_analysis import build_network_outputs, export_network_files
from ..taxonomy import resolve_project_path

ROOT = Path(__file__).resolve().parents[3]
DESCRIPTION = "Build deterministic bibliometric analytics artifacts from a classified corpus CSV."


def handle_command(args: argparse.Namespace) -> int:
    config = load_bibliometric_config(args.config, root=ROOT)
    if args.reuse_output_dir:
        written_output_dir = resolve_project_path(args.reuse_output_dir, root=ROOT)
        artifacts = load_saved_bibliometric_outputs(written_output_dir, root=ROOT)
        written = None
        input_artifact = written_output_dir
        output_dir = written_output_dir
    else:
        input_artifact = resolve_project_path(args.input_artifact, root=ROOT)
        input_rows = pd.read_csv(input_artifact)
        artifacts = build_bibliometric_outputs(input_rows, config=config)
        written = write_bibliometric_outputs(
            artifacts,
            input_artifact=input_artifact,
            output_dir=args.output_dir,
            config=config,
            root=ROOT,
        )
        output_dir = written.output_dir
    network_written = None
    network_outputs = None
    if not args.skip_networks:
        network_outputs = build_network_outputs(artifacts, config=config)
        network_written = export_network_files(
            network_outputs,
            output_dir=Path(output_dir) / "networks",
            config=config,
            root=ROOT,
        )
    reporting_written = None
    if not args.skip_reporting:
        reporting_written = build_analytics_report(
            artifacts,
            output_dir=Path(output_dir),
            config=config,
            network_artifacts=network_outputs,
            network_run_artifacts=network_written,
            root=ROOT,
        )
    if written is not None:
        _extend_manifest(
            written.manifest_path,
            network_written=network_written,
            reporting_written=reporting_written,
            root=ROOT,
        )
        print(f"Output directory: {written.output_dir}")
        print(f"Manifest: {written.manifest_path}")
        print(f"Descriptive stats: {written.descriptive_stats_path}")
        print(f"Parsed references: {written.parsed_references_path}")
        print(f"Author frequency: {written.corpus_author_frequency_path}")
        print(f"Cited author frequency: {written.cited_author_frequency_path}")
        print(f"Author x label matrix: {written.author_label_matrix_path}")
        print(f"Author x theme matrix: {written.author_theme_matrix_path}")
        print(f"Theme x label matrix: {written.theme_label_matrix_path}")
        print(f"Keyword x label matrix: {written.keyword_label_matrix_path}")
    else:
        print(f"Reused output directory: {output_dir}")
    if network_written is not None:
        print(f"Network nodes: {network_written.nodes_path}")
        print(f"Network edges: {network_written.edges_path}")
    if reporting_written is not None:
        print(f"Markdown report: {reporting_written.markdown_path}")
        print(f"HTML report: {reporting_written.html_path}")
        print(f"Interactive index: {reporting_written.interactive_index_path}")
    return 0


def register(subparsers) -> None:
    parser = subparsers.add_parser(
        "bibliometrics",
        help="Build bibliometric analytics outputs.",
        description=DESCRIPTION,
    )
    parser.add_argument(
        "--config",
        default="configs/bibliometrics.toml",
        help="Path to the bibliometrics config TOML.",
    )
    parser.add_argument(
        "--input-artifact",
        default="reports/phase10/scopus_only_predict/predictions.csv",
        help="Classified CSV artifact to analyze.",
    )
    parser.add_argument(
        "--output-dir",
        help="Optional output directory. Defaults to the bibliometrics config output root.",
    )
    parser.add_argument(
        "--reuse-output-dir",
        help="Reuse an existing bibliometrics output directory and only rebuild downstream network/report artifacts.",
    )
    parser.add_argument(
        "--skip-networks",
        action="store_true",
        help="Skip task-2 network outputs.",
    )
    parser.add_argument(
        "--skip-reporting",
        action="store_true",
        help="Skip task-3 report and interactive outputs.",
    )
    parser.set_defaults(handler=handle_command)


def _extend_manifest(
    manifest_path: Path,
    *,
    network_written,
    reporting_written,
    root: Path,
) -> None:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if network_written is not None:
        payload["network_artifacts"] = {
            "nodes": _relative_path(network_written.nodes_path, root),
            "edges": _relative_path(network_written.edges_path, root),
            "co_citation_graphml": _relative_path(network_written.cocitation_graphml_path, root),
            "co_author_graphml": _relative_path(network_written.coauthor_graphml_path, root),
            "bibliographic_coupling_graphml": _relative_path(network_written.coupling_graphml_path, root),
        }
    if reporting_written is not None:
        payload["reporting_artifacts"] = {
            "markdown_report": _relative_path(reporting_written.markdown_path, root),
            "html_report": _relative_path(reporting_written.html_path, root),
            "interactive_index": _relative_path(reporting_written.interactive_index_path, root),
        }
    manifest_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _relative_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())
