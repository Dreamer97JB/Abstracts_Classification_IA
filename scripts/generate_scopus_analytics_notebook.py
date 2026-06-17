from __future__ import annotations

import argparse
import json
from pathlib import Path
from textwrap import dedent


def _md_cell(source: str) -> dict[str, object]:
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": dedent(source).strip("\n").splitlines(keepends=True),
    }


def _code_cell(source: str) -> dict[str, object]:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": dedent(source).strip("\n").splitlines(keepends=True),
    }


def build_notebook() -> dict[str, object]:
    cells: list[dict[str, object]] = [
        _md_cell(
            """
            # Scopus analytics notebook

            This notebook is the presentation-first analytical report for the classified Scopus corpus.
            It is designed to surface the most useful descriptive, thematic, author, citation, and network
            patterns for research interpretation, while keeping every chart interactive.

            **How to use it**
            - Run the notebook from top to bottom.
            - Hover over charts for exact values.
            - Use the Plotly legend to isolate labels or themes.
            - Open the exported CSV files when you need exhaustive inspection beyond the curated views.
            """
        ),
        _md_cell(
            """
            ## 0. Setup and artifact loading

            The notebook reads the already generated artifacts under `reports/analytics/scopus_live/`.
            That lets us focus on interpretation and visualization instead of re-running the full pipeline.
            """
        ),
        _code_cell(
            """
            from __future__ import annotations

            import json
            import math
            import warnings
            from pathlib import Path

            import networkx as nx
            import numpy as np
            import pandas as pd
            import plotly.express as px
            import plotly.graph_objects as go
            from plotly.subplots import make_subplots

            try:
                from IPython.display import HTML, Markdown, display
            except ImportError:
                def display(value):
                    print(value)

                def HTML(value):
                    return value

                def Markdown(value):
                    return value

            warnings.filterwarnings("ignore")
            pd.set_option("display.max_columns", 120)
            pd.set_option("display.max_colwidth", 120)
            pd.set_option("display.float_format", lambda value: f"{value:,.3f}")


            def find_project_root(start: Path | None = None) -> Path:
                candidate = (start or Path.cwd()).resolve()
                for current in (candidate, *candidate.parents):
                    if (current / ".git").exists() or (current / "requirements" / "base.txt").exists():
                        return current
                raise FileNotFoundError("Could not locate the project root from the notebook working directory.")


            PROJECT_ROOT = find_project_root()
            ARTIFACT_DIR = PROJECT_ROOT / "reports" / "analytics" / "scopus_live"
            TABLES_DIR = ARTIFACT_DIR / "tables"
            NETWORKS_DIR = ARTIFACT_DIR / "networks"

            stats = json.loads((ARTIFACT_DIR / "descriptive_stats.json").read_text(encoding="utf-8"))
            network_summary = json.loads((NETWORKS_DIR / "network_summary.json").read_text(encoding="utf-8"))

            article_df = pd.read_csv(TABLES_DIR / "client_results_enriched.csv", low_memory=False)
            author_frequency = pd.read_csv(TABLES_DIR / "author_frequency.csv")
            cited_author_frequency = pd.read_csv(TABLES_DIR / "cited_author_frequency.csv")
            author_label_matrix = pd.read_csv(TABLES_DIR / "author_label_matrix.csv")
            author_theme_matrix = pd.read_csv(TABLES_DIR / "author_theme_matrix.csv")
            theme_label_matrix = pd.read_csv(TABLES_DIR / "theme_label_matrix.csv")
            keyword_label_matrix = pd.read_csv(TABLES_DIR / "keyword_label_matrix.csv")
            parsed_references = pd.read_csv(TABLES_DIR / "parsed_references.csv", low_memory=False)
            network_nodes = pd.read_csv(NETWORKS_DIR / "network_nodes.csv", low_memory=False)
            network_edges = pd.read_csv(NETWORKS_DIR / "network_edges.csv", low_memory=False)

            LABEL_ORDER = list(stats["labels_distribution"].keys())
            LABEL_COLOR_MAP = {
                label: color
                for label, color in zip(
                    LABEL_ORDER,
                    px.colors.qualitative.Safe + px.colors.qualitative.Vivid + px.colors.qualitative.Bold,
                )
            }
            THEME_COLORS = px.colors.qualitative.Bold

            px.defaults.template = "plotly_white"
            px.defaults.color_discrete_sequence = px.colors.qualitative.Safe


            def split_pipe(value: object) -> list[str]:
                if value is None or (isinstance(value, float) and np.isnan(value)):
                    return []
                text = str(value).strip()
                if not text:
                    return []
                return [part.strip() for part in text.split("|") if part.strip()]


            def union_keyword_count(row: pd.Series) -> int:
                return len(set(split_pipe(row.get("author_keywords_normalized"))) | set(split_pipe(row.get("index_keywords_normalized"))))


            def is_meaningful_theme(term: str) -> bool:
                normalized = str(term).strip().lower()
                generic_terms = {
                    "social", "science", "knowledge", "research", "studies", "new", "history", "policy",
                    "education", "design", "network", "model", "work", "culture", "practice", "students",
                    "medical", "academic", "problems", "challenges", "individual", "focus", "need",
                    "political", "environmental", "management", "process", "impact", "technological",
                    "sociology", "sciences", "scientific knowledge", "scientific careers",
                }
                if not normalized or normalized in generic_terms:
                    return False
                if len(normalized) < 4:
                    return False
                if sum(character.isalpha() for character in normalized) < 4:
                    return False
                if normalized.isdigit():
                    return False
                return True


            def is_plausible_author(name: object) -> bool:
                text = str(name or "").strip()
                lowered = text.lower()
                blocked_fragments = (
                    "science in action",
                    "knowledge",
                    "society",
                    "technology studies",
                    "planning d society",
                    "reassembling the social",
                    "how to follow scientists",
                )
                if not text:
                    return False
                if any(fragment in lowered for fragment in blocked_fragments):
                    return False
                if any(character.isdigit() for character in text):
                    return False
                if sum(character.isalpha() for character in text) < 3:
                    return False
                tokens = [token for token in text.replace(".", " ").split() if token]
                if len(tokens) > 6:
                    return False
                return True


            def kpi_cards(items: list[tuple[str, str, str]]) -> None:
                cards = []
                for label, value, note in items:
                    cards.append(
                        f'''
                        <div style="padding:16px 18px;border:1px solid #d9d2c3;border-radius:16px;background:linear-gradient(180deg,#fffdf9,#f7f2e8);box-shadow:0 8px 24px rgba(16,24,40,.06)">
                          <div style="font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:#5b6b78;margin-bottom:8px">{label}</div>
                          <div style="font-size:28px;font-weight:700;color:#12343b;margin-bottom:6px">{value}</div>
                          <div style="font-size:13px;color:#52606d">{note}</div>
                        </div>
                        '''
                    )
                html = (
                    '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px;margin:8px 0 18px">'
                    + "".join(cards)
                    + "</div>"
                )
                display(HTML(html))


            def build_ranked_bar(frame: pd.DataFrame, x: str, y: str, color: str | None = None, title: str = "") -> go.Figure:
                fig = px.bar(
                    frame,
                    x=x,
                    y=y,
                    color=color,
                    orientation="h",
                    text=x,
                    title=title,
                    color_discrete_map=LABEL_COLOR_MAP if color else None,
                )
                fig.update_traces(textposition="outside", cliponaxis=False)
                fig.update_layout(height=max(420, 28 * len(frame) + 140), showlegend=bool(color))
                return fig


            def display_note(text: str) -> None:
                display(
                    HTML(
                        f'<div style="margin:12px 0 20px;padding:14px 16px;border:1px solid #d9d2c3;'
                        f'border-radius:14px;background:#faf6ee;color:#29434e">{text}</div>'
                    )
                )


            article_df["publication_year"] = pd.to_numeric(article_df["year"], errors="coerce")
            article_df["references_count"] = pd.to_numeric(article_df["references_count"], errors="coerce").fillna(0)
            article_df["abstract_word_count"] = pd.to_numeric(article_df["abstract_word_count"], errors="coerce").fillna(0)
            article_df["authors_per_article"] = article_df["corpus_authors_normalized"].map(lambda value: len(split_pipe(value)))
            article_df["keywords_per_article"] = article_df.apply(union_keyword_count, axis=1)
            article_df["author_keyword_count"] = article_df["author_keywords_normalized"].map(lambda value: len(split_pipe(value)))
            article_df["index_keyword_count"] = article_df["index_keywords_normalized"].map(lambda value: len(split_pipe(value)))
            article_df["label_name"] = article_df["label_name"].fillna(article_df["predicted_label_canonica"])

            label_counts = (
                article_df["label_name"]
                .value_counts(dropna=False)
                .rename_axis("label_name")
                .reset_index(name="article_count")
            )
            label_counts["share"] = label_counts["article_count"] / len(article_df)

            yearly_label_counts = (
                article_df.dropna(subset=["publication_year", "label_name"])
                .groupby(["publication_year", "label_name"], as_index=False)
                .agg(article_count=("record_id", "nunique"))
                .sort_values(["publication_year", "label_name"])
            )

            theme_rows = []
            for row in article_df[["record_id", "publication_year", "label_name", "themes_normalized"]].to_dict(orient="records"):
                for theme in split_pipe(row["themes_normalized"]):
                    theme_rows.append(
                        {
                            "record_id": row["record_id"],
                            "publication_year": row["publication_year"],
                            "label_name": row["label_name"],
                            "theme": theme,
                        }
                    )
            theme_df = pd.DataFrame(theme_rows)
            if not theme_df.empty:
                theme_df = theme_df[theme_df["theme"].map(is_meaningful_theme)]

            curated_theme_counts = (
                theme_df.groupby("theme", as_index=False)
                .agg(article_count=("record_id", "nunique"))
                .sort_values(["article_count", "theme"], ascending=[False, True])
            )
            curated_theme_counts = curated_theme_counts[curated_theme_counts["article_count"] >= 8].reset_index(drop=True)
            curated_top_themes = curated_theme_counts.head(15).copy()
            curated_timeline_themes = curated_theme_counts.head(8)["theme"].tolist()

            keyword_counts = (
                keyword_label_matrix.groupby(["keyword", "keyword_source"], as_index=False)
                .agg(article_count=("article_count", "sum"))
                .sort_values(["article_count", "keyword"], ascending=[False, True])
            )
            keyword_counts = keyword_counts[
                keyword_counts["keyword"].map(lambda value: isinstance(value, str) and len(value.strip()) >= 4)
            ].reset_index(drop=True)

            top_corpus_authors = author_frequency.sort_values(
                ["article_count", "author_display"], ascending=[False, True]
            ).head(30)
            top_cited_authors = cited_author_frequency[
                cited_author_frequency["author_display"].map(is_plausible_author)
            ].sort_values(
                ["article_citation_coverage", "cited_author_count"], ascending=[False, False]
            ).head(30)

            descriptive_profile_rows = []
            label_map = {
                "publication_year": "Publication year",
                "authors_per_article": "Authors per article",
                "references_per_article": "References per article",
                "keywords_per_article": "Keywords per article",
                "abstract_word_count": "Abstract words",
            }
            for key, values in stats["numeric_descriptives"].items():
                descriptive_profile_rows.append({"metric": label_map.get(key, key), **values})
            descriptive_profiles = pd.DataFrame(descriptive_profile_rows)

            print(f"Project root: {PROJECT_ROOT}")
            print(f"Artifact directory: {ARTIFACT_DIR}")
            print(f"Articles loaded: {len(article_df):,}")
            print(f"Parsed references loaded: {len(parsed_references):,}")
            """
        ),
        _md_cell(
            """
            ## 1. Executive summary

            This first section frames the classified corpus at a glance: scale, metadata coverage, reference parsing quality,
            and the balance across the official labels.
            """
        ),
        _code_cell(
            """
            dominant_label = max(stats["labels_distribution"], key=stats["labels_distribution"].get)
            dominant_theme = max(stats["themes_distribution"], key=stats["themes_distribution"].get)
            theme_coverage = stats["theme_assignment_summary"]["articles_with_themes"] / stats["total_articles"]

            kpi_cards(
                [
                    ("Total articles", f"{stats['total_articles']:,}", "Classified Scopus articles available in this analytical package."),
                    ("Reference parse success", f"{stats['reference_parse_success_rate']:.1%}", "Structured references recovered from the raw cited-reference strings."),
                    ("Keyword coverage", f"{stats['articles_with_keywords']:,}", "Articles with at least one author or index keyword."),
                    ("Theme coverage", f"{stats['theme_assignment_summary']['articles_with_themes']:,}", f"{theme_coverage:.1%} of the corpus has an explicit or derived theme."),
                    ("Corpus authors", f"{stats['total_corpus_authors']:,}", "Distinct authors appearing as article authors in the classified corpus."),
                    ("Cited authors", f"{stats['total_cited_authors']:,}", "Distinct cited-author signatures recovered from parsed references."),
                ]
            )

            overview_fig = px.bar(
                label_counts.sort_values("article_count"),
                x="article_count",
                y="label_name",
                orientation="h",
                color="label_name",
                color_discrete_map=LABEL_COLOR_MAP,
                text=label_counts.sort_values("article_count")["share"].map(lambda value: f"{value:.1%}"),
                title="Official label distribution across the classified Scopus corpus",
            )
            overview_fig.update_traces(textposition="outside", cliponaxis=False)
            overview_fig.update_layout(height=520, showlegend=False, xaxis_title="Articles", yaxis_title="")
            overview_fig.show()

            display_note(
                f"<strong>Reading this overview:</strong> the dominant official label is <strong>{dominant_label}</strong>. "
                f"The most frequent recovered theme in the raw theme layer is <strong>{dominant_theme}</strong>, but later sections "
                "apply additional curation so that thematic visuals privilege clearer and more interpretable themes."
            )
            """
        ),
        _md_cell(
            """
            ## 2. Descriptive profiles

            The goal here is not only to list summary statistics, but to explain what a *typical* article looks like
            in terms of publication timing, collaboration, references, keywords, and abstract length.
            """
        ),
        _code_cell(
            """
            display(
                descriptive_profiles.style
                .format(
                    {
                        "count": "{:,.0f}",
                        "mean": "{:,.3f}",
                        "median": "{:,.0f}",
                        "mode": "{:,.0f}",
                        "min": "{:,.0f}",
                        "max": "{:,.0f}",
                    }
                )
                .hide(axis="index")
                .set_properties(**{"text-align": "left"})
                .set_table_styles(
                    [
                        {"selector": "th", "props": [("background-color", "#efe7d8"), ("text-align", "left")]},
                        {"selector": "td", "props": [("padding", "8px 10px")]},
                    ]
                )
            )

            profile_notes = [
                f"Publication year centers on a mean of {descriptive_profiles.loc[descriptive_profiles['metric'] == 'Publication year', 'mean'].iloc[0]:.1f}, with a median of {descriptive_profiles.loc[descriptive_profiles['metric'] == 'Publication year', 'median'].iloc[0]:.0f}.",
                f"The typical article is written by {descriptive_profiles.loc[descriptive_profiles['metric'] == 'Authors per article', 'median'].iloc[0]:.0f} author(s), with a mean collaboration size of {descriptive_profiles.loc[descriptive_profiles['metric'] == 'Authors per article', 'mean'].iloc[0]:.2f}.",
                f"The median bibliography size is {descriptive_profiles.loc[descriptive_profiles['metric'] == 'References per article', 'median'].iloc[0]:.0f} references, which is usually more informative than the mean when long review-like papers are present.",
                f"The median abstract length is {descriptive_profiles.loc[descriptive_profiles['metric'] == 'Abstract words', 'median'].iloc[0]:.0f} words, indicating the common reporting style across the corpus.",
            ]
            display(Markdown("### Interpretation\\n" + "\\n".join(f"- {note}" for note in profile_notes)))
            """
        ),
        _code_cell(
            """
            year_counts = (
                article_df.dropna(subset=["publication_year"])
                .groupby("publication_year", as_index=False)
                .agg(article_count=("record_id", "nunique"))
                .sort_values("publication_year")
            )
            year_counts["rolling_mean"] = year_counts["article_count"].rolling(window=5, min_periods=1).mean()

            fig_year = go.Figure()
            fig_year.add_bar(
                x=year_counts["publication_year"],
                y=year_counts["article_count"],
                marker_color="#0f766e",
                name="Articles",
                hovertemplate="Year %{x}<br>Articles %{y:,}<extra></extra>",
            )
            fig_year.add_trace(
                go.Scatter(
                    x=year_counts["publication_year"],
                    y=year_counts["rolling_mean"],
                    mode="lines",
                    line={"color": "#d97706", "width": 3},
                    name="5-year rolling mean",
                    hovertemplate="Rolling mean %{y:.1f}<extra></extra>",
                )
            )
            fig_year.update_layout(
                title="Publication timeline of the classified corpus",
                height=460,
                xaxis_title="Publication year",
                yaxis_title="Articles",
            )
            fig_year.show()

            display_note(
                "The bars show annual output, while the rolling line smooths short-term noise. "
                "This helps separate structural growth from isolated spikes."
            )
            """
        ),
        _code_cell(
            """
            label_timeline_fig = px.area(
                yearly_label_counts.sort_values(["publication_year", "label_name"]),
                x="publication_year",
                y="article_count",
                color="label_name",
                color_discrete_map=LABEL_COLOR_MAP,
                title="Evolution of the official labels over publication years",
            )
            label_timeline_fig.update_layout(height=520, xaxis_title="Publication year", yaxis_title="Articles")
            label_timeline_fig.show()

            year_label_pivot = (
                yearly_label_counts.pivot_table(
                    index="label_name",
                    columns="publication_year",
                    values="article_count",
                    fill_value=0,
                )
                .reindex(index=LABEL_ORDER)
            )
            heatmap_fig = px.imshow(
                year_label_pivot,
                aspect="auto",
                color_continuous_scale="YlGnBu",
                title="Heatmap of label concentration by publication year",
                labels={"x": "Publication year", "y": "Official label", "color": "Articles"},
            )
            heatmap_fig.update_layout(height=420)
            heatmap_fig.show()
            """
        ),
        _code_cell(
            """
            distribution_specs = [
                ("Authors per article", "authors_per_article", 14, "#0f766e", "Exact collaboration size distribution."),
                ("Keywords per article", "keywords_per_article", 18, "#1d4ed8", "A zero here normally means missing keyword metadata, not thematic emptiness."),
                ("References per article", "references_count", int(article_df["references_count"].quantile(0.99)), "#b45309", "The long right tail is expected in review-like or theory-heavy papers."),
                ("Abstract word count", "abstract_word_count", int(article_df["abstract_word_count"].quantile(0.99)), "#7c3aed", "The distribution highlights how standardized or heterogeneous abstract-writing conventions are."),
            ]

            for title, column, cap, color, note in distribution_specs:
                if column in {"authors_per_article", "keywords_per_article"}:
                    dist = (
                        article_df[column]
                        .value_counts()
                        .sort_index()
                        .reset_index()
                    )
                    dist.columns = [column, "article_count"]
                    fig = px.bar(
                        dist[dist[column] <= cap],
                        x=column,
                        y="article_count",
                        title=title,
                        labels={column: title, "article_count": "Articles"},
                    )
                    fig.update_traces(marker_color=color, hovertemplate=f"{title}: %{{x}}<br>Articles: %{{y:,}}<extra></extra>")
                else:
                    fig = px.histogram(
                        article_df[article_df[column] <= cap],
                        x=column,
                        nbins=35,
                        marginal="box",
                        title=title,
                        labels={column: title, "count": "Articles"},
                    )
                    fig.update_traces(marker_color=color)
                fig.update_layout(height=420)
                fig.show()
                display_note(note)
            """
        ),
        _code_cell(
            """
            clipped_references = article_df.assign(
                references_count_clipped=article_df["references_count"].clip(upper=article_df["references_count"].quantile(0.99))
            )
            violin_fig = px.violin(
                clipped_references,
                x="label_name",
                y="references_count_clipped",
                color="label_name",
                color_discrete_map=LABEL_COLOR_MAP,
                box=True,
                points=False,
                title="Reference-count profiles by official label (clipped at the 99th percentile)",
            )
            violin_fig.update_layout(height=540, xaxis_title="", yaxis_title="References per article")
            violin_fig.show()

            abstract_box_fig = px.box(
                article_df,
                x="label_name",
                y="abstract_word_count",
                color="label_name",
                color_discrete_map=LABEL_COLOR_MAP,
                points=False,
                title="Abstract-length profiles by official label",
            )
            abstract_box_fig.update_layout(height=540, xaxis_title="", yaxis_title="Abstract words")
            abstract_box_fig.show()
            """
        ),
        _md_cell(
            """
            ## 3. Themes, labels, and thematic trajectories

            The raw recovered-theme layer is broad and noisy, so this section privileges themes that are both
            frequent and interpretable. The goal is to understand what the corpus is *about*, not only how large it is.
            """
        ),
        _code_cell(
            """
            display(
                curated_top_themes.style
                .format({"article_count": "{:,.0f}"})
                .hide(axis="index")
                .set_caption("Curated recovered themes with at least eight articles and non-generic wording.")
            )

            theme_bar = px.bar(
                curated_top_themes.sort_values("article_count"),
                x="article_count",
                y="theme",
                orientation="h",
                title="Most recurrent curated recovered themes",
                labels={"article_count": "Articles", "theme": "Theme"},
                color="article_count",
                color_continuous_scale="Tealgrn",
            )
            theme_bar.update_layout(height=560, coloraxis_showscale=False)
            theme_bar.show()

            display_note(
                "These themes come from the hydrated theme layer, which prioritizes explicit themes first, then keyword-derived themes, "
                "and only uses TF-IDF fallback when richer thematic fields are absent."
            )
            """
        ),
        _code_cell(
            """
            curated_theme_names = curated_top_themes["theme"].tolist()
            theme_label_curated = (
                theme_label_matrix[theme_label_matrix["theme"].isin(curated_theme_names)]
                .groupby(["theme", "label_name"], as_index=False)
                .agg(article_count=("article_count", "sum"))
            )
            theme_label_heatmap = (
                theme_label_curated.pivot_table(
                    index="theme",
                    columns="label_name",
                    values="article_count",
                    fill_value=0,
                )
                .reindex(columns=LABEL_ORDER, fill_value=0)
                .reindex(index=curated_theme_names, fill_value=0)
            )
            fig_theme_label = px.imshow(
                theme_label_heatmap,
                aspect="auto",
                color_continuous_scale="YlGnBu",
                title="Theme x official label heatmap",
                labels={"x": "Official label", "y": "Recovered theme", "color": "Articles"},
            )
            fig_theme_label.update_layout(height=620)
            fig_theme_label.show()
            """
        ),
        _code_cell(
            """
            theme_timeline = (
                theme_df[theme_df["theme"].isin(curated_timeline_themes)]
                .dropna(subset=["publication_year"])
                .groupby(["publication_year", "theme"], as_index=False)
                .agg(article_count=("record_id", "nunique"))
                .sort_values(["publication_year", "theme"])
            )

            fig_theme_timeline = px.area(
                theme_timeline,
                x="publication_year",
                y="article_count",
                color="theme",
                title="Temporal evolution of the most interpretable recurrent themes",
                color_discrete_sequence=THEME_COLORS,
            )
            fig_theme_timeline.update_layout(height=520, xaxis_title="Publication year", yaxis_title="Articles")
            fig_theme_timeline.show()

            theme_share_by_label = (
                theme_label_curated.groupby("theme", as_index=False)
                .apply(lambda frame: frame.assign(share=frame["article_count"] / frame["article_count"].sum()))
                .reset_index(drop=True)
            )
            dominant_theme_per_label = (
                theme_share_by_label.sort_values(["label_name", "share"], ascending=[True, False])
                .groupby("label_name", as_index=False)
                .head(3)
            )
            display(
                dominant_theme_per_label[["label_name", "theme", "article_count", "share"]]
                .style.format({"article_count": "{:,.0f}", "share": "{:.1%}"})
                .hide(axis="index")
                .set_caption("Top recovered themes inside each official label.")
            )
            """
        ),
        _md_cell(
            """
            ## 4. Keywords and metadata richness

            Keywords are not only topical descriptors. They also tell us how richly the corpus is self-described
            by authors and by indexing systems.
            """
        ),
        _code_cell(
            """
            keyword_coverage = pd.DataFrame(
                {
                    "source": ["Author keywords", "Index keywords", "Any keyword metadata"],
                    "articles": [
                        int((article_df["author_keyword_count"] > 0).sum()),
                        int((article_df["index_keyword_count"] > 0).sum()),
                        int((article_df["keywords_per_article"] > 0).sum()),
                    ],
                }
            )
            keyword_coverage["share"] = keyword_coverage["articles"] / len(article_df)

            fig_keyword_coverage = px.bar(
                keyword_coverage,
                x="articles",
                y="source",
                orientation="h",
                text=keyword_coverage["share"].map(lambda value: f"{value:.1%}"),
                title="Keyword coverage by metadata source",
                labels={"articles": "Articles", "source": ""},
                color="source",
            )
            fig_keyword_coverage.update_traces(textposition="outside", cliponaxis=False)
            fig_keyword_coverage.update_layout(height=360, showlegend=False)
            fig_keyword_coverage.show()

            top_keywords_by_source = (
                keyword_counts.groupby("keyword_source", group_keys=False)
                .head(15)
                .copy()
            )
            fig_keywords = px.bar(
                top_keywords_by_source.sort_values("article_count"),
                x="article_count",
                y="keyword",
                color="keyword_source",
                orientation="h",
                facet_col="keyword_source",
                facet_col_wrap=1,
                title="Top keywords by source",
                labels={"article_count": "Articles", "keyword": "Keyword", "keyword_source": "Source"},
            )
            fig_keywords.update_layout(height=900)
            fig_keywords.for_each_annotation(lambda annotation: annotation.update(text=annotation.text.split("=")[-1]))
            fig_keywords.show()
            """
        ),
        _md_cell(
            """
            ## 5. Authors, cited authors, and intellectual anchors

            This section distinguishes between two levels:
            - **Corpus authors**: the people who wrote the articles in the classified corpus.
            - **Cited authors**: the people most often invoked in the reference lists.

            Together they help answer who is producing the corpus and which intellectual figures anchor it.
            """
        ),
        _code_cell(
            """
            corpus_authors_fig = px.bar(
                top_corpus_authors.sort_values("article_count"),
                x="article_count",
                y="author_display",
                orientation="h",
                title="Most prolific corpus authors in the classified Scopus set",
                labels={"article_count": "Articles", "author_display": "Author"},
                color="article_count",
                color_continuous_scale="Teal",
            )
            corpus_authors_fig.update_layout(height=820, coloraxis_showscale=False)
            corpus_authors_fig.show()

            cited_authors_fig = px.bar(
                top_cited_authors.sort_values("article_citation_coverage"),
                x="article_citation_coverage",
                y="author_display",
                orientation="h",
                title="Most cited authors by article coverage after display curation",
                labels={"article_citation_coverage": "Articles citing the author", "author_display": "Cited author"},
                color="article_citation_coverage",
                color_continuous_scale="Sunsetdark",
            )
            cited_authors_fig.update_layout(height=820, coloraxis_showscale=False)
            cited_authors_fig.show()
            """
        ),
        _code_cell(
            """
            display(
                top_corpus_authors[["author_display", "corpus_author_count", "article_count"]]
                .style.format({"corpus_author_count": "{:,.0f}", "article_count": "{:,.0f}"})
                .hide(axis="index")
                .set_caption("Top corpus authors. The full table remains available in author_frequency.csv.")
            )

            display(
                top_cited_authors[["author_display", "cited_author_count", "article_citation_coverage"]]
                .style.format({"cited_author_count": "{:,.0f}", "article_citation_coverage": "{:,.0f}"})
                .hide(axis="index")
                .set_caption("Top cited authors after filtering obviously implausible display strings. The full universe remains in cited_author_frequency.csv.")
            )
            """
        ),
        _code_cell(
            """
            curated_author_names = top_cited_authors.head(15)["author_display"].tolist()
            author_label_curated = (
                author_label_matrix[author_label_matrix["cited_author_display"].isin(curated_author_names)]
                .groupby(["cited_author_display", "label_name"], as_index=False)
                .agg(article_count=("article_count", "sum"))
            )
            author_label_heatmap = (
                author_label_curated.pivot_table(
                    index="cited_author_display",
                    columns="label_name",
                    values="article_count",
                    fill_value=0,
                )
                .reindex(columns=LABEL_ORDER, fill_value=0)
                .reindex(index=curated_author_names, fill_value=0)
            )
            author_heatmap_fig = px.imshow(
                author_label_heatmap,
                aspect="auto",
                color_continuous_scale="YlOrBr",
                title="Cited author x official label heatmap",
                labels={"x": "Official label", "y": "Cited author", "color": "Articles"},
            )
            author_heatmap_fig.update_layout(height=700)
            author_heatmap_fig.show()
            """
        ),
        _md_cell(
            """
            ## 6. Networks

            The notebook focuses on interpretable subgraphs rather than rendering the full network all at once.
            The full HTML and GraphML exports remain available in the `networks/` directory for deeper external exploration.
            """
        ),
        _code_cell(
            """
            kpi_cards(
                [
                    ("Co-author edges", f"{network_summary['coauthor_edges']:,}", "Observed co-authorship links in the exported network."),
                    ("Co-citation edges", f"{network_summary['cocitation_edges']:,}", "Pairs of cited authors co-mentioned across the corpus."),
                    ("Bibliographic coupling edges", f"{network_summary['bibliographic_coupling_edges']:,}", "Article-to-article coupling links based on shared references."),
                    ("Author coverage threshold", f"{network_summary['min_cited_author_article_coverage']:,}", "Minimum number of citing articles required for cited-author inclusion."),
                ]
            )


            def build_network_figure(
                nodes: pd.DataFrame,
                edges: pd.DataFrame,
                *,
                node_type: str,
                edge_type: str,
                top_n: int,
                title: str,
            ) -> go.Figure | None:
                node_subset = (
                    nodes[nodes["node_type"] == node_type]
                    .sort_values(["weighted_degree", "degree", "count"], ascending=[False, False, False])
                    .head(top_n)
                    .copy()
                )
                node_ids = set(node_subset["node_id"])
                edge_subset = edges[
                    (edges["edge_type"] == edge_type)
                    & (edges["source"].isin(node_ids))
                    & (edges["target"].isin(node_ids))
                ].copy()
                if edge_subset.empty:
                    return None

                graph = nx.Graph()
                for row in node_subset.to_dict(orient="records"):
                    graph.add_node(row["node_id"], **row)
                for row in edge_subset.sort_values("weight", ascending=False).head(max(top_n * 5, 120)).to_dict(orient="records"):
                    graph.add_edge(row["source"], row["target"], weight=row["weight"])

                if graph.number_of_edges() == 0:
                    return None

                largest_component = max(nx.connected_components(graph), key=len)
                graph = graph.subgraph(largest_component).copy()
                positions = nx.spring_layout(graph, seed=42, k=0.55 / math.sqrt(max(graph.number_of_nodes(), 1)))

                edge_x = []
                edge_y = []
                for source, target in graph.edges():
                    x0, y0 = positions[source]
                    x1, y1 = positions[target]
                    edge_x.extend([x0, x1, None])
                    edge_y.extend([y0, y1, None])

                edge_trace = go.Scatter(
                    x=edge_x,
                    y=edge_y,
                    mode="lines",
                    line={"width": 0.6, "color": "rgba(107,114,128,0.35)"},
                    hoverinfo="skip",
                )

                node_x = []
                node_y = []
                node_size = []
                node_color = []
                node_text = []
                node_labels = []
                for node_id, payload in graph.nodes(data=True):
                    x, y = positions[node_id]
                    node_x.append(x)
                    node_y.append(y)
                    node_size.append(max(10, min(42, 10 + payload.get("weighted_degree", 0) ** 0.35 * 5)))
                    node_color.append(payload.get("community_id", -1) if not pd.isna(payload.get("community_id")) else -1)
                    node_text.append(
                        "<br>".join(
                            [
                                f"<b>{payload.get('display_name', node_id)}</b>",
                                f"Degree: {payload.get('degree', 0):,}",
                                f"Weighted degree: {payload.get('weighted_degree', 0):,.0f}",
                                f"Dominant label: {payload.get('dominant_label_name', 'n/a')}",
                            ]
                        )
                    )
                    node_labels.append(payload.get("display_name", node_id))

                node_trace = go.Scatter(
                    x=node_x,
                    y=node_y,
                    mode="markers+text",
                    text=node_labels,
                    textposition="top center",
                    hovertext=node_text,
                    hoverinfo="text",
                    marker={
                        "size": node_size,
                        "color": node_color,
                        "colorscale": "Viridis",
                        "showscale": False,
                        "line": {"width": 1, "color": "rgba(15,23,42,0.35)"},
                        "opacity": 0.92,
                    },
                )

                fig = go.Figure(data=[edge_trace, node_trace])
                fig.update_layout(
                    title=title,
                    height=760,
                    margin={"l": 20, "r": 20, "t": 60, "b": 20},
                    xaxis={"showgrid": False, "zeroline": False, "showticklabels": False},
                    yaxis={"showgrid": False, "zeroline": False, "showticklabels": False},
                )
                return fig


            coauthor_network_fig = build_network_figure(
                network_nodes,
                network_edges,
                node_type="CORPUS_AUTHOR",
                edge_type="CO_AUTHOR",
                top_n=80,
                title="Co-author network preview built directly inside the notebook",
            )
            if coauthor_network_fig is not None:
                coauthor_network_fig.show()
            else:
                display_note("No co-author notebook preview could be built from the exported network slice.")

            cocited_network_fig = build_network_figure(
                network_nodes,
                network_edges,
                node_type="CITED_AUTHOR",
                edge_type="CO_CITED_AUTHOR",
                top_n=90,
                title="Co-cited author network preview built directly inside the notebook",
            )
            if cocited_network_fig is not None:
                cocited_network_fig.show()
            else:
                display_note("No co-cited author notebook preview could be built from the exported network slice.")

            display(
                Markdown(
                    "Full network exports available at:\\n"
                    f"- `{(NETWORKS_DIR / 'co_author.html').relative_to(PROJECT_ROOT).as_posix()}`\\n"
                    f"- `{(NETWORKS_DIR / 'co_citation_authors.html').relative_to(PROJECT_ROOT).as_posix()}`\\n"
                    f"- `{(NETWORKS_DIR / 'bibliographic_coupling.html').relative_to(PROJECT_ROOT).as_posix()}`"
                )
            )
            """
        ),
        _md_cell(
            """
            ## 7. Data quality and interpretation boundaries

            Every analytical product simplifies reality. This section keeps the notebook honest about what the reader should and should not infer too quickly.
            """
        ),
        _code_cell(
            """
            quality_notes = [
                f"{stats['total_references_raw'] - stats['total_references_parsed']:,} references were not parsed into structured form, so cited-author evidence is strong but not exhaustive.",
                f"{stats['total_articles'] - stats['articles_with_keywords']:,} articles lack keyword metadata, so thematic recovery sometimes depends on TF-IDF fallback rather than explicit descriptors.",
                "Recovered themes are analytically useful, but they should be treated as a corpus-level lens rather than a perfect human-curated ontology.",
                "Cited-author displays were already improved in the pipeline and additionally filtered here for presentation, but exhaustive author disambiguation is still a separate curation problem.",
                "Network visualizations shown in this notebook are curated subgraphs for readability, not the full network universe.",
            ]
            display(Markdown("\\n".join(f"- {note}" for note in quality_notes)))
            """
        ),
        _md_cell(
            """
            ## 8. Key takeaways

            This final section compresses the notebook into a set of presentation-ready talking points.
            """
        ),
        _code_cell(
            """
            latest_year = int(article_df["publication_year"].dropna().max())
            median_year = int(descriptive_profiles.loc[descriptive_profiles["metric"] == "Publication year", "median"].iloc[0])
            median_authors = int(descriptive_profiles.loc[descriptive_profiles["metric"] == "Authors per article", "median"].iloc[0])
            median_references = int(descriptive_profiles.loc[descriptive_profiles["metric"] == "References per article", "median"].iloc[0])
            median_abstract_words = int(descriptive_profiles.loc[descriptive_profiles["metric"] == "Abstract words", "median"].iloc[0])
            top_theme_text = ", ".join(curated_top_themes.head(5)["theme"].tolist())
            top_cited_text = ", ".join(top_cited_authors.head(5)["author_display"].tolist())

            conclusion_points = [
                f"The classified Scopus corpus contains {stats['total_articles']:,} articles, with a publication center of gravity around {median_year} and coverage extending through {latest_year}.",
                f"The dominant official label is {dominant_label}, indicating that the corpus leans most strongly toward that epistemic position.",
                f"A typical article is authored by {median_authors} person(s), cites about {median_references} references, and uses an abstract of roughly {median_abstract_words} words.",
                f"The most interpretable recurrent themes include {top_theme_text}, which together provide a more readable thematic map than the raw unfiltered theme inventory.",
                f"The cited-author landscape is anchored by figures such as {top_cited_text}, which helps identify the intellectual scaffolding of the classified literature.",
                "For presentation purposes, this notebook should be treated as the main analytical interface, while the CSV, GraphML, and HTML exports remain the deep-dive appendix.",
            ]
            display(Markdown("### Presentation-ready synthesis\\n" + "\\n".join(f"- {point}" for point in conclusion_points)))
            """
        ),
    ]

    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "version": "3.11",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the presentation-first Scopus analytics notebook.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/analytics/scopus_live/scopus_analytics_report.ipynb"),
        help="Notebook output path.",
    )
    args = parser.parse_args()

    notebook = build_notebook()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(notebook, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Notebook written to {args.output.resolve()}")


if __name__ == "__main__":
    main()
