from __future__ import annotations

import csv
import html
import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .bibliometrics import BibliometricArtifacts, BibliometricConfig
from .network_analysis import NetworkArtifacts, NetworkRunArtifacts
from .taxonomy import ROOT


@dataclass(frozen=True)
class AnalyticsReportArtifacts:
    markdown_path: Path
    html_path: Path
    interactive_dir: Path
    interactive_index_path: Path
    manifest_path: Path


def build_analytics_report(
    bibliometric_artifacts: BibliometricArtifacts,
    *,
    output_dir: str | Path,
    config: BibliometricConfig,
    network_artifacts: NetworkArtifacts | None = None,
    network_run_artifacts: NetworkRunArtifacts | None = None,
    root: Path | None = None,
) -> AnalyticsReportArtifacts:
    project_root = root or ROOT
    resolved_output_dir = Path(output_dir)
    if not resolved_output_dir.is_absolute():
        resolved_output_dir = (project_root / resolved_output_dir).resolve()
    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    markdown_path = resolved_output_dir / "scopus_analytics_report.md"
    html_path = resolved_output_dir / "scopus_analytics_report.html"
    interactive_dir = resolved_output_dir / "interactive"
    interactive_index_path = interactive_dir / "index.html"
    manifest_path = resolved_output_dir / "analytics_reporting_manifest.json"

    report_payload = _build_report_payload(
        bibliometric_artifacts,
        config=config,
        network_artifacts=network_artifacts,
        network_run_artifacts=network_run_artifacts,
    )
    markdown_path.write_text(
        render_markdown_report(report_payload, config=config),
        encoding="utf-8",
    )
    html_path.write_text(
        render_html_report(report_payload, config=config),
        encoding="utf-8",
    )
    build_interactive_bundle(
        bibliometric_artifacts,
        output_dir=interactive_dir,
        config=config,
        network_artifacts=network_artifacts,
        network_run_artifacts=network_run_artifacts,
        root=project_root,
    )
    manifest_path.write_text(
        json.dumps(
            {
                "markdown_report": _relative_path(markdown_path, project_root),
                "html_report": _relative_path(html_path, project_root),
                "interactive_index": _relative_path(interactive_index_path, project_root),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return AnalyticsReportArtifacts(
        markdown_path=markdown_path,
        html_path=html_path,
        interactive_dir=interactive_dir,
        interactive_index_path=interactive_index_path,
        manifest_path=manifest_path,
    )


def render_markdown_report(
    payload: dict[str, object],
    *,
    config: BibliometricConfig,
) -> str:
    lines: list[str] = [
        "# Informe de análisis bibliométrico y temático - Corpus Scopus",
        "",
        "## 1. Executive summary",
    ]
    summary = payload["summary"]
    lines.extend(
        [
            f"- Total articles analyzed: `{summary['total_articles']}`",
            f"- Articles with references: `{summary['articles_with_references']}`",
            f"- Reference parse success rate: `{summary['reference_parse_success_rate']:.2%}`",
            f"- Dominant classification: `{summary['dominant_label']}`",
            f"- Dominant theme: `{summary['dominant_theme']}`",
            f"- Articles with themes: `{summary.get('theme_assignment_summary', {}).get('articles_with_themes', 0)}`",
            "",
            "## 2. Corpus coverage and descriptive stats",
            "",
            f"- Articles with abstracts: `{summary['articles_with_abstract']}`",
            f"- Articles with keywords: `{summary['articles_with_keywords']}`",
            f"- Total raw references: `{summary['total_references_raw']}`",
            f"- Total parsed references: `{summary['total_references_parsed']}`",
            "",
            "### Numeric descriptive profiles",
            "",
        ]
    )
    lines.extend(
        _markdown_records(
            payload["descriptive_profiles"],
            ["metric", "count", "mean", "median", "mode", "min", "max"],
        )
    )
    lines.extend(["", "### Theme coverage", ""])
    lines.extend(_markdown_records(payload["theme_assignment_rows"], ["source", "article_count", "share"]))
    lines.extend(
        [
            "",
            "## 3. Classification distribution",
            "",
        ]
    )
    lines.extend(_markdown_records(payload["label_distribution"], ["label", "count", "share"]))
    lines.extend(["", "## 4. Themes and keywords", ""])
    lines.append("### Top themes")
    lines.extend(_markdown_records(payload["top_themes"], ["theme", "count", "share"]))
    lines.append("")
    lines.append("### Top keywords")
    lines.extend(_markdown_records(payload["top_keywords"], ["keyword", "keyword_source", "article_count"]))
    lines.extend(["", "## 5. Corpus authors", ""])
    lines.extend(_markdown_records(payload["top_corpus_authors"], ["author_display", "corpus_author_count", "article_count"]))
    lines.extend(["", "## 6. Cited authors", ""])
    lines.extend(
        _markdown_records(
            payload["top_cited_authors"],
            ["author_display", "cited_author_count", "article_citation_coverage"],
        )
    )
    lines.extend(["", "## 7. Analytical crosses", ""])
    lines.append("### Author x label")
    lines.extend(
        _markdown_records(
            payload["author_label_rows"],
            ["cited_author_display", "label_name", "article_count", "share_within_author"],
        )
    )
    lines.append("")
    lines.append("### Theme x label")
    lines.extend(
        _markdown_records(
            payload["theme_label_rows"],
            ["theme", "label_name", "article_count", "share_within_theme"],
        )
    )
    lines.append("")
    lines.append("### Keyword x label")
    lines.extend(
        _markdown_records(
            payload["keyword_label_rows"],
            ["keyword", "keyword_source", "label_name", "article_count"],
        )
    )
    lines.extend(["", "## 8. Networks", ""])
    if payload["network_summary"] is None:
        lines.append("- Network outputs are not available for this run.")
    else:
        lines.extend(
            [
                f"- Co-citation edges: `{payload['network_summary']['cocitation_edges']}`",
                f"- Co-author edges: `{payload['network_summary']['coauthor_edges']}`",
                f"- Bibliographic coupling edges: `{payload['network_summary']['bibliographic_coupling_edges']}`",
            ]
        )
    lines.extend(
        [
            "",
            "## 9. Data quality and limitations",
            "",
            f"- Unparsed references: `{summary['total_references_raw'] - summary['total_references_parsed']}`",
            f"- Articles without abstracts: `{summary['total_articles'] - summary['articles_with_abstract']}`",
            f"- Articles without keywords: `{summary['total_articles'] - summary['articles_with_keywords']}`",
            "- Author identity is normalized conservatively; homonyms may remain unresolved.",
            "- Theme and keyword claims are based on deterministic corpus fields plus TF-IDF fallback terms.",
            "",
            "## 10. Conclusions",
            "",
            f"- The classified Scopus corpus contains `{summary['total_articles']}` articles with a reference parsing success rate of `{summary['reference_parse_success_rate']:.2%}`.",
            f"- The most represented classification is `{summary['dominant_label']}`, and the most frequent theme is `{summary['dominant_theme']}`.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def render_html_report(
    payload: dict[str, object],
    *,
    config: BibliometricConfig,
) -> str:
    def section_table(rows: list[dict[str, object]], columns: list[str]) -> str:
        if not rows:
            return "<p>None available.</p>"
        head = "".join(f"<th>{html.escape(column)}</th>" for column in columns)
        body_rows = []
        for row in rows:
            cells = "".join(f"<td>{html.escape(_format_cell(row.get(column, '')))}</td>" for column in columns)
            body_rows.append(f"<tr>{cells}</tr>")
        return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>"

    summary = payload["summary"]
    network_html = "<p>Network outputs are not available for this run.</p>"
    if payload["network_summary"] is not None:
        network_html = (
            "<ul>"
            f"<li>Co-citation edges: {payload['network_summary']['cocitation_edges']}</li>"
            f"<li>Co-author edges: {payload['network_summary']['coauthor_edges']}</li>"
            f"<li>Bibliographic coupling edges: {payload['network_summary']['bibliographic_coupling_edges']}</li>"
            "</ul>"
        )
    descriptive_profiles_html = section_table(
        payload["descriptive_profiles"],
        ["metric", "count", "mean", "median", "mode", "min", "max"],
    )
    theme_assignment_html = section_table(
        payload["theme_assignment_rows"],
        ["source", "article_count", "share"],
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Scopus Analytics Report</title>
  <style>
    body {{ font-family: Georgia, serif; margin: 32px; color: #1f2933; background: #f7f4ee; }}
    h1,h2,h3 {{ color: #12343b; }}
    .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }}
    .card {{ background: white; border: 1px solid #d9d2c3; border-radius: 10px; padding: 14px; }}
    table {{ width: 100%; border-collapse: collapse; background: white; margin: 12px 0 20px; }}
    th, td {{ border: 1px solid #d9d2c3; padding: 8px; text-align: left; }}
    th {{ background: #e8e2d4; }}
  </style>
</head>
<body>
  <h1>Informe de análisis bibliométrico y temático - Corpus Scopus</h1>
  <h2>1. Executive summary</h2>
  <div class="cards">
    <div class="card"><strong>Total articles</strong><div>{summary['total_articles']}</div></div>
    <div class="card"><strong>References coverage</strong><div>{summary['articles_with_references']}</div></div>
    <div class="card"><strong>Parse success rate</strong><div>{summary['reference_parse_success_rate']:.2%}</div></div>
    <div class="card"><strong>Dominant label</strong><div>{html.escape(str(summary['dominant_label']))}</div></div>
  </div>
  <h2>2. Corpus coverage and descriptive stats</h2>
  <ul>
    <li>Articles with abstracts: {summary['articles_with_abstract']}</li>
    <li>Articles with keywords: {summary['articles_with_keywords']}</li>
    <li>Total raw references: {summary['total_references_raw']}</li>
    <li>Total parsed references: {summary['total_references_parsed']}</li>
  </ul>
  <h3>Numeric descriptive profiles</h3>
  {descriptive_profiles_html}
  <h3>Theme coverage</h3>
  {theme_assignment_html}
  <h2>3. Classification distribution</h2>
  {section_table(payload['label_distribution'], ['label', 'count', 'share'])}
  <h2>4. Themes and keywords</h2>
  <h3>Top themes</h3>
  {section_table(payload['top_themes'], ['theme', 'count', 'share'])}
  <h3>Top keywords</h3>
  {section_table(payload['top_keywords'], ['keyword', 'keyword_source', 'article_count'])}
  <h2>5. Corpus authors</h2>
  {section_table(payload['top_corpus_authors'], ['author_display', 'corpus_author_count', 'article_count'])}
  <h2>6. Cited authors</h2>
  {section_table(payload['top_cited_authors'], ['author_display', 'cited_author_count', 'article_citation_coverage'])}
  <h2>7. Analytical crosses</h2>
  <h3>Author x label</h3>
  {section_table(payload['author_label_rows'], ['cited_author_display', 'label_name', 'article_count', 'share_within_author'])}
  <h3>Theme x label</h3>
  {section_table(payload['theme_label_rows'], ['theme', 'label_name', 'article_count', 'share_within_theme'])}
  <h3>Keyword x label</h3>
  {section_table(payload['keyword_label_rows'], ['keyword', 'keyword_source', 'label_name', 'article_count'])}
  <h2>8. Networks</h2>
  {network_html}
  <h2>9. Data quality and limitations</h2>
  <ul>
    <li>Unparsed references: {summary['total_references_raw'] - summary['total_references_parsed']}</li>
    <li>Articles without abstracts: {summary['total_articles'] - summary['articles_with_abstract']}</li>
    <li>Articles without keywords: {summary['total_articles'] - summary['articles_with_keywords']}</li>
    <li>Author identity remains conservatively normalized.</li>
    <li>Theme claims rely on deterministic fields and TF-IDF fallback terms.</li>
  </ul>
  <h2>10. Conclusions</h2>
  <p>The classified Scopus corpus contains {summary['total_articles']} articles with a reference parsing success rate of {summary['reference_parse_success_rate']:.2%}.</p>
  <p>The dominant classification is {html.escape(str(summary['dominant_label']))}, while the dominant theme is {html.escape(str(summary['dominant_theme']))}.</p>
</body>
</html>
"""


def build_interactive_bundle(
    bibliometric_artifacts: BibliometricArtifacts,
    *,
    output_dir: str | Path,
    config: BibliometricConfig,
    network_artifacts: NetworkArtifacts | None = None,
    network_run_artifacts: NetworkRunArtifacts | None = None,
    root: Path | None = None,
) -> Path:
    project_root = root or ROOT
    resolved_output_dir = Path(output_dir)
    if not resolved_output_dir.is_absolute():
        resolved_output_dir = (project_root / resolved_output_dir).resolve()
    data_dir = resolved_output_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    payload = _build_report_payload(
        bibliometric_artifacts,
        config=config,
        network_artifacts=network_artifacts,
        network_run_artifacts=network_run_artifacts,
    )
    _write_data_exports(bibliometric_artifacts, data_dir=data_dir, network_artifacts=network_artifacts)
    index_path = resolved_output_dir / "index.html"
    index_path.write_text(_interactive_html(payload), encoding="utf-8")
    return index_path


def _build_report_payload(
    bibliometric_artifacts: BibliometricArtifacts,
    *,
    config: BibliometricConfig,
    network_artifacts: NetworkArtifacts | None,
    network_run_artifacts: NetworkRunArtifacts | None,
) -> dict[str, object]:
    stats = bibliometric_artifacts.descriptive_stats
    label_distribution = _distribution_rows(
        stats.get("labels_distribution", {}),
        total=int(stats.get("total_articles", 0)),
    )
    theme_distribution = _distribution_rows(
        stats.get("themes_distribution", {}),
        total=max(sum(stats.get("themes_distribution", {}).values()), 1),
        key_name="theme",
    )
    dominant_label = label_distribution[0]["label"] if label_distribution else "unassigned"
    dominant_theme = theme_distribution[0]["theme"] if theme_distribution else "unassigned"
    return {
        "summary": {
            **stats,
            "dominant_label": dominant_label,
            "dominant_theme": dominant_theme,
        },
        "label_distribution": label_distribution,
        "top_themes": theme_distribution[: config.report.top_n_themes],
        "top_keywords": _top_keyword_rows(
            bibliometric_artifacts.keyword_label_matrix,
            limit=config.report.top_n_keywords,
        ),
        "descriptive_profiles": _descriptive_profile_rows(stats.get("numeric_descriptives", {})),
        "theme_assignment_rows": _theme_assignment_rows(
            stats.get("theme_assignment_summary", {}),
            total=int(stats.get("total_articles", 0)),
        ),
        "distribution_snapshots": stats.get("distribution_snapshots", {}),
        "theme_year_timeline": stats.get("theme_year_timeline", []),
        "theme_label_heatmap": _heatmap_rows(
            bibliometric_artifacts.theme_label_matrix,
            row_column="theme",
            column_column="label_name",
            value_column="article_count",
            top_rows=config.report.top_n_themes,
            top_columns=max(config.report.top_n_themes, 6),
        ),
        "author_label_heatmap": _heatmap_rows(
            bibliometric_artifacts.author_label_matrix,
            row_column="cited_author_display",
            column_column="label_name",
            value_column="article_count",
            top_rows=min(config.report.top_n_authors, 12),
            top_columns=max(config.report.top_n_themes, 6),
        ),
        "label_year_heatmap": _year_label_heatmap_rows(bibliometric_artifacts.enriched_rows),
        "corpus_author_rows": bibliometric_artifacts.corpus_author_frequency.to_dict(orient="records"),
        "cited_author_rows": bibliometric_artifacts.cited_author_frequency.head(5000).to_dict(orient="records"),
        "cited_author_total_rows": int(len(bibliometric_artifacts.cited_author_frequency)),
        "top_corpus_authors": bibliometric_artifacts.corpus_author_frequency.head(
            config.report.top_n_authors
        ).to_dict(orient="records"),
        "top_cited_authors": bibliometric_artifacts.cited_author_frequency.head(
            config.report.top_n_authors
        ).to_dict(orient="records"),
        "author_label_rows": _top_matrix_rows(
            bibliometric_artifacts.author_label_matrix,
            order_columns=["article_count", "mention_count", "share_within_author"],
            limit=config.report.top_n_matrix_rows,
        ),
        "theme_label_rows": _top_matrix_rows(
            bibliometric_artifacts.theme_label_matrix,
            order_columns=["article_count", "share_within_theme", "share_within_label"],
            limit=config.report.top_n_matrix_rows,
        ),
        "keyword_label_rows": _top_matrix_rows(
            bibliometric_artifacts.keyword_label_matrix,
            order_columns=["article_count", "keyword_count", "share_within_keyword"],
            limit=config.report.top_n_matrix_rows,
        ),
        "author_theme_rows": _top_matrix_rows(
            bibliometric_artifacts.author_theme_matrix,
            order_columns=["article_count", "mention_count", "share_within_author"],
            limit=config.report.top_n_matrix_rows,
        ),
        "network_summary": None if network_artifacts is None else {
            **network_artifacts.metadata,
            "preview_files": {} if network_run_artifacts is None else {
                "co_citation_authors_html": str(network_run_artifacts.cocitation_html_path.name),
                "co_author_html": str(network_run_artifacts.coauthor_html_path.name),
                "bibliographic_coupling_html": str(network_run_artifacts.coupling_html_path.name),
            },
        },
    }


def _distribution_rows(distribution: dict[str, int], *, total: int, key_name: str = "label") -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for key, count in sorted(distribution.items(), key=lambda item: (-item[1], item[0])):
        rows.append({key_name: key, "count": int(count), "share": 0.0 if total == 0 else float(count) / float(total)})
    return rows


def _top_keyword_rows(frame: pd.DataFrame, *, limit: int) -> list[dict[str, object]]:
    if frame.empty:
        return []
    grouped = (
        frame.groupby(["keyword", "keyword_source"], dropna=False)["article_count"]
        .sum()
        .reset_index()
        .sort_values(by=["article_count", "keyword"], ascending=[False, True])
    )
    return grouped.head(limit).to_dict(orient="records")


def _top_matrix_rows(
    frame: pd.DataFrame,
    *,
    order_columns: list[str],
    limit: int,
) -> list[dict[str, object]]:
    if frame.empty:
        return []
    existing_columns = [column for column in order_columns if column in frame.columns]
    if not existing_columns:
        return frame.head(limit).to_dict(orient="records")
    ordered = frame.sort_values(by=existing_columns, ascending=[False] * len(existing_columns))
    return ordered.head(limit).to_dict(orient="records")


def _markdown_records(rows: list[dict[str, object]], columns: list[str]) -> list[str]:
    if not rows:
        return ["_None_"]
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(_format_cell(row.get(column, "")) for column in columns) + " |")
    return lines


def _format_cell(value: object) -> str:
    if isinstance(value, float):
        if 0.0 <= value <= 1.0:
            return f"{value:.2%}"
        return f"{value:.4f}"
    return str(value)


def _descriptive_profile_rows(profiles: dict[str, object]) -> list[dict[str, object]]:
    metric_labels = {
        "publication_year": "Publication year",
        "authors_per_article": "Authors per article",
        "references_per_article": "References per article",
        "keywords_per_article": "Keywords per article",
        "abstract_word_count": "Abstract words",
    }
    rows: list[dict[str, object]] = []
    for key, label in metric_labels.items():
        profile = profiles.get(key)
        if not isinstance(profile, dict):
            continue
        rows.append({"metric": label, **profile})
    return rows


def _theme_assignment_rows(summary: dict[str, int], *, total: int) -> list[dict[str, object]]:
    labels = {
        "articles_with_explicit_themes": "Explicit themes",
        "articles_with_derived_keyword_themes": "Derived from keywords",
        "articles_with_derived_tfidf_themes": "Derived from TF-IDF",
        "articles_without_themes": "Without themes",
    }
    rows: list[dict[str, object]] = []
    for key, label in labels.items():
        count = int(summary.get(key, 0))
        rows.append(
            {
                "source": label,
                "article_count": count,
                "share": 0.0 if total == 0 else float(count) / float(total),
            }
        )
    return rows


def _heatmap_rows(
    frame: pd.DataFrame,
    *,
    row_column: str,
    column_column: str,
    value_column: str,
    top_rows: int,
    top_columns: int,
) -> dict[str, object]:
    if frame.empty or row_column not in frame.columns or column_column not in frame.columns or value_column not in frame.columns:
        return {"rows": [], "columns": [], "values": []}
    pivot = (
        frame.groupby([row_column, column_column], dropna=False)[value_column]
        .sum()
        .unstack(fill_value=0)
    )
    if pivot.empty:
        return {"rows": [], "columns": [], "values": []}
    pivot = pivot.loc[pivot.sum(axis=1).sort_values(ascending=False).head(top_rows).index]
    column_order = pivot.sum(axis=0).sort_values(ascending=False).head(top_columns).index
    pivot = pivot.loc[:, column_order]
    return {
        "rows": [str(index) for index in pivot.index.tolist()],
        "columns": [str(column) for column in pivot.columns.tolist()],
        "values": [[int(value) for value in row] for row in pivot.to_numpy().tolist()],
    }


def _year_label_heatmap_rows(enriched_rows: pd.DataFrame) -> dict[str, object]:
    if enriched_rows.empty:
        return {"rows": [], "columns": [], "values": []}
    candidate_year = None
    for column in ("year", "publication_year", "Year"):
        if column in enriched_rows.columns:
            candidate_year = column
            break
    if candidate_year is None:
        return {"rows": [], "columns": [], "values": []}
    label_column = "label_name" if "label_name" in enriched_rows.columns else None
    if label_column is None:
        return {"rows": [], "columns": [], "values": []}
    frame = enriched_rows[[candidate_year, label_column]].copy()
    frame[candidate_year] = pd.to_numeric(frame[candidate_year], errors="coerce")
    frame[label_column] = frame[label_column].fillna("").map(str).str.strip()
    frame = frame.loc[frame[candidate_year].notna() & (frame[label_column] != "")]
    if frame.empty:
        return {"rows": [], "columns": [], "values": []}
    frame[candidate_year] = frame[candidate_year].astype(int)
    pivot = (
        frame.groupby([candidate_year, label_column], dropna=False)
        .size()
        .unstack(fill_value=0)
        .sort_index()
    )
    label_order = pivot.sum(axis=0).sort_values(ascending=False).index
    pivot = pivot.loc[:, label_order]
    return {
        "rows": [str(index) for index in pivot.index.tolist()],
        "columns": [str(column) for column in pivot.columns.tolist()],
        "values": [[int(value) for value in row] for row in pivot.to_numpy().tolist()],
    }


def _interactive_html(payload: dict[str, object]) -> str:
    serialized = json.dumps(payload, ensure_ascii=False)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Scopus Interactive Analytics</title>
  <style>
    :root {{
      --bg: #f4f0e8;
      --panel: #fffdf9;
      --ink: #20323a;
      --accent: #0f766e;
      --accent-2: #d97706;
      --muted: #d9d2c3;
      --soft: #efe7d8;
      --shadow: 0 10px 28px rgba(16, 24, 40, 0.08);
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: 'Segoe UI', sans-serif; background:
      radial-gradient(circle at top left, #f8edd1 0, transparent 34%),
      radial-gradient(circle at top right, #dcefe2 0, transparent 28%),
      linear-gradient(180deg, #faf6ef 0%, var(--bg) 100%);
      color: var(--ink); }}
    header {{ padding: 34px 26px; background: linear-gradient(135deg, #0b3c49, #2d6a4f 58%, #6b8e23 100%); color: white; position: relative; overflow: hidden; }}
    header::after {{ content: ''; position: absolute; inset: auto -8% -60px auto; width: 260px; height: 260px; border-radius: 50%; background: rgba(255,255,255,0.09); }}
    .eyebrow {{ text-transform: uppercase; letter-spacing: 0.16em; font-size: 12px; opacity: 0.8; }}
    main {{ padding: 24px; display: grid; gap: 18px; }}
    .panel {{ background: var(--panel); border: 1px solid var(--muted); border-radius: 18px; padding: 18px; box-shadow: var(--shadow); }}
    .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }}
    .card {{ padding: 14px; border-radius: 14px; background: linear-gradient(180deg, #fffdf9, #f8f5ee); border: 1px solid var(--muted); }}
    .card strong {{ display: block; font-size: 13px; color: #52606d; margin-bottom: 6px; }}
    .big-number {{ font-size: 28px; font-weight: 700; color: #102a43; }}
    .grid-2 {{ display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(0, 0.8fr); gap: 18px; }}
    .stack {{ display: grid; gap: 14px; }}
    .muted {{ color: #6b7280; }}
    table {{ width: 100%; border-collapse: collapse; background: white; }}
    th, td {{ border: 1px solid var(--muted); padding: 8px; text-align: left; vertical-align: top; }}
    th {{ background: var(--soft); position: sticky; top: 0; }}
    .controls {{ display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 10px; }}
    select, input {{ padding: 8px 10px; border-radius: 10px; border: 1px solid #c7bfb0; background: white; }}
    .table-wrap {{ max-height: 460px; overflow: auto; border-radius: 12px; }}
    .bars {{ display: grid; gap: 10px; }}
    .bar-row {{ display: grid; grid-template-columns: minmax(160px, 220px) 1fr 62px; gap: 10px; align-items: center; }}
    .bar-track {{ height: 12px; background: #ece7dc; border-radius: 999px; overflow: hidden; }}
    .bar-fill {{ height: 100%; border-radius: 999px; background: linear-gradient(90deg, var(--accent), #34a0a4); }}
    .metric-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }}
    .metric-card {{ border: 1px solid var(--muted); border-radius: 14px; padding: 14px; background: white; }}
    .metric-card strong {{ display: block; margin-bottom: 8px; color: #35505a; }}
    .metric-card dl {{ margin: 0; display: grid; grid-template-columns: auto 1fr; gap: 6px 10px; font-size: 14px; }}
    .metric-card dt {{ color: #52606d; }}
    .metric-card dd {{ margin: 0; font-weight: 600; color: #102a43; }}
    .heatmap-wrap {{ overflow: auto; border: 1px solid var(--muted); border-radius: 14px; background: white; }}
    .heatmap {{ display: grid; gap: 1px; background: #e7dfd1; min-width: 520px; }}
    .heatmap-cell {{
      padding: 10px 8px;
      min-height: 48px;
      display: flex;
      align-items: center;
      justify-content: center;
      text-align: center;
      font-size: 13px;
      background: white;
    }}
    .heatmap-head {{ position: sticky; top: 0; z-index: 1; font-weight: 700; background: #f4efe5; }}
    .heatmap-side {{ justify-content: flex-start; font-weight: 600; background: #fbf8f2; }}
    .heatmap-value {{ font-variant-numeric: tabular-nums; }}
    .viz-stack {{ display: grid; gap: 18px; }}
    .distribution-stack {{ display: grid; gap: 18px; }}
    .distribution-card {{ border: 1px solid var(--muted); border-radius: 16px; padding: 18px; background: white; }}
    .distribution-card h3 {{ margin-top: 0; }}
    .distribution-meta {{ display: flex; flex-wrap: wrap; gap: 10px; margin: 10px 0 12px; }}
    .distribution-pill {{ padding: 7px 10px; border-radius: 999px; background: #f5efe2; border: 1px solid #e1d5c0; font-size: 13px; color: #35505a; }}
    .distribution-viz {{ width: 100%; height: 280px; border: 1px solid #e5dccd; border-radius: 12px; background: linear-gradient(180deg, #fbf8f2, #fff); }}
    .distribution-toplist {{ margin-top: 14px; display: grid; gap: 8px; }}
    .distribution-toprow {{ display: grid; grid-template-columns: minmax(180px, 260px) 1fr 72px; gap: 10px; align-items: center; }}
    .section-stack {{ display: grid; gap: 18px; }}
    .author-panel .table-wrap {{ max-height: 860px; }}
    .tag {{ display: inline-block; padding: 4px 8px; border-radius: 999px; background: #e6f4ea; color: #1b4332; font-size: 12px; }}
    .empty {{ padding: 16px; border: 1px dashed #c9c1b2; border-radius: 12px; background: #faf7f0; }}
    .kpi-note {{ margin-top: 10px; color: #52606d; font-size: 14px; }}
    .insight {{ padding: 12px 14px; border-radius: 12px; background: #f7f2e8; border: 1px solid #e2d7c5; margin-top: 10px; color: #29434e; }}
    .insight strong {{ color: #102a43; }}
    .timeline-legend {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 12px; }}
    .timeline-item {{ display: inline-flex; align-items: center; gap: 6px; font-size: 13px; color: #35505a; }}
    .timeline-swatch {{ width: 12px; height: 12px; border-radius: 999px; }}
    a {{ color: var(--accent); }}
    @media (max-width: 900px) {{
      .grid-2 {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="eyebrow">Offline Analytics Bundle</div>
    <h1>Scopus Interactive Analytics</h1>
    <p>Artifact-driven exploration over the classified Scopus corpus, designed for local review and client handoff.</p>
  </header>
  <main>
    <section class="panel" id="overview"></section>
    <section>
      <div class="panel">
        <h2>Descriptive profiles</h2>
        <p class="muted">Mean, median, mode, and range for the main article-level variables in the classified Scopus corpus. Count refers to the number of articles with a usable value for that metric.</p>
        <div id="descriptiveProfiles"></div>
      </div>
    </section>
    <section class="panel">
      <h2>Corpus distributions</h2>
      <p class="muted">Article-level distributions, now separated into readable full-width panels so the main patterns can be understood at a glance.</p>
      <div id="distributionCharts" class="distribution-stack"></div>
    </section>
    <section class="panel">
      <div class="tag" style="margin-bottom:10px">Heatmaps</div>
      <h2>Theme x label heatmap</h2>
      <p class="muted">How recovered themes distribute across the official classification labels.</p>
      <div id="themeLabelHeatmap"></div>
    </section>
    <section class="panel">
      <h2>Cited author x label heatmap</h2>
      <p class="muted">Which cited authors are most associated with each official label after curating the cited-author extraction.</p>
      <div id="authorLabelHeatmap"></div>
    </section>
    <section class="panel">
      <div class="tag" style="margin-bottom:10px">Temporal evolution</div>
      <h2>Label x publication year heatmap</h2>
      <p class="muted">Temporal concentration of the official labels across publication years.</p>
      <div id="labelYearHeatmap"></div>
    </section>
    <section class="panel">
      <h2>Theme timeline</h2>
      <p class="muted">Evolution over time of the most discussed themes recovered in the corpus.</p>
      <div id="themeTimeline"></div>
    </section>
    <section class="panel">
      <h2>Interpretation guide</h2>
      <p class="muted">What these descriptive metrics mean, and how to read them in research terms.</p>
      <div id="interpretationGuide"></div>
    </section>
    <section class="grid-2">
      <div class="panel author-panel">
        <h2>Authors</h2>
        <p class="muted">Search across all corpus authors. Cited authors are shown as a curated ranked slice here, with the full exported CSV linked below because the complete cited-author universe is very large.</p>
        <div class="controls">
          <label>Author table:
            <select id="authorMode">
              <option value="corpus">Corpus authors</option>
              <option value="cited">Cited authors</option>
            </select>
          </label>
          <label>Search:
            <input id="authorSearch" placeholder="Type an author name">
          </label>
        </div>
        <div class="kpi-note">
          Full exports:
          <a href="data/author_frequency.csv">Corpus authors CSV</a> |
          <a href="data/cited_author_frequency.csv">Cited authors CSV</a>
        </div>
        <div id="authorsTable"></div>
      </div>
      <div class="panel stack">
        <div>
          <h2>Cross highlights</h2>
          <p class="muted">Top cross-tab rows ranked by article coverage instead of raw file order.</p>
        </div>
        <div>
          <span class="tag">Author x label</span>
          <div id="authorLabelTable"></div>
        </div>
        <div>
          <span class="tag">Author x theme</span>
          <div id="authorThemeTable"></div>
        </div>
      </div>
    </section>
    <section class="grid-2">
      <div class="panel">
        <h2>Themes and keywords</h2>
        <div class="controls">
          <label>Keyword source:
            <select id="keywordSource"></select>
          </label>
          <label>Search:
            <input id="keywordSearch" placeholder="Type a keyword">
          </label>
        </div>
        <div id="keywordsTable"></div>
      </div>
      <div class="panel">
        <h2>Theme x label</h2>
        <p class="muted">When explicit themes are missing, this view is backfilled from author keywords, then index keywords, and only then TF-IDF terms.</p>
        <div id="themesTable"></div>
      </div>
    </section>
    <section class="panel">
      <h2>Networks</h2>
      <div id="networkSummary"></div>
    </section>
  </main>
  <script>
    const payload = {serialized};
    const fmtPct = (value) => `${{(value * 100).toFixed(2)}}%`;
    const fmtNumber = (value) => typeof value === 'number' ? value.toLocaleString('en-US') : value;
    const palette = ['#0f766e', '#d97706', '#2563eb', '#a21caf', '#b91c1c', '#0891b2', '#65a30d', '#7c3aed'];
    const table = (rows, columns, options = {{}}) => {{
      if (!rows.length) return '<div class="empty">None available for this view.</div>';
      const head = `<tr>${{columns.map((c) => `<th>${{c}}</th>`).join('')}}</tr>`;
      const body = rows.map((row) => `<tr>${{columns.map((c) => {{
        const cell = row[c];
        const rendered = typeof cell === 'number' && cell <= 1 && cell >= 0
          ? fmtPct(cell)
          : fmtNumber(cell ?? '');
        return `<td>${{rendered}}</td>`;
      }}).join('')}}</tr>`).join('');
      const maxHeight = options.maxHeight ? ` style="max-height:${{options.maxHeight}}px"` : '';
      return `<div class="table-wrap"${{maxHeight}}><table><thead>${{head}}</thead><tbody>${{body}}</tbody></table></div>`;
    }};
    const bars = (rows, keyField) => {{
      if (!rows.length) return '<div class="empty">No ranked distribution available.</div>';
      const max = Math.max(...rows.map((row) => row.count || row.article_count || 0), 1);
      return `<div class="bars">${{rows.map((row) => {{
        const value = row.count ?? row.article_count ?? 0;
        const label = row[keyField] ?? row.keyword ?? '';
        return `<div class="bar-row"><div>${{label}}</div><div class="bar-track"><div class="bar-fill" style="width:${{(value / max) * 100}}%"></div></div><div>${{value}}</div></div>`;
      }}).join('')}}</div>`;
    }};
    const filterRows = (rows, term, fields) => {{
      const needle = term.trim().toLowerCase();
      if (!needle) return rows;
      return rows.filter((row) => fields.some((field) => String(row[field] ?? '').toLowerCase().includes(needle)));
    }};
    const metricCards = (rows) => {{
      if (!rows.length) return '<div class="empty">No numeric descriptive profiles available.</div>';
      return `<div class="metric-grid">${{rows.map((row) => `
        <div class="metric-card">
          <strong>${{row.metric}}</strong>
          <dl>
            <dt>Count</dt><dd>${{fmtNumber(row.count)}}</dd>
            <dt>Mean</dt><dd>${{fmtNumber(row.mean)}}</dd>
            <dt>Median</dt><dd>${{fmtNumber(row.median)}}</dd>
            <dt>Mode</dt><dd>${{fmtNumber(row.mode)}}</dd>
            <dt>Min</dt><dd>${{fmtNumber(row.min)}}</dd>
            <dt>Max</dt><dd>${{fmtNumber(row.max)}}</dd>
          </dl>
        </div>
      `).join('')}}</div>`;
    }};
    const profileByMetric = (rows) =>
      Object.fromEntries((rows || []).map((row) => [row.metric, row]));
    const parseBucketStart = (bucket) => {{
      const text = String(bucket ?? '').trim();
      const match = text.match(/-?\\d+(?:\\.\\d+)?/);
      return match ? Number(match[0]) : Number.POSITIVE_INFINITY;
    }};
    const summarizeTail = (rows) => {{
      if (!rows?.length) return {{ total: 0, topShare: 0 }};
      const total = rows.reduce((sum, row) => sum + (row.count || 0), 0);
      const ranked = [...rows].sort((a, b) => (b.count || 0) - (a.count || 0));
      return {{ total, topShare: total ? ((ranked[0]?.count || 0) / total) : 0 }};
    }};
    const metricInsight = (metric, row, totalArticles) => {{
      if (!row) return '';
      const count = row.count ?? 0;
      const coverage = totalArticles ? fmtPct(count / totalArticles) : '0.00%';
      const messages = {{
        'Publication year': `This uses ${{fmtNumber(count)}} articles with year metadata, covering ${{coverage}} of the classified corpus. The mean year tells us the center of gravity of the literature, while the median shows the typical publication year without being distorted by older tail records.`,
        'Authors per article': `This counts named corpus authors per article across ${{fmtNumber(count)}} records. The mean reflects overall collaboration intensity, while the median reveals what a typical article looks like in practice.`,
        'References per article': `This measures bibliography size article by article across the full corpus. The mean is useful for overall citation density, while the median is usually the better indicator of a typical article because very long reference lists can pull the average upward.`,
        'Keywords per article': `This reflects declared author keywords plus index keywords per article. It is a quick proxy for metadata richness and thematic self-description.`,
        'Abstract words': `This measures abstract length. The median helps us understand the common reporting style, while the max shows how heterogeneous abstract writing becomes across journals and periods.`,
      }};
      return `<div class="insight"><strong>${{metric}}:</strong> ${{messages[metric] || ''}}</div>`;
    }};
    const distributionSvg = (rows) => {{
      if (!rows?.length) return '';
      const width = 920;
      const height = 280;
      const margin = {{ top: 16, right: 18, bottom: 54, left: 54 }};
      const innerWidth = width - margin.left - margin.right;
      const innerHeight = height - margin.top - margin.bottom;
      const max = Math.max(...rows.map((row) => row.count || 0), 1);
      const barWidth = innerWidth / Math.max(rows.length, 1);
      const tickCount = Math.min(6, rows.length);
      const tickIndexes = [...new Set(
        Array.from({{ length: tickCount }}, (_value, index) =>
          Math.round((index / Math.max(tickCount - 1, 1)) * Math.max(rows.length - 1, 0))
        )
      )];
      const yTicks = [0, 0.25, 0.5, 0.75, 1];
      const barsMarkup = rows.map((row, index) => {{
        const value = row.count || 0;
        const barHeight = (value / max) * innerHeight;
        const x = margin.left + (index * barWidth) + Math.max(barWidth * 0.08, 1);
        const y = margin.top + innerHeight - barHeight;
        const widthPx = Math.max(barWidth * 0.84, 1.5);
        const title = `${{row.bucket}}: ${{fmtNumber(value)}} articles`;
        return `<g><title>${{title}}</title><rect x="${{x.toFixed(2)}}" y="${{y.toFixed(2)}}" width="${{widthPx.toFixed(2)}}" height="${{barHeight.toFixed(2)}}" rx="2" fill="#0f766e" opacity="0.88"></rect></g>`;
      }}).join('');
      const xTicksMarkup = tickIndexes.map((index) => {{
        const x = margin.left + ((index + 0.5) * barWidth);
        const label = rows[index]?.bucket ?? '';
        return `
          <line x1="${{x.toFixed(2)}}" y1="${{height - margin.bottom}}" x2="${{x.toFixed(2)}}" y2="${{height - margin.bottom + 6}}" stroke="#9ca3af" stroke-width="1"></line>
          <text x="${{x.toFixed(2)}}" y="${{height - margin.bottom + 22}}" text-anchor="middle" font-size="12" fill="#52606d">${{label}}</text>
        `;
      }}).join('');
      const yTicksMarkup = yTicks.map((ratio) => {{
        const value = Math.round(max * ratio);
        const y = margin.top + innerHeight - (ratio * innerHeight);
        return `
          <line x1="${{margin.left}}" y1="${{y.toFixed(2)}}" x2="${{width - margin.right}}" y2="${{y.toFixed(2)}}" stroke="#ebe3d4" stroke-width="1"></line>
          <text x="${{margin.left - 10}}" y="${{(y + 4).toFixed(2)}}" text-anchor="end" font-size="12" fill="#52606d">${{fmtNumber(value)}}</text>
        `;
      }}).join('');
      return `
        <svg viewBox="0 0 ${{width}} ${{height}}" class="distribution-viz" preserveAspectRatio="none" aria-label="Distribution chart">
          <line x1="${{margin.left}}" y1="${{height - margin.bottom}}" x2="${{width - margin.right}}" y2="${{height - margin.bottom}}" stroke="#6b7280" stroke-width="1.2"></line>
          <line x1="${{margin.left}}" y1="${{margin.top}}" x2="${{margin.left}}" y2="${{height - margin.bottom}}" stroke="#6b7280" stroke-width="1.2"></line>
          ${{yTicksMarkup}}
          ${{barsMarkup}}
          ${{xTicksMarkup}}
        </svg>
      `;
    }};
    const distributionTopRows = (rows) => {{
      const ranked = [...(rows || [])].sort((a, b) => (b.count || 0) - (a.count || 0));
      if (!ranked.length) return '';
      const topRows = ranked.slice(0, 10);
      const max = Math.max(...topRows.map((row) => row.count || 0), 1);
      return `<div class="distribution-toplist">${{topRows.map((row) => `
        <div class="distribution-toprow">
          <div>${{row.bucket}}</div>
          <div class="bar-track"><div class="bar-fill" style="width:${{((row.count || 0) / max) * 100}}%"></div></div>
          <div>${{fmtNumber(row.count || 0)}}</div>
        </div>
      `).join('')}}</div>`;
    }};
    const distributionBlock = (title, rows, profile) => {{
      if (!rows?.length) return '';
      const ordered = [...rows].sort((a, b) => parseBucketStart(a.bucket) - parseBucketStart(b.bucket));
      const dominant = [...ordered].sort((a, b) => (b.count || 0) - (a.count || 0))[0];
      const summary = summarizeTail(ordered);
      return `
        <div class="distribution-card">
          <h3>${{title}}</h3>
          <div class="distribution-meta">
            <span class="distribution-pill">Articles with value: ${{fmtNumber(profile?.count ?? summary.total)}}</span>
            <span class="distribution-pill">Mean: ${{fmtNumber(profile?.mean ?? 'n/a')}}</span>
            <span class="distribution-pill">Median: ${{fmtNumber(profile?.median ?? 'n/a')}}</span>
            <span class="distribution-pill">Mode: ${{fmtNumber(profile?.mode ?? dominant?.bucket ?? 'n/a')}}</span>
            <span class="distribution-pill">Dominant bucket share: ${{fmtPct(summary.topShare)}}</span>
          </div>
          ${{distributionSvg(ordered)}}
          <div class="insight">${{distributionInsight(title, ordered, profile)}}</div>
          <div class="kpi-note">Top buckets by article count. The chart above preserves the full ordered distribution, while the ranked list below highlights where the corpus concentrates most strongly.</div>
          ${{distributionTopRows(ordered)}}
        </div>
      `;
    }};
    const distributionInsight = (title, rows, profile) => {{
      if (!rows?.length) return 'No distributional evidence is available for this variable.';
      const sorted = [...rows].sort((a, b) => (b.count || 0) - (a.count || 0));
      const dominant = sorted[0];
      const last = rows[rows.length - 1];
      const first = rows[0];
      const mean = profile?.mean;
      const median = profile?.median;
      const messages = {{
        'Publication year': `The highest concentration appears around <strong>${{dominant.bucket}}</strong>. With a mean of <strong>${{fmtNumber(mean)}}</strong> and a median of <strong>${{fmtNumber(median)}}</strong>, this panel shows whether the corpus is concentrated in recent years or whether earlier decades still carry substantial weight.`,
        'References per article': `The most recurrent bibliography-size bucket is <strong>${{dominant.bucket}}</strong>. Compare that center with the extended right tail to identify whether a smaller subset of review-style or theory-heavy papers is pulling the average upward.`,
        'Authors per article': `The most common authorship size is <strong>${{dominant.bucket}}</strong>. Here, <strong>0</strong> usually means missing author metadata rather than a true zero-author article, while a dominant value near <strong>1</strong> indicates a literature produced mainly by solo authors.`,
        'Keywords per article': `The most common keyword-count bucket is <strong>${{dominant.bucket}}</strong>. In this chart, <strong>0</strong> means articles without usable keyword metadata, so the left side reflects metadata absence as much as thematic sparsity.`,
        'Abstract words': `The most recurrent abstract-length bucket is <strong>${{dominant.bucket}}</strong>. The span from <strong>${{first.bucket}}</strong> to <strong>${{last.bucket}}</strong> shows how heterogeneous abstract-writing conventions are across journals, periods, and document types.`,
      }};
      return messages[title] || `The most common bucket here is <strong>${{dominant.bucket}}</strong>.`;
    }};
    const heatmap = (payload, labelPrefix = '') => {{
      const rows = payload?.rows || [];
      const columns = payload?.columns || [];
      const values = payload?.values || [];
      if (!rows.length || !columns.length || !values.length) {{
        return '<div class="empty">No heatmap data available for this view.</div>';
      }}
      const max = Math.max(...values.flat(), 1);
      const templateColumns = `minmax(180px, 1.2fr) repeat(${{columns.length}}, minmax(96px, 1fr))`;
      const cells = [];
      cells.push('<div class="heatmap-cell heatmap-head"></div>');
      columns.forEach((column) => cells.push(`<div class="heatmap-cell heatmap-head">${{column}}</div>`));
      rows.forEach((row, rowIndex) => {{
        cells.push(`<div class="heatmap-cell heatmap-side">${{row}}</div>`);
        columns.forEach((_column, columnIndex) => {{
          const value = values[rowIndex]?.[columnIndex] || 0;
          const intensity = value / max;
          const alpha = Math.max(0.08, intensity * 0.9);
          const bg = `rgba(15, 118, 110, ${{alpha.toFixed(3)}})`;
          const color = intensity > 0.55 ? '#f8fafc' : '#102a43';
          const title = `${{labelPrefix}}${{row}} x ${{columns[columnIndex]}}: ${{fmtNumber(value)}}`;
          cells.push(`<div class="heatmap-cell heatmap-value" title="${{title}}" style="background:${{bg}};color:${{color}}">${{fmtNumber(value)}}</div>`);
        }});
      }});
      return `<div class="heatmap-wrap"><div class="heatmap" style="grid-template-columns:${{templateColumns}}">${{cells.join('')}}</div></div>`;
    }};
    const themeTimeline = (rows) => {{
      if (!rows?.length) return '<div class="empty">No theme timeline is available for this run.</div>';
      const themes = [...new Set(rows.map((row) => row.theme))].slice(0, 8);
      const years = [...new Set(rows.map((row) => row.year))].sort((a, b) => a - b);
      const max = Math.max(...rows.map((row) => row.article_count || 0), 1);
      const width = 960;
      const height = 320;
      const margin = {{ top: 18, right: 20, bottom: 56, left: 54 }};
      const innerWidth = width - margin.left - margin.right;
      const innerHeight = height - margin.top - margin.bottom;
      const xForYear = (yearIndex) => margin.left + (yearIndex / Math.max(years.length - 1, 1)) * innerWidth;
      const yForValue = (value) => margin.top + innerHeight - ((value / max) * innerHeight);
      const series = themes.map((theme, index) => {{
        const themedRows = rows.filter((row) => row.theme === theme);
        const total = themedRows.reduce((sum, row) => sum + (row.article_count || 0), 0);
        const points = years.map((year, yearIndex) => {{
          const match = rows.find((row) => row.theme === theme && row.year === year);
          const value = match?.article_count || 0;
          const x = xForYear(yearIndex);
          const y = yForValue(value);
          return `${{x}},${{y}}`;
        }}).join(' ');
        return {{
          theme,
          color: palette[index % palette.length],
          points,
          total,
        }};
      }});
      const tickIndexes = [...new Set([
        0,
        ...Array.from({{ length: Math.min(6, years.length) }}, (_value, index) =>
          Math.round((index / Math.max(Math.min(6, years.length) - 1, 1)) * Math.max(years.length - 1, 0))
        ),
        years.length - 1,
      ])].filter((index) => index >= 0);
      const yTicks = [0, 0.25, 0.5, 0.75, 1];
      return `
        <svg viewBox="0 0 ${{width}} ${{height}}" class="distribution-viz" preserveAspectRatio="none" aria-label="Theme timeline">
          <line x1="${{margin.left}}" y1="${{height - margin.bottom}}" x2="${{width - margin.right}}" y2="${{height - margin.bottom}}" stroke="#6b7280" stroke-width="1.2"></line>
          <line x1="${{margin.left}}" y1="${{margin.top}}" x2="${{margin.left}}" y2="${{height - margin.bottom}}" stroke="#6b7280" stroke-width="1.2"></line>
          ${{yTicks.map((ratio) => {{
            const y = margin.top + innerHeight - (ratio * innerHeight);
            const value = Math.round(max * ratio);
            return `
              <line x1="${{margin.left}}" y1="${{y.toFixed(2)}}" x2="${{width - margin.right}}" y2="${{y.toFixed(2)}}" stroke="#ebe3d4" stroke-width="1"></line>
              <text x="${{margin.left - 10}}" y="${{(y + 4).toFixed(2)}}" text-anchor="end" font-size="12" fill="#52606d">${{fmtNumber(value)}}</text>
            `;
          }}).join('')}}
          ${{tickIndexes.map((index) => {{
            const x = xForYear(index);
            const year = years[index];
            return `
              <line x1="${{x.toFixed(2)}}" y1="${{height - margin.bottom}}" x2="${{x.toFixed(2)}}" y2="${{height - margin.bottom + 6}}" stroke="#9ca3af" stroke-width="1"></line>
              <text x="${{x.toFixed(2)}}" y="${{height - margin.bottom + 22}}" text-anchor="middle" font-size="12" fill="#52606d">${{year}}</text>
            `;
          }}).join('')}}
          ${{series.map((line) => `<polyline fill="none" stroke="${{line.color}}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" points="${{line.points}}"></polyline>`).join('')}}
        </svg>
        <div class="timeline-legend">${{series.map((line) => `<span class="timeline-item"><span class="timeline-swatch" style="background:${{line.color}}"></span>${{line.theme}} (${{fmtNumber(line.total)}})</span>`).join('')}}</div>
        <div class="insight">This timeline tracks annual article counts for the most recurrent recovered themes. Read it as a temporal profile: a theme can be historically foundational, steadily persistent, episodic, or clearly expanding in recent years. The final year shown is <strong>${{years[years.length - 1]}}</strong>.</div>
      `;
    }};
    const interpretationGuide = (summary) => `
      <div class="insight"><strong>Publication year:</strong> read mean and median together. If both are recent, the classified literature is concentrated in the last decade; if the mean is much older than the median, the corpus has a historical tail.</div>
      <div class="insight"><strong>References per article:</strong> the median is usually the best "typical article" indicator. The mean becomes larger when a smaller set of review-style or theory-heavy papers cite very extensively.</div>
      <div class="insight"><strong>Keywords and themes:</strong> keywords tell us what authors and indexers declared; recovered themes are a curated analytical layer used to compare labels, years, and trajectories.</div>
      <div class="insight"><strong>Cited authors:</strong> use the heatmaps and top cited-author views to identify intellectual anchors, but always check that the parser is surfacing actual people rather than books or journals.</div>
      <div class="insight"><strong>Network previews:</strong> they are bounded summaries for readability. The CSV and GraphML exports preserve the larger graph for deeper analysis.</div>
    `;

    const summary = payload.summary;
    const themeCoverage = payload.theme_assignment_rows || [];
    document.getElementById('overview').innerHTML = `
      <div class="grid-2">
        <div>
          <h2>Overview</h2>
          <div class="cards">
            <div class="card"><strong>Total articles</strong><div class="big-number">${{fmtNumber(summary.total_articles)}}</div></div>
            <div class="card"><strong>Articles with references</strong><div class="big-number">${{fmtNumber(summary.articles_with_references)}}</div></div>
            <div class="card"><strong>Parse success rate</strong><div class="big-number">${{fmtPct(summary.reference_parse_success_rate)}}</div></div>
            <div class="card"><strong>Dominant label</strong><div>${{summary.dominant_label}}</div></div>
          </div>
          <div class="cards" style="margin-top:12px">
            <div class="card"><strong>Keyword coverage</strong><div>${{fmtNumber(summary.articles_with_keywords)}} articles</div></div>
            <div class="card"><strong>Theme coverage</strong><div>${{fmtNumber(summary.theme_assignment_summary?.articles_with_themes || 0)}} articles</div></div>
            <div class="card"><strong>Cited authors tracked</strong><div>${{fmtNumber(summary.total_cited_authors)}}</div></div>
            <div class="card"><strong>Corpus authors tracked</strong><div>${{fmtNumber(summary.total_corpus_authors)}}</div></div>
          </div>
          <div class="kpi-note">Theme coverage prioritizes explicit themes first, then author keywords, index keywords, and TF-IDF only as a last fallback.</div>
        </div>
        <div>
          <h2>Label distribution</h2>
          ${{bars(payload.label_distribution, 'label')}}
        </div>
      </div>
      <div class="grid-2" style="margin-top:18px">
        <div>
          <h2>Top themes</h2>
          ${{bars(payload.top_themes.slice(0, 10).map((row) => ({{...row, count: row.count}})), 'theme')}}
        </div>
        <div>
          <h2>Theme coverage sources</h2>
          ${{bars(themeCoverage.map((row) => ({{...row, count: row.article_count}})), 'source')}}
        </div>
      </div>
      <div class="grid-2" style="margin-top:18px">
        <div>
          <h2>Top keywords</h2>
          ${{bars(payload.top_keywords.slice(0, 10), 'keyword')}}
        </div>
        <div>
          <h2>Top cited authors</h2>
          ${{bars(payload.top_cited_authors.slice(0, 10).map((row) => ({{...row, count: row.article_citation_coverage}})), 'author_display')}}
        </div>
      </div>
    `;
    document.getElementById('descriptiveProfiles').innerHTML = metricCards(payload.descriptive_profiles || []) +
      (payload.descriptive_profiles || []).map((row) => metricInsight(row.metric, row, summary.total_articles)).join('');
    const profilesByMetric = profileByMetric(payload.descriptive_profiles || []);
    document.getElementById('distributionCharts').innerHTML = [
      distributionBlock('Publication year', payload.distribution_snapshots?.publication_year || [], profilesByMetric['Publication year']),
      distributionBlock('References per article', payload.distribution_snapshots?.references_per_article || [], profilesByMetric['References per article']),
      distributionBlock('Authors per article', payload.distribution_snapshots?.authors_per_article || [], profilesByMetric['Authors per article']),
      distributionBlock('Keywords per article', payload.distribution_snapshots?.keywords_per_article || [], profilesByMetric['Keywords per article']),
      distributionBlock('Abstract words', payload.distribution_snapshots?.abstract_word_count || [], profilesByMetric['Abstract words']),
    ].join('');
    document.getElementById('themeLabelHeatmap').innerHTML = heatmap(payload.theme_label_heatmap, 'Theme ');
    document.getElementById('authorLabelHeatmap').innerHTML = heatmap(payload.author_label_heatmap, 'Author ');
    document.getElementById('labelYearHeatmap').innerHTML = heatmap(payload.label_year_heatmap, 'Year ');
    document.getElementById('themeTimeline').innerHTML = themeTimeline(payload.theme_year_timeline || []);
    document.getElementById('interpretationGuide').innerHTML = interpretationGuide(summary);

    const authorMode = document.getElementById('authorMode');
    const authorSearch = document.getElementById('authorSearch');
    const renderAuthors = () => {{
      const baseRows = authorMode.value === 'corpus' ? payload.corpus_author_rows : payload.cited_author_rows;
      const rows = filterRows(baseRows, authorSearch.value, ['author_display']);
      const columns = authorMode.value === 'corpus'
        ? ['author_display', 'corpus_author_count', 'article_count']
        : ['author_display', 'cited_author_count', 'article_citation_coverage'];
      const note = authorMode.value === 'cited'
        ? `<div class="kpi-note">Showing a ranked interactive slice of ${{fmtNumber(payload.cited_author_rows.length)}} cited authors out of ${{fmtNumber(payload.cited_author_total_rows)}} total. Use the full cited-author CSV export for exhaustive inspection.</div>`
        : `<div class="kpi-note">Showing all ${{fmtNumber(payload.corpus_author_rows.length)}} corpus authors available in this bundle.</div>`;
      document.getElementById('authorsTable').innerHTML = note + table(rows, columns, {{ maxHeight: 980 }});
    }};
    authorMode.addEventListener('change', renderAuthors);
    authorSearch.addEventListener('input', renderAuthors);
    renderAuthors();
    document.getElementById('authorLabelTable').innerHTML = table(payload.author_label_rows, ['cited_author_display', 'label_name', 'article_count', 'share_within_author']);
    document.getElementById('authorThemeTable').innerHTML = table(payload.author_theme_rows, ['cited_author_display', 'theme', 'article_count', 'share_within_author']);

    const keywordSource = document.getElementById('keywordSource');
    const keywordSearch = document.getElementById('keywordSearch');
    const keywordSources = [...new Set(payload.keyword_label_rows.map((row) => row.keyword_source))];
    keywordSources.unshift('ALL');
    keywordSource.innerHTML = keywordSources.map((source) => `<option value="${{source}}">${{source}}</option>`).join('');
    const renderKeywords = () => {{
      const source = keywordSource.value;
      const sourceRows = source === 'ALL'
        ? payload.keyword_label_rows
        : payload.keyword_label_rows.filter((row) => row.keyword_source === source);
      const rows = filterRows(sourceRows, keywordSearch.value, ['keyword', 'label_name']);
      document.getElementById('keywordsTable').innerHTML = table(rows, ['keyword', 'keyword_source', 'label_name', 'article_count']);
      document.getElementById('themesTable').innerHTML = payload.theme_label_rows.length
        ? table(payload.theme_label_rows, ['theme', 'label_name', 'article_count', 'share_within_theme'])
        : '<div class="empty">No theme assignments were recovered for this run, even after keyword and TF-IDF fallback.</div>';
    }};
    keywordSource.addEventListener('change', renderKeywords);
    keywordSearch.addEventListener('input', renderKeywords);
    renderKeywords();

    const network = payload.network_summary;
    if (!network) {{
      document.getElementById('networkSummary').innerHTML = '<div class="empty"><strong>Network outputs are not available for this run.</strong><p class="muted">The offline analytics package still includes the full deterministic report, frequency tables, and matrix views. Networks can be generated later with a bounded network configuration.</p></div>';
    }} else {{
      const previews = network.preview_files || {{}};
      document.getElementById('networkSummary').innerHTML = `
        <div class="cards">
          <div class="card"><strong>Co-citation edges</strong><div class="big-number">${{fmtNumber(network.cocitation_edges)}}</div></div>
          <div class="card"><strong>Co-author edges</strong><div class="big-number">${{fmtNumber(network.coauthor_edges)}}</div></div>
          <div class="card"><strong>Coupling edges</strong><div class="big-number">${{fmtNumber(network.bibliographic_coupling_edges)}}</div></div>
          <div class="card"><strong>Author coverage filter</strong><div>>= ${{fmtNumber(network.min_cited_author_article_coverage)}} citing articles</div></div>
        </div>
        <p class="kpi-note">These previews are intentionally bounded for readability. Labels are prioritized for the most central nodes, while the underlying CSV and GraphML exports preserve the larger graph.</p>
        <ul>
          <li><a href="../networks/${{previews.co_citation_authors_html || ''}}">Co-citation preview</a></li>
          <li><a href="../networks/${{previews.co_author_html || ''}}">Co-author preview</a></li>
          <li><a href="../networks/${{previews.bibliographic_coupling_html || ''}}">Bibliographic coupling preview</a></li>
        </ul>
      `;
    }}
  </script>
</body>
</html>
"""


def _write_data_exports(
    bibliometric_artifacts: BibliometricArtifacts,
    *,
    data_dir: Path,
    network_artifacts: NetworkArtifacts | None,
) -> None:
    (data_dir / "descriptive_stats.json").write_text(
        json.dumps(bibliometric_artifacts.descriptive_stats, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    for name, frame in (
        ("author_frequency.csv", bibliometric_artifacts.corpus_author_frequency),
        ("cited_author_frequency.csv", bibliometric_artifacts.cited_author_frequency),
        ("author_label_matrix.csv", bibliometric_artifacts.author_label_matrix),
        ("author_theme_matrix.csv", bibliometric_artifacts.author_theme_matrix),
        ("theme_label_matrix.csv", bibliometric_artifacts.theme_label_matrix),
        ("keyword_label_matrix.csv", bibliometric_artifacts.keyword_label_matrix),
    ):
        frame.to_csv(data_dir / name, index=False, encoding="utf-8")
    if network_artifacts is not None:
        network_artifacts.nodes.to_csv(data_dir / "network_nodes.csv", index=False, encoding="utf-8")
        network_artifacts.edges.to_csv(data_dir / "network_edges.csv", index=False, encoding="utf-8")


def _relative_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())
