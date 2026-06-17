# SDD 02: Network Analytics

## 1. Objective

Build deterministic network-analysis outputs on top of the analytics foundation.

This task converts bibliometric outputs into graph-ready structures, metrics, and exports for later reporting and interactive presentation.

## 2. Dependency

This task depends on:

- `01-analytics-foundation.md`

Hard rule:

- do not start this task before the parsed-reference and author-mention contracts exist

## 3. Scope

This task includes:

- graph construction
- node and edge export
- network metrics
- GraphML export
- lightweight HTML graph preview export

This task does not include:

- final written report composition
- dashboard layout
- interactive filtering UX outside graph preview pages

## 4. Architectural Boundary

New module required:

- `src/abstract_classifier/network_analysis.py`

Hard boundaries:

- graph computation must not live in `client_reporting.py`
- graph computation must not be embedded directly in CLI code
- report rendering code must not own centrality math

## 5. Required Public Functions

The module must expose:

```python
build_network_outputs(...)
build_article_cited_author_graph(...)
build_cocitation_graph(...)
build_coauthor_graph(...)
build_bibliographic_coupling_graph(...)
compute_network_metrics(...)
export_network_files(...)
```

## 6. Required Network Types

### 6.1 Article -> cited author

Meaning:

- article nodes linked to cited-author nodes

Required edge type:

- `ARTICLE_CITES_AUTHOR`

### 6.2 Co-citation network

Meaning:

- two cited authors are connected when they are cited in the same article

Required edge type:

- `CO_CITED_AUTHOR`

Weight definition:

- number of unique articles that cite both authors

### 6.3 Co-author network

Meaning:

- two corpus authors are connected when they appear together as article authors

Required edge type:

- `CO_AUTHOR`

### 6.4 Bibliographic coupling network

Meaning:

- two articles are connected when they share cited references, cited DOI values, or cited-author evidence according to implemented rule

Required edge type:

- `ARTICLE_BIBLIOGRAPHIC_COUPLING`

Hard rule:

- the implemented coupling rule must be explicit in code and summary metadata
- do not claim a stronger linkage definition than the actual deterministic evidence used

## 7. Node Contract

Required file:

- `networks/network_nodes.csv`

Required columns:

```text
node_id,node_type,label,display_name,count,dominant_label_id,dominant_label_name,degree,weighted_degree,betweenness,pagerank,community_id
```

Allowed `node_type` values:

- `ARTICLE`
- `CORPUS_AUTHOR`
- `CITED_AUTHOR`
- `KEYWORD`
- `THEME`
- `LABEL`

For the first implementation, the minimum required node types are:

- `ARTICLE`
- `CORPUS_AUTHOR`
- `CITED_AUTHOR`

## 8. Edge Contract

Required file:

- `networks/network_edges.csv`

Required columns:

```text
source,target,edge_type,weight,evidence_count,source_records
```

Rules:

- `weight` must be numeric
- `evidence_count` must be deterministic
- `source_records` must preserve traceability back to article ids where feasible

## 9. Required Metrics

The module must compute at minimum:

- `degree`
- `weighted_degree`
- `betweenness`
- `pagerank`
- `community_id`

Hard rule:

- if community detection is disabled or unavailable, output must remain valid and use a safe null/empty community representation

## 10. Config Contract

The network task may read from:

- `configs/bibliometrics.toml`

or a dedicated future network section.

Minimum config controls:

- `min_edge_weight`
- `max_nodes_html`
- `compute_betweenness`
- `community_detection`

## 11. Export Contract

Required exports:

- `reports/analytics/scopus/networks/network_nodes.csv`
- `reports/analytics/scopus/networks/network_edges.csv`
- `reports/analytics/scopus/networks/co_citation_authors.graphml`
- `reports/analytics/scopus/networks/co_author.graphml`
- `reports/analytics/scopus/networks/bibliographic_coupling.graphml`

Preferred additional exports:

- `reports/analytics/scopus/networks/co_citation_authors.html`
- `reports/analytics/scopus/networks/co_author.html`
- `reports/analytics/scopus/networks/bibliographic_coupling.html`

## 12. Performance and Safety Rules

### 12.1 Graph size rule

HTML preview graphs must be bounded.

If the graph exceeds configured display limits:

- filter by edge weight
- cap nodes
- record the applied filtering in metadata

### 12.2 Determinism rule

Metric outputs must be reproducible from the same input and config.

### 12.3 Traceability rule

All exported nodes and edges must be derivable from persisted bibliometric artifacts.

## 13. Testing Requirements

Required tests:

- `tests/test_network_analysis.py`

Test coverage must include:

- co-citation pair creation
- co-author pair creation
- coupling weight calculation
- node/edge export schema
- safe handling of sparse graphs

## 14. Non-Goals

This task must not:

- write the final client narrative report
- implement a dashboard
- add an API
- require manual Gephi steps for core correctness

## 15. Acceptance Criteria

This task is complete only when:

1. The required graph types are generated from analytics-foundation outputs.
2. Node and edge exports follow the required schemas.
3. GraphML exports open in external tooling such as Gephi.
4. Graph metrics are computed and persisted deterministically.
5. HTML previews remain bounded and do not attempt to render unmanageable graphs.
