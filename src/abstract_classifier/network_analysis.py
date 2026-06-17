from __future__ import annotations

import html
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

import networkx as nx
import pandas as pd
import plotly.graph_objects as go

from .bibliometrics import BibliometricArtifacts, BibliometricConfig
from .taxonomy import ROOT


@dataclass(frozen=True)
class NetworkArtifacts:
    nodes: pd.DataFrame
    edges: pd.DataFrame
    article_cited_author_graph: nx.Graph
    cocitation_graph: nx.Graph
    coauthor_graph: nx.Graph
    bibliographic_coupling_graph: nx.Graph
    metadata: dict[str, object]


@dataclass(frozen=True)
class NetworkRunArtifacts:
    output_dir: Path
    nodes_path: Path
    edges_path: Path
    cocitation_graphml_path: Path
    coauthor_graphml_path: Path
    coupling_graphml_path: Path
    cocitation_html_path: Path
    coauthor_html_path: Path
    coupling_html_path: Path
    metadata_path: Path


def build_network_outputs(
    bibliometric_artifacts: BibliometricArtifacts,
    *,
    config: BibliometricConfig,
) -> NetworkArtifacts:
    article_graph, article_edges = build_article_cited_author_graph(bibliometric_artifacts, config=config)
    cocitation_graph, cocitation_edges = build_cocitation_graph(bibliometric_artifacts, config=config)
    coauthor_graph, coauthor_edges = build_coauthor_graph(bibliometric_artifacts)
    coupling_graph, coupling_edges = build_bibliographic_coupling_graph(
        bibliometric_artifacts,
        config=config,
    )

    edge_frames = [
        frame
        for frame in (article_edges, cocitation_edges, coauthor_edges, coupling_edges)
        if not frame.empty
    ]
    all_edges = (
        pd.concat(edge_frames, ignore_index=True)
        if edge_frames
        else pd.DataFrame(columns=["source", "target", "edge_type", "weight", "evidence_count", "source_records"])
    )
    nodes = compute_network_metrics(
        all_edges,
        bibliometric_artifacts=bibliometric_artifacts,
        config=config,
    )
    metadata = {
        "article_cited_author_edges": int(len(article_edges)),
        "cocitation_edges": int(len(cocitation_edges)),
        "coauthor_edges": int(len(coauthor_edges)),
        "bibliographic_coupling_edges": int(len(coupling_edges)),
        "min_edge_weight": config.networks.min_edge_weight,
        "min_cited_author_article_coverage": config.networks.min_cited_author_article_coverage,
        "max_cited_authors_per_article": config.networks.max_cited_authors_per_article,
        "max_signature_record_frequency": config.networks.max_signature_record_frequency,
        "min_bibliographic_coupling_weight": config.networks.min_bibliographic_coupling_weight,
    }
    return NetworkArtifacts(
        nodes=nodes,
        edges=all_edges,
        article_cited_author_graph=article_graph,
        cocitation_graph=cocitation_graph,
        coauthor_graph=coauthor_graph,
        bibliographic_coupling_graph=coupling_graph,
        metadata=metadata,
    )


def build_article_cited_author_graph(
    bibliometric_artifacts: BibliometricArtifacts,
    *,
    config: BibliometricConfig,
) -> tuple[nx.Graph, pd.DataFrame]:
    graph = nx.Graph()
    graph.graph["edge_type"] = "ARTICLE_CITES_AUTHOR"
    edges: list[dict[str, object]] = []
    if bibliometric_artifacts.parsed_references.empty:
        return graph, pd.DataFrame(columns=["source", "target", "edge_type", "weight", "evidence_count", "source_records"])

    labels = _record_labels(bibliometric_artifacts.enriched_rows)
    allowed_authors, author_rank = _allowed_cited_authors(bibliometric_artifacts, config=config)
    for record_id, frame in bibliometric_artifacts.parsed_references.groupby("record_id", dropna=False):
        author_counts: Counter[tuple[str, str]] = Counter()
        for authors_raw in frame["authors_normalized"].astype(str).tolist():
            for author_display in _split_author_values(authors_raw):
                node_id = _author_node_id(author_display)
                if allowed_authors and node_id not in allowed_authors:
                    continue
                author_counts[(node_id, author_display)] += 1
        if author_counts and config.networks.max_cited_authors_per_article > 0:
            ranked_items = sorted(
                author_counts.items(),
                key=lambda item: (
                    item[1],
                    -author_rank.get(item[0][0], 0),
                    item[0][1],
                ),
                reverse=True,
            )[: config.networks.max_cited_authors_per_article]
            author_counts = Counter(dict(ranked_items))

        label_id, label_name = labels.get(str(record_id), ("", ""))
        graph.add_node(
            _article_node_id(str(record_id)),
            node_type="ARTICLE",
            display_name=str(record_id),
            label_id=label_id,
            label_name=label_name,
            count=1,
        )
        for (author_node_id, author_display), count in author_counts.items():
            graph.add_node(
                author_node_id,
                node_type="CITED_AUTHOR",
                display_name=author_display,
                count=count,
            )
            graph.add_edge(
                _article_node_id(str(record_id)),
                author_node_id,
                weight=int(count),
                source_records=str(record_id),
                evidence_count=int(count),
                edge_type="ARTICLE_CITES_AUTHOR",
            )
            edges.append(
                {
                    "source": _article_node_id(str(record_id)),
                    "target": author_node_id,
                    "edge_type": "ARTICLE_CITES_AUTHOR",
                    "weight": int(count),
                    "evidence_count": int(count),
                    "source_records": str(record_id),
                }
            )

    return graph, pd.DataFrame.from_records(
        edges,
        columns=["source", "target", "edge_type", "weight", "evidence_count", "source_records"],
    )


def build_cocitation_graph(
    bibliometric_artifacts: BibliometricArtifacts,
    *,
    config: BibliometricConfig,
) -> tuple[nx.Graph, pd.DataFrame]:
    graph = nx.Graph()
    graph.graph["edge_type"] = "CO_CITED_AUTHOR"
    pair_records: dict[tuple[str, str], set[str]] = defaultdict(set)
    display_lookup: dict[str, str] = {}
    if bibliometric_artifacts.parsed_references.empty:
        return graph, pd.DataFrame(columns=["source", "target", "edge_type", "weight", "evidence_count", "source_records"])

    allowed_authors, author_rank = _allowed_cited_authors(bibliometric_artifacts, config=config)
    for record_id, frame in bibliometric_artifacts.parsed_references.groupby("record_id", dropna=False):
        authors = {
            _author_node_id(author_display): author_display
            for authors_raw in frame["authors_normalized"].astype(str).tolist()
            for author_display in _split_author_values(authors_raw)
            if not allowed_authors or _author_node_id(author_display) in allowed_authors
        }
        if authors and config.networks.max_cited_authors_per_article > 0:
            ranked = sorted(
                authors.items(),
                key=lambda item: (-author_rank.get(item[0], 0), item[1]),
            )[: config.networks.max_cited_authors_per_article]
            authors = dict(ranked)
        for node_id, display_name in authors.items():
            display_lookup[node_id] = display_name
        for left, right in combinations(sorted(authors), 2):
            pair_records[(left, right)].add(str(record_id))

    edges = _pair_records_to_edges(
        pair_records,
        edge_type="CO_CITED_AUTHOR",
        min_edge_weight=config.networks.min_edge_weight,
    )
    for row in edges.to_dict(orient="records"):
        source = str(row["source"])
        target = str(row["target"])
        graph.add_node(source, node_type="CITED_AUTHOR", display_name=display_lookup.get(source, source))
        graph.add_node(target, node_type="CITED_AUTHOR", display_name=display_lookup.get(target, target))
        graph.add_edge(source, target, **row)
    return graph, edges


def build_coauthor_graph(
    bibliometric_artifacts: BibliometricArtifacts,
) -> tuple[nx.Graph, pd.DataFrame]:
    graph = nx.Graph()
    graph.graph["edge_type"] = "CO_AUTHOR"
    pair_records: dict[tuple[str, str], set[str]] = defaultdict(set)
    display_lookup: dict[str, str] = {}
    for row in bibliometric_artifacts.enriched_rows.to_dict(orient="records"):
        authors = {
            _corpus_author_node_id(author_display): author_display
            for author_display in _split_author_values(str(row.get("corpus_authors_normalized", "")))
        }
        for node_id, display_name in authors.items():
            display_lookup[node_id] = display_name
        for left, right in combinations(sorted(authors), 2):
            pair_records[(left, right)].add(str(row["record_id"]))

    edges = _pair_records_to_edges(pair_records, edge_type="CO_AUTHOR", min_edge_weight=1)
    for row in edges.to_dict(orient="records"):
        source = str(row["source"])
        target = str(row["target"])
        graph.add_node(source, node_type="CORPUS_AUTHOR", display_name=display_lookup.get(source, source))
        graph.add_node(target, node_type="CORPUS_AUTHOR", display_name=display_lookup.get(target, target))
        graph.add_edge(source, target, **row)
    return graph, edges


def build_bibliographic_coupling_graph(
    bibliometric_artifacts: BibliometricArtifacts,
    *,
    config: BibliometricConfig,
) -> tuple[nx.Graph, pd.DataFrame]:
    graph = nx.Graph()
    graph.graph["edge_type"] = "ARTICLE_BIBLIOGRAPHIC_COUPLING"
    records_by_signature: dict[str, set[str]] = defaultdict(set)
    for row in bibliometric_artifacts.parsed_references.to_dict(orient="records"):
        record_id = str(row["record_id"])
        evidence = _reference_signature(row)
        if evidence:
            records_by_signature[evidence].add(record_id)
    pair_records: dict[tuple[str, str], int] = defaultdict(int)
    pair_signatures: dict[tuple[str, str], list[str]] = defaultdict(list)
    max_signature_record_frequency = config.networks.max_signature_record_frequency
    for signature, record_ids in records_by_signature.items():
        if max_signature_record_frequency > 0 and len(record_ids) > max_signature_record_frequency:
            continue
        ordered_records = sorted(record_ids)
        for left_record, right_record in combinations(ordered_records, 2):
            pair_key = (_article_node_id(left_record), _article_node_id(right_record))
            pair_records[pair_key] += 1
            if len(pair_signatures[pair_key]) < 12:
                pair_signatures[pair_key].append(signature)

    edges: list[dict[str, object]] = []
    for (left, right), shared_count in sorted(pair_records.items()):
        if shared_count < config.networks.min_bibliographic_coupling_weight:
            continue
        shared = pair_signatures[(left, right)]
        edges.append(
            {
                "source": left,
                "target": right,
                "edge_type": "ARTICLE_BIBLIOGRAPHIC_COUPLING",
                "weight": shared_count,
                "evidence_count": shared_count,
                "source_records": " | ".join(shared),
            }
        )
        graph.add_node(left, node_type="ARTICLE", display_name=left.removeprefix("article:"))
        graph.add_node(right, node_type="ARTICLE", display_name=right.removeprefix("article:"))
        graph.add_edge(
            left,
            right,
            weight=shared_count,
            evidence_count=shared_count,
            source_records=" | ".join(shared),
            edge_type="ARTICLE_BIBLIOGRAPHIC_COUPLING",
        )
    return graph, pd.DataFrame.from_records(
        edges,
        columns=["source", "target", "edge_type", "weight", "evidence_count", "source_records"],
    )


def compute_network_metrics(
    edges: pd.DataFrame,
    *,
    bibliometric_artifacts: BibliometricArtifacts,
    config: BibliometricConfig,
) -> pd.DataFrame:
    graph = nx.Graph()
    for row in edges.to_dict(orient="records"):
        if int(row["weight"]) < config.networks.min_edge_weight:
            continue
        graph.add_edge(str(row["source"]), str(row["target"]), weight=float(row["weight"]))

    degree = dict(graph.degree()) if graph.number_of_nodes() else {}
    weighted_degree = dict(graph.degree(weight="weight")) if graph.number_of_nodes() else {}
    betweenness = (
        nx.betweenness_centrality(graph, weight="weight", normalized=True)
        if graph.number_of_nodes() and config.networks.compute_betweenness
        else {}
    )
    pagerank = nx.pagerank(graph, weight="weight") if graph.number_of_nodes() else {}
    community_map = _community_map(graph, enabled=config.networks.community_detection)
    metadata = _node_metadata(bibliometric_artifacts)

    rows: list[dict[str, object]] = []
    for node_id in sorted(set(graph.nodes()) | set(metadata)):
        info = metadata.get(node_id, {})
        rows.append(
            {
                "node_id": node_id,
                "node_type": info.get("node_type", ""),
                "label": info.get("label", info.get("display_name", node_id)),
                "display_name": info.get("display_name", node_id),
                "count": int(info.get("count", 0)),
                "dominant_label_id": info.get("dominant_label_id", ""),
                "dominant_label_name": info.get("dominant_label_name", ""),
                "degree": int(degree.get(node_id, 0)),
                "weighted_degree": float(weighted_degree.get(node_id, 0.0)),
                "betweenness": float(betweenness.get(node_id, 0.0)),
                "pagerank": float(pagerank.get(node_id, 0.0)),
                "community_id": community_map.get(node_id, ""),
            }
        )
    return pd.DataFrame.from_records(
        rows,
        columns=[
            "node_id",
            "node_type",
            "label",
            "display_name",
            "count",
            "dominant_label_id",
            "dominant_label_name",
            "degree",
            "weighted_degree",
            "betweenness",
            "pagerank",
            "community_id",
        ],
    )


def export_network_files(
    artifacts: NetworkArtifacts,
    *,
    output_dir: str | Path,
    config: BibliometricConfig,
    root: Path | None = None,
) -> NetworkRunArtifacts:
    project_root = root or ROOT
    resolved_output_dir = Path(output_dir)
    if not resolved_output_dir.is_absolute():
        resolved_output_dir = (project_root / resolved_output_dir).resolve()
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    nodes_path = resolved_output_dir / "network_nodes.csv"
    edges_path = resolved_output_dir / "network_edges.csv"
    cocitation_graphml_path = resolved_output_dir / "co_citation_authors.graphml"
    coauthor_graphml_path = resolved_output_dir / "co_author.graphml"
    coupling_graphml_path = resolved_output_dir / "bibliographic_coupling.graphml"
    cocitation_html_path = resolved_output_dir / "co_citation_authors.html"
    coauthor_html_path = resolved_output_dir / "co_author.html"
    coupling_html_path = resolved_output_dir / "bibliographic_coupling.html"
    metadata_path = resolved_output_dir / "network_summary.json"

    artifacts.nodes.to_csv(nodes_path, index=False, encoding="utf-8")
    artifacts.edges.to_csv(edges_path, index=False, encoding="utf-8")
    nx.write_graphml(artifacts.cocitation_graph, cocitation_graphml_path)
    nx.write_graphml(artifacts.coauthor_graph, coauthor_graphml_path)
    nx.write_graphml(artifacts.bibliographic_coupling_graph, coupling_graphml_path)
    cocitation_html_path.write_text(
        _graph_preview_html(artifacts.cocitation_graph, title="Co-citation Authors", config=config),
        encoding="utf-8",
    )
    coauthor_html_path.write_text(
        _graph_preview_html(artifacts.coauthor_graph, title="Co-author Network", config=config),
        encoding="utf-8",
    )
    coupling_html_path.write_text(
        _graph_preview_html(artifacts.bibliographic_coupling_graph, title="Bibliographic Coupling", config=config),
        encoding="utf-8",
    )
    metadata_path.write_text(json.dumps(artifacts.metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    return NetworkRunArtifacts(
        output_dir=resolved_output_dir,
        nodes_path=nodes_path,
        edges_path=edges_path,
        cocitation_graphml_path=cocitation_graphml_path,
        coauthor_graphml_path=coauthor_graphml_path,
        coupling_graphml_path=coupling_graphml_path,
        cocitation_html_path=cocitation_html_path,
        coauthor_html_path=coauthor_html_path,
        coupling_html_path=coupling_html_path,
        metadata_path=metadata_path,
    )


def _pair_records_to_edges(
    pair_records: dict[tuple[str, str], set[str]],
    *,
    edge_type: str,
    min_edge_weight: int,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for (source, target), record_ids in sorted(pair_records.items()):
        weight = len(record_ids)
        if weight < min_edge_weight:
            continue
        rows.append(
            {
                "source": source,
                "target": target,
                "edge_type": edge_type,
                "weight": weight,
                "evidence_count": weight,
                "source_records": " | ".join(sorted(record_ids)),
            }
        )
    return pd.DataFrame.from_records(
        rows,
        columns=["source", "target", "edge_type", "weight", "evidence_count", "source_records"],
    )


def _allowed_cited_authors(
    bibliometric_artifacts: BibliometricArtifacts,
    *,
    config: BibliometricConfig,
) -> tuple[set[str], dict[str, int]]:
    frame = bibliometric_artifacts.cited_author_frequency
    if frame.empty:
        return set(), {}
    filtered = frame.loc[
        frame["article_citation_coverage"].fillna(0).astype(int)
        >= config.networks.min_cited_author_article_coverage
    ].copy()
    allowed = {_author_node_id(str(row["author_display"])) for row in filtered.to_dict(orient="records")}
    rank = {
        _author_node_id(str(row["author_display"])): int(row["article_citation_coverage"])
        for row in filtered.to_dict(orient="records")
    }
    return allowed, rank


def _community_map(graph: nx.Graph, *, enabled: bool) -> dict[str, str]:
    if not enabled or graph.number_of_nodes() == 0 or graph.number_of_edges() == 0:
        return {str(node): "" for node in graph.nodes()}
    communities = nx.algorithms.community.greedy_modularity_communities(graph, weight="weight")
    mapping: dict[str, str] = {}
    for index, community in enumerate(communities, start=1):
        for node in community:
            mapping[str(node)] = str(index)
    return mapping


def _node_metadata(bibliometric_artifacts: BibliometricArtifacts) -> dict[str, dict[str, object]]:
    metadata: dict[str, dict[str, object]] = {}
    for row in bibliometric_artifacts.enriched_rows.to_dict(orient="records"):
        record_id = str(row["record_id"])
        node_id = _article_node_id(record_id)
        metadata[node_id] = {
            "node_type": "ARTICLE",
            "display_name": record_id,
            "label": str(row.get("title", "") or record_id),
            "count": 1,
            "dominant_label_id": str(row.get("label_id", "") or ""),
            "dominant_label_name": str(row.get("label_name", "") or ""),
        }

    for frame, node_type, prefix in (
        (bibliometric_artifacts.corpus_author_frequency, "CORPUS_AUTHOR", _corpus_author_node_id),
        (bibliometric_artifacts.cited_author_frequency, "CITED_AUTHOR", _author_node_id),
    ):
        if frame.empty:
            continue
        for row in frame.to_dict(orient="records"):
            node_id = prefix(str(row["author_display"]))
            metadata[node_id] = {
                "node_type": node_type,
                "display_name": str(row["author_display"]),
                "label": str(row["author_display"]),
                "count": int(
                    row.get("article_count")
                    or row.get("article_citation_coverage")
                    or row.get("cited_author_count")
                    or row.get("corpus_author_count")
                    or 0
                ),
                "dominant_label_id": "",
                "dominant_label_name": "",
            }

    _attach_dominant_labels(
        metadata,
        bibliometric_artifacts.author_label_matrix,
        key_column="cited_author_key",
        id_prefix="cited_author:",
    )
    _attach_dominant_labels_from_articles(metadata, bibliometric_artifacts.enriched_rows)
    return metadata


def _attach_dominant_labels(
    metadata: dict[str, dict[str, object]],
    frame: pd.DataFrame,
    *,
    key_column: str,
    id_prefix: str,
) -> None:
    if frame.empty:
        return
    ordered = frame.sort_values(
        by=["article_count", "mention_count", "label_name"],
        ascending=[False, False, True],
    )
    for author_key, author_rows in ordered.groupby(key_column, dropna=False):
        first = author_rows.iloc[0]
        node_id = f"{id_prefix}{author_key}"
        if node_id in metadata:
            metadata[node_id]["dominant_label_id"] = str(first["label_id"])
            metadata[node_id]["dominant_label_name"] = str(first["label_name"])


def _attach_dominant_labels_from_articles(
    metadata: dict[str, dict[str, object]],
    enriched_rows: pd.DataFrame,
) -> None:
    author_labels: dict[str, Counter[tuple[str, str]]] = defaultdict(Counter)
    for row in enriched_rows.to_dict(orient="records"):
        label_pair = (str(row.get("label_id", "") or ""), str(row.get("label_name", "") or ""))
        for author_display in _split_author_values(str(row.get("corpus_authors_normalized", ""))):
            author_labels[_corpus_author_node_id(author_display)][label_pair] += 1
    for node_id, counts in author_labels.items():
        if not counts or node_id not in metadata:
            continue
        (label_id, label_name), _count = counts.most_common(1)[0]
        metadata[node_id]["dominant_label_id"] = label_id
        metadata[node_id]["dominant_label_name"] = label_name


def _graph_preview_html(graph: nx.Graph, *, title: str, config: BibliometricConfig) -> str:
    if graph.number_of_nodes() == 0:
        return f"<html><body><h1>{html.escape(title)}</h1><p>No network data available.</p></body></html>"
    preview = _bounded_graph(graph, max_nodes=config.networks.max_nodes_html)
    layout = nx.spring_layout(
        preview,
        seed=42,
        weight="weight",
        k=max(0.35, 2.4 / max(preview.number_of_nodes() ** 0.5, 1.0)),
        iterations=200,
    )
    weighted_degree = dict(preview.degree(weight="weight"))
    ranked_nodes = sorted(weighted_degree.items(), key=lambda item: item[1], reverse=True)
    labeled_nodes = {node for node, _score in ranked_nodes[: min(18, len(ranked_nodes))]}
    node_palette = {
        "ARTICLE": "#d97706",
        "CORPUS_AUTHOR": "#1d4ed8",
        "CITED_AUTHOR": "#0b6e4f",
    }
    edge_x: list[float] = []
    edge_y: list[float] = []
    for left, right in preview.edges():
        x0, y0 = layout[left]
        x1, y1 = layout[right]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])
    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        line=dict(width=1, color="#9aa0a6"),
        hoverinfo="none",
        mode="lines",
    )
    node_x: list[float] = []
    node_y: list[float] = []
    node_text: list[str] = []
    hover_text: list[str] = []
    node_size: list[float] = []
    node_color: list[str] = []
    for node in preview.nodes():
        x, y = layout[node]
        node_x.append(x)
        node_y.append(y)
        node_name = str(preview.nodes[node].get("display_name", node))
        node_type = str(preview.nodes[node].get("node_type", ""))
        degree = float(weighted_degree.get(node, 0.0))
        node_text.append(node_name if node in labeled_nodes else "")
        hover_text.append(f"{html.escape(node_name)}<br>Type: {html.escape(node_type or 'unknown')}<br>Weighted degree: {degree:.1f}")
        node_size.append(10 + min(30.0, (degree ** 0.5) * 3.4))
        node_color.append(node_palette.get(node_type, "#35505a"))
    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        text=node_text,
        textposition="top center",
        hovertext=hover_text,
        hoverinfo="text",
        marker=dict(size=node_size, color=node_color, line=dict(width=1, color="#073b4c"), opacity=0.82),
        textfont=dict(size=11, color="#102a43"),
    )
    figure = go.Figure(
        data=[edge_trace, node_trace],
        layout=go.Layout(
            title=title,
            showlegend=False,
            margin=dict(l=20, r=20, t=50, b=20),
            xaxis=dict(showgrid=False, zeroline=False, visible=False),
            yaxis=dict(showgrid=False, zeroline=False, visible=False),
        ),
    )
    summary = f"<p>Nodes shown: {preview.number_of_nodes()} of {graph.number_of_nodes()} | Edges shown: {preview.number_of_edges()} of {graph.number_of_edges()}</p>"
    return (
        "<html><body>"
        f"<h1>{html.escape(title)}</h1>"
        f"{summary}"
        f"{figure.to_html(full_html=False, include_plotlyjs=True)}"
        "</body></html>"
    )


def _bounded_graph(graph: nx.Graph, *, max_nodes: int) -> nx.Graph:
    if graph.number_of_nodes() <= max_nodes:
        return graph.copy()
    ranked_nodes = sorted(graph.degree(weight="weight"), key=lambda item: item[1], reverse=True)
    keep = {node for node, _score in ranked_nodes[:max_nodes]}
    return graph.subgraph(keep).copy()


def _record_labels(enriched_rows: pd.DataFrame) -> dict[str, tuple[str, str]]:
    return {
        str(row["record_id"]): (str(row.get("label_id", "") or ""), str(row.get("label_name", "") or ""))
        for row in enriched_rows.to_dict(orient="records")
    }


def _reference_signature(row: dict[str, object]) -> str:
    doi = str(row.get("doi", "") or "").strip().lower()
    if doi:
        return f"doi:{doi}"
    first_author = str(row.get("first_author", "") or "").strip().lower()
    year = str(row.get("year", "") or "").strip()
    title_fragment = str(row.get("title_fragment", "") or "").strip().lower()
    raw = str(row.get("reference_raw", "") or "").strip().lower()
    if first_author or year or title_fragment:
        return f"ref:{first_author}|{year}|{title_fragment}"
    return f"raw:{raw}" if raw else ""


def _split_author_values(raw_value: str) -> list[str]:
    text = raw_value.strip()
    if not text:
        return []
    if "|" in text:
        parts = [part.strip() for part in text.split("|")]
    elif ";" in text:
        parts = [part.strip() for part in text.split(";")]
    else:
        parts = [text]
    return [part for part in parts if part]


def _article_node_id(record_id: str) -> str:
    return f"article:{record_id}"


def _author_node_id(author_display: str) -> str:
    return f"cited_author:{_author_key(author_display)}"


def _corpus_author_node_id(author_display: str) -> str:
    return f"corpus_author:{_author_key(author_display)}"


def _author_key(author_display: str) -> str:
    text = author_display.lower()
    text = "".join(char for char in text if char.isalnum() or char in {" ", ","})
    text = " ".join(text.replace(",", " ").split())
    return text
