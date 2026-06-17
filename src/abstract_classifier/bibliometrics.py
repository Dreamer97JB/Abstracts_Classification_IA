from __future__ import annotations

import json
import re
import tomllib
import unicodedata
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

from .normalization import normalize_year
from .taxonomy import ROOT, resolve_project_path

DEFAULT_BIBLIOMETRICS_CONFIG = Path("configs/bibliometrics.toml")
_DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.IGNORECASE)
_YEAR_RE = re.compile(r"\b(18\d{2}|19\d{2}|20\d{2}|21\d{2})\b")
_LEADING_REF_MARKER_RE = re.compile(r"^\s*(?:\[\d+\]|\d+\.)\s*")
_WHITESPACE_RE = re.compile(r"\s+")
_PARENS_RE = re.compile(r"\([^)]*\)")
_NON_AUTHOR_RE = re.compile(r"[^A-Za-zÀ-ÿ0-9,.\- '&]+")
_NON_KEY_RE = re.compile(r"[^a-z0-9 ]+")
_SURNAME_INITIALS_RE = re.compile(
    r"[A-ZÀ-ÿ][A-Za-zÀ-ÿ'`\-]+(?:\s+[A-ZÀ-ÿ][A-Za-zÀ-ÿ'`\-]+)*,\s*(?:[A-Z]\.\s*){1,4}"
)
_INITIALS_SURNAME_RE = re.compile(
    r"(?:[A-Z]\.\s*){1,4}[A-ZÀ-ÿ][A-Za-zÀ-ÿ'`\-]+(?:\s+[A-ZÀ-ÿ][A-Za-zÀ-ÿ'`\-]+)*"
)
_SURNAME_TRAILING_INITIALS_RE = re.compile(
    r"\b[A-ZÀ-ÿ][A-Za-zÀ-ÿ'`\-]+(?:\s+[A-ZÀ-ÿ][A-Za-zÀ-ÿ'`\-]+)*\s+(?:[A-Z](?:\.[A-Z]?\.?)*|[A-Z]{1,3})\b"
)
_SPLIT_NUMBERED_REFS_RE = re.compile(r"(?=(?:\[\d+\]|\d+\.)\s)")
_GENERIC_THEME_TERMS = {
    "article",
    "article",
    "adult",
    "adults",
    "book",
    "books",
    "chapter",
    "chapters",
    "editorial",
    "female",
    "females",
    "human",
    "humans",
    "male",
    "males",
    "paper",
    "papers",
    "review",
    "reviews",
    "scientific",
}


@dataclass(frozen=True)
class BibliometricColumnAliases:
    record_id: tuple[str, ...]
    title: tuple[str, ...]
    abstract: tuple[str, ...]
    authors: tuple[str, ...]
    author_keywords: tuple[str, ...]
    index_keywords: tuple[str, ...]
    references: tuple[str, ...]
    doi: tuple[str, ...]
    year: tuple[str, ...]
    label_id: tuple[str, ...]
    label_name: tuple[str, ...]
    theme: tuple[str, ...]
    themes: tuple[str, ...]


@dataclass(frozen=True)
class BibliometricReferenceSettings:
    min_author_token_length: int
    min_parse_confidence: str


@dataclass(frozen=True)
class BibliometricThemeSettings:
    min_term_frequency: int
    max_terms: int
    ngram_min: int
    ngram_max: int
    tfidf_terms_per_record: int


@dataclass(frozen=True)
class BibliometricNetworkSettings:
    min_edge_weight: int
    max_nodes_html: int
    compute_betweenness: bool
    community_detection: bool
    min_cited_author_article_coverage: int
    max_cited_authors_per_article: int
    max_signature_record_frequency: int
    min_bibliographic_coupling_weight: int


@dataclass(frozen=True)
class BibliometricReportSettings:
    top_n_authors: int
    top_n_keywords: int
    top_n_themes: int
    top_n_matrix_rows: int


@dataclass(frozen=True)
class BibliometricConfig:
    version: str
    config_path: Path
    default_input_artifact_path: Path
    default_output_root: Path
    columns: BibliometricColumnAliases
    references: BibliometricReferenceSettings
    themes: BibliometricThemeSettings
    networks: BibliometricNetworkSettings
    report: BibliometricReportSettings


@dataclass(frozen=True)
class BibliometricRecord:
    record_id: str
    title: str
    abstract: str
    year: int | None
    doi: str | None
    corpus_authors: tuple[str, ...]
    author_keywords: tuple[str, ...]
    index_keywords: tuple[str, ...]
    references_raw: tuple[str, ...]
    label_id: str | None
    label_name: str | None
    themes: tuple[str, ...]


@dataclass(frozen=True)
class ParsedReference:
    record_id: str
    reference_index: int
    reference_raw: str
    style_guess: str
    first_author: str | None
    year: int | None
    title_fragment: str | None
    doi: str | None
    authors: tuple[str, ...]
    parse_confidence: str


@dataclass(frozen=True)
class AuthorMention:
    record_id: str
    author_key: str
    author_display: str
    mention_source: str
    label_id: str | None
    theme: str | None


@dataclass(frozen=True)
class BibliometricArtifacts:
    enriched_rows: pd.DataFrame
    parsed_references: pd.DataFrame
    corpus_author_frequency: pd.DataFrame
    cited_author_frequency: pd.DataFrame
    author_label_matrix: pd.DataFrame
    author_theme_matrix: pd.DataFrame
    theme_label_matrix: pd.DataFrame
    keyword_label_matrix: pd.DataFrame
    descriptive_stats: dict[str, object]


@dataclass(frozen=True)
class BibliometricRunArtifacts:
    output_dir: Path
    descriptive_stats_path: Path
    enriched_rows_path: Path
    parsed_references_path: Path
    corpus_author_frequency_path: Path
    cited_author_frequency_path: Path
    author_label_matrix_path: Path
    author_theme_matrix_path: Path
    theme_label_matrix_path: Path
    keyword_label_matrix_path: Path
    manifest_path: Path


def load_bibliometric_config(
    path: str | Path = DEFAULT_BIBLIOMETRICS_CONFIG,
    *,
    root: Path | None = None,
) -> BibliometricConfig:
    project_root = root or ROOT
    config_path = resolve_project_path(path, root=project_root)
    data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    columns = data.get("columns", {})
    reference_data = data.get("references", {})
    theme_data = data.get("themes", {})
    network_data = data.get("networks", {})
    report_data = data.get("report", {})

    return BibliometricConfig(
        version=str(data.get("version", "")),
        config_path=config_path,
        default_input_artifact_path=resolve_project_path(
            data.get("default_input_artifact", "reports/phase10/scopus_only_predict/predictions.csv"),
            root=project_root,
        ),
        default_output_root=resolve_project_path(
            data.get("default_output_root", "reports/analytics/scopus"),
            root=project_root,
        ),
        columns=BibliometricColumnAliases(
            record_id=_tuple_aliases(columns.get("record_id", ["record_id"])),
            title=_tuple_aliases(columns.get("title", ["title", "Title", "Article Title", "Título"])),
            abstract=_tuple_aliases(columns.get("abstract", ["abstract", "Abstract", "Resumen"])),
            authors=_tuple_aliases(columns.get("authors", ["authors", "Authors", "Author full names", "Autores"])),
            author_keywords=_tuple_aliases(
                columns.get("author_keywords", ["author_keywords", "Author Keywords", "Keywords"])
            ),
            index_keywords=_tuple_aliases(
                columns.get("index_keywords", ["index_keywords", "Index Keywords", "Indexed Keywords"])
            ),
            references=_tuple_aliases(
                columns.get("references", ["references", "References", "Cited References", "Bibliography", "Referencias"])
            ),
            doi=_tuple_aliases(columns.get("doi", ["doi", "DOI"])),
            year=_tuple_aliases(columns.get("year", ["year", "Year", "Publication Year", "Año"])),
            label_id=_tuple_aliases(
                columns.get("label_id", ["predicted_canonical_id", "canonical_id", "label_id"])
            ),
            label_name=_tuple_aliases(
                columns.get("label_name", ["predicted_label_canonica", "label_canonica", "label_name"])
            ),
            theme=_tuple_aliases(columns.get("theme", ["theme", "primary_theme"])),
            themes=_tuple_aliases(columns.get("themes", ["themes", "theme_labels"])),
        ),
        references=BibliometricReferenceSettings(
            min_author_token_length=int(reference_data.get("min_author_token_length", 3)),
            min_parse_confidence=str(reference_data.get("min_parse_confidence", "LOW")).strip() or "LOW",
        ),
        themes=BibliometricThemeSettings(
            min_term_frequency=int(theme_data.get("min_term_frequency", 2)),
            max_terms=int(theme_data.get("max_terms", 200)),
            ngram_min=int(theme_data.get("ngram_min", 1)),
            ngram_max=int(theme_data.get("ngram_max", 3)),
            tfidf_terms_per_record=int(theme_data.get("tfidf_terms_per_record", 3)),
        ),
        networks=BibliometricNetworkSettings(
            min_edge_weight=int(network_data.get("min_edge_weight", 1)),
            max_nodes_html=int(network_data.get("max_nodes_html", 150)),
            compute_betweenness=bool(network_data.get("compute_betweenness", True)),
            community_detection=bool(network_data.get("community_detection", True)),
            min_cited_author_article_coverage=int(network_data.get("min_cited_author_article_coverage", 1)),
            max_cited_authors_per_article=int(network_data.get("max_cited_authors_per_article", 50)),
            max_signature_record_frequency=int(network_data.get("max_signature_record_frequency", 0)),
            min_bibliographic_coupling_weight=int(network_data.get("min_bibliographic_coupling_weight", 1)),
        ),
        report=BibliometricReportSettings(
            top_n_authors=int(report_data.get("top_n_authors", 15)),
            top_n_keywords=int(report_data.get("top_n_keywords", 15)),
            top_n_themes=int(report_data.get("top_n_themes", 15)),
            top_n_matrix_rows=int(report_data.get("top_n_matrix_rows", 20)),
        ),
    )


def resolve_bibliometric_columns(
    frame: pd.DataFrame,
    config: BibliometricConfig,
) -> dict[str, str | None]:
    columns = {
        "record_id": _resolve_first_column(frame.columns, config.columns.record_id, required=True),
        "title": _resolve_first_column(frame.columns, config.columns.title, required=False),
        "abstract": _resolve_first_column(frame.columns, config.columns.abstract, required=False),
        "authors": _resolve_first_column(frame.columns, config.columns.authors, required=True),
        "author_keywords": _resolve_first_column(frame.columns, config.columns.author_keywords, required=False),
        "index_keywords": _resolve_first_column(frame.columns, config.columns.index_keywords, required=False),
        "references": _resolve_first_column(frame.columns, config.columns.references, required=True),
        "doi": _resolve_first_column(frame.columns, config.columns.doi, required=False),
        "year": _resolve_first_column(frame.columns, config.columns.year, required=False),
        "label_id": _resolve_first_column(frame.columns, config.columns.label_id, required=False),
        "label_name": _resolve_first_column(frame.columns, config.columns.label_name, required=False),
        "theme": _resolve_first_column(frame.columns, config.columns.theme, required=False),
        "themes": _resolve_first_column(frame.columns, config.columns.themes, required=False),
    }

    missing_groups: list[str] = []
    if columns["title"] is None and columns["abstract"] is None:
        missing_groups.append("title_or_abstract")
    if columns["label_id"] is None and columns["label_name"] is None:
        missing_groups.append("label_id_or_label_name")
    if missing_groups:
        raise ValueError(f"Input artifact is missing required columns: {missing_groups}")
    return columns


def build_bibliometric_records(
    frame: pd.DataFrame,
    *,
    columns: dict[str, str | None],
) -> list[BibliometricRecord]:
    records: list[BibliometricRecord] = []
    for row in frame.to_dict(orient="records"):
        record_id = _clean_text(row.get(columns["record_id"])) or ""
        title = _clean_text(row.get(columns["title"])) or ""
        abstract = _clean_text(row.get(columns["abstract"])) or ""
        doi = _clean_text(row.get(columns["doi"]))
        year = normalize_year(row.get(columns["year"])) if columns["year"] else None
        label_id = _clean_text(row.get(columns["label_id"]))
        label_name = _clean_text(row.get(columns["label_name"]))
        corpus_authors = tuple(dict.fromkeys(_split_authors(_clean_text(row.get(columns["authors"])) or "")))
        author_keywords = tuple(
            dict.fromkeys(_split_terms(_clean_text(row.get(columns["author_keywords"])) or ""))
        )
        index_keywords = tuple(
            dict.fromkeys(_split_terms(_clean_text(row.get(columns["index_keywords"])) or ""))
        )
        references_raw = split_references(_clean_text(row.get(columns["references"])) or "")
        themes = _extract_record_themes(row=row, columns=columns)
        records.append(
            BibliometricRecord(
                record_id=record_id,
                title=title,
                abstract=abstract,
                year=year,
                doi=doi,
                corpus_authors=corpus_authors,
                author_keywords=author_keywords,
                index_keywords=index_keywords,
                references_raw=references_raw,
                label_id=label_id,
                label_name=label_name,
                themes=themes,
            )
        )
    return records


def hydrate_record_themes(
    records: list[BibliometricRecord],
    *,
    config: BibliometricConfig,
) -> tuple[list[BibliometricRecord], dict[str, int]]:
    derived_tfidf_terms = _build_record_tfidf_terms(records, config=config)
    hydrated: list[BibliometricRecord] = []
    summary = {
        "articles_with_explicit_themes": 0,
        "articles_with_derived_keyword_themes": 0,
        "articles_with_derived_tfidf_themes": 0,
        "articles_without_themes": 0,
    }
    max_themes = max(1, config.themes.tfidf_terms_per_record)

    for record in records:
        explicit_themes = _normalize_themes(record.themes, limit=max_themes)
        if explicit_themes:
            summary["articles_with_explicit_themes"] += 1
            hydrated.append(replace(record, themes=explicit_themes))
            continue

        keyword_themes = _derive_keyword_themes(record, limit=max_themes)
        if keyword_themes:
            summary["articles_with_derived_keyword_themes"] += 1
            hydrated.append(replace(record, themes=keyword_themes))
            continue

        tfidf_themes = derived_tfidf_terms.get(record.record_id, ())
        if tfidf_themes:
            summary["articles_with_derived_tfidf_themes"] += 1
            hydrated.append(replace(record, themes=tfidf_themes))
            continue

        summary["articles_without_themes"] += 1
        hydrated.append(record)

    summary["articles_with_themes"] = (
        summary["articles_with_explicit_themes"]
        + summary["articles_with_derived_keyword_themes"]
        + summary["articles_with_derived_tfidf_themes"]
    )
    return hydrated, summary


def split_references(raw_value: str) -> tuple[str, ...]:
    text = _clean_text(raw_value) or ""
    if not text:
        return ()
    lines = [line.strip() for line in text.replace("\r", "\n").split("\n") if line.strip()]
    if len(lines) > 1:
        return tuple(lines)
    numbered_matches = list(_SPLIT_NUMBERED_REFS_RE.finditer(text))
    if len(numbered_matches) > 1:
        parts = [part.strip(" ;") for part in _SPLIT_NUMBERED_REFS_RE.split(text) if part.strip(" ;")]
        return tuple(parts)
    if ";" in text:
        parts = [part.strip() for part in re.split(r"\s*;\s*", text) if part.strip()]
        return tuple(parts)
    return (text,)


def guess_reference_style(reference: str) -> str:
    text = _LEADING_REF_MARKER_RE.sub("", reference.strip())
    if re.match(r"^(?:\[\d+\]|\d+\.)", reference.strip()):
        return "IEEE_LIKE"
    if re.search(r"\(\s*(18\d{2}|19\d{2}|20\d{2}|21\d{2})\s*\)", text):
        return "APA_LIKE"
    if re.search(r"\b(18\d{2}|19\d{2}|20\d{2}|21\d{2})\b", text) and re.match(
        r"^[A-ZÀ-ÿ][A-Za-zÀ-ÿ'`\-]+(?:\s+[A-Z]\.)?", text
    ):
        return "VANCOUVER_LIKE"
    return "UNKNOWN"


def extract_doi(reference: str) -> str | None:
    match = _DOI_RE.search(reference)
    if match is None:
        return None
    return match.group(0).rstrip(".,;)")


def extract_year(reference: str) -> int | None:
    current_year = date.today().year
    for match in _YEAR_RE.finditer(reference):
        year = int(match.group(1))
        if 1800 <= year <= current_year:
            return year
    return None


def extract_author_segment(reference: str, style_guess: str, year: int | None) -> str:
    text = _LEADING_REF_MARKER_RE.sub("", reference.strip())
    if style_guess == "IEEE_LIKE" and '"' in text:
        text = text.split('"', 1)[0].rstrip(" ,.")
        return text
    if year is not None:
        year_match = re.search(rf"[\[(]?\b{year}\b[\])]?", text)
        if year_match is not None:
            return text[: year_match.start()].rstrip(" ,.;")
    if "." in text:
        return text.split(".", 1)[0].strip()
    return text


def split_reference_authors(author_segment: str) -> tuple[str, ...]:
    segment = _clean_author_text(author_segment)
    if not segment:
        return ()

    candidates = [normalize_author_name(value) for value in _SURNAME_INITIALS_RE.findall(segment)]
    if candidates:
        return tuple(dict.fromkeys(value for value in candidates if _is_plausible_author_candidate(value)))

    candidates = [normalize_author_name(value) for value in _INITIALS_SURNAME_RE.findall(segment)]
    if candidates:
        return tuple(dict.fromkeys(value for value in candidates if _is_plausible_author_candidate(value)))

    candidates = []
    for match in _SURNAME_TRAILING_INITIALS_RE.finditer(segment):
        end = match.end()
        next_character = segment[end:end + 1]
        if next_character not in {"", ".", ",", ";", "&", "("}:
            continue
        candidates.append(normalize_author_name(match.group(0)))
    if candidates:
        return tuple(dict.fromkeys(value for value in candidates if _is_plausible_author_candidate(value)))

    fallback_parts = re.split(r"\s*(?:&| and |;)\s*", segment)
    normalized_parts = [
        normalize_author_name(part)
        for part in fallback_parts
        if _is_plausible_author_candidate(normalize_author_name(part))
    ]
    return tuple(dict.fromkeys(normalized_parts))


def normalize_author_name(author: str) -> str:
    text = _clean_author_text(author)
    text = text.strip(" -,")
    return text


def parse_references(
    records: list[BibliometricRecord],
    *,
    config: BibliometricConfig,
) -> pd.DataFrame:
    parsed_records: list[dict[str, object]] = []
    min_tokens = config.references.min_author_token_length
    for record in records:
        for reference_index, reference_raw in enumerate(record.references_raw, start=1):
            style_guess = guess_reference_style(reference_raw)
            doi = extract_doi(reference_raw)
            year = extract_year(reference_raw)
            author_segment = extract_author_segment(reference_raw, style_guess, year)
            authors = tuple(
                author
                for author in split_reference_authors(author_segment)
                if _author_has_signal(author, min_token_length=min_tokens)
            )
            title_fragment = _extract_title_fragment(reference_raw, author_segment, year)
            parse_confidence = _assign_parse_confidence(authors=authors, year=year, doi=doi, title_fragment=title_fragment)
            parsed = ParsedReference(
                record_id=record.record_id,
                reference_index=reference_index,
                reference_raw=reference_raw,
                style_guess=style_guess,
                first_author=authors[0] if authors else None,
                year=year,
                title_fragment=title_fragment,
                doi=doi,
                authors=authors,
                parse_confidence=parse_confidence,
            )
            parsed_records.append(
                {
                    "record_id": parsed.record_id,
                    "reference_index": parsed.reference_index,
                    "reference_raw": parsed.reference_raw,
                    "style_guess": parsed.style_guess,
                    "first_author": parsed.first_author or "",
                    "year": parsed.year,
                    "title_fragment": parsed.title_fragment or "",
                    "doi": parsed.doi or "",
                    "authors_raw": author_segment,
                    "authors_normalized": " | ".join(parsed.authors),
                    "parse_confidence": parsed.parse_confidence,
                }
            )
    return pd.DataFrame.from_records(
        parsed_records,
        columns=[
            "record_id",
            "reference_index",
            "reference_raw",
            "style_guess",
            "first_author",
            "year",
            "title_fragment",
            "doi",
            "authors_raw",
            "authors_normalized",
            "parse_confidence",
        ],
    )


def extract_cited_authors(
    parsed_references: pd.DataFrame,
    *,
    records: list[BibliometricRecord],
) -> pd.DataFrame:
    lookup = {record.record_id: record for record in records}
    mentions: list[dict[str, object]] = []
    for row in parsed_references.to_dict(orient="records"):
        record = lookup[str(row["record_id"])]
        authors = _split_display_values(str(row.get("authors_normalized", "")))
        for author in authors:
            mentions.append(
                AuthorMention(
                    record_id=record.record_id,
                    author_key=_author_key(author),
                    author_display=author,
                    mention_source="CITED_AUTHOR",
                    label_id=record.label_id,
                    theme=None,
                ).__dict__
            )
    return pd.DataFrame.from_records(
        mentions,
        columns=["record_id", "author_key", "author_display", "mention_source", "label_id", "theme"],
    )


def build_author_frequency(
    author_mentions: pd.DataFrame,
    *,
    mention_source: str,
) -> pd.DataFrame:
    if author_mentions.empty:
        if mention_source == "CORPUS_AUTHOR":
            return pd.DataFrame(columns=["author_key", "author_display", "corpus_author_count", "article_count"])
        return pd.DataFrame(columns=["author_key", "author_display", "cited_author_count", "article_citation_coverage"])

    source_rows = author_mentions.loc[
        author_mentions["mention_source"].astype(str) == mention_source
    ].copy()
    if source_rows.empty:
        return build_author_frequency(pd.DataFrame(), mention_source=mention_source)

    grouped = (
        source_rows.groupby(["author_key", "author_display"], dropna=False)
        .agg(mention_count=("record_id", "size"), article_count=("record_id", "nunique"))
        .reset_index()
        .sort_values(by=["article_count", "mention_count", "author_display"], ascending=[False, False, True])
        .reset_index(drop=True)
    )
    if mention_source == "CORPUS_AUTHOR":
        return grouped.rename(columns={"mention_count": "corpus_author_count"})
    return grouped.rename(
        columns={"mention_count": "cited_author_count", "article_count": "article_citation_coverage"}
    )


def build_author_label_matrix(
    cited_author_mentions: pd.DataFrame,
    *,
    records: list[BibliometricRecord],
) -> pd.DataFrame:
    empty = pd.DataFrame(
        columns=[
            "cited_author_key",
            "cited_author_display",
            "label_id",
            "label_name",
            "article_count",
            "mention_count",
            "share_within_author",
            "share_within_label",
        ]
    )
    if cited_author_mentions.empty:
        return empty

    label_lookup = {record.record_id: (record.label_id or "", record.label_name or "") for record in records}
    rows = cited_author_mentions.copy()
    rows["label_id"] = rows["record_id"].map(lambda value: label_lookup[str(value)][0])
    rows["label_name"] = rows["record_id"].map(lambda value: label_lookup[str(value)][1])
    rows = rows.loc[rows["label_id"].astype(str).str.strip() != ""].copy()
    if rows.empty:
        return empty

    grouped = (
        rows.groupby(["author_key", "author_display", "label_id", "label_name"], dropna=False)
        .agg(article_count=("record_id", "nunique"), mention_count=("record_id", "size"))
        .reset_index()
    )
    author_totals = grouped.groupby("author_key")["article_count"].sum().to_dict()
    label_totals = _label_totals(records)
    grouped["share_within_author"] = grouped.apply(
        lambda row: _safe_ratio(row["article_count"], author_totals.get(row["author_key"], 0)),
        axis=1,
    )
    grouped["share_within_label"] = grouped.apply(
        lambda row: _safe_ratio(row["article_count"], label_totals.get(str(row["label_id"]), 0)),
        axis=1,
    )
    return grouped.rename(
        columns={"author_key": "cited_author_key", "author_display": "cited_author_display"}
    ).sort_values(
        by=["cited_author_display", "article_count", "mention_count", "label_name"],
        ascending=[True, False, False, True],
    ).reset_index(drop=True)


def build_author_theme_matrix(
    cited_author_mentions: pd.DataFrame,
    *,
    records: list[BibliometricRecord],
) -> pd.DataFrame:
    empty = pd.DataFrame(
        columns=[
            "cited_author_key",
            "cited_author_display",
            "theme",
            "article_count",
            "mention_count",
            "share_within_author",
        ]
    )
    if cited_author_mentions.empty:
        return empty

    theme_map = {record.record_id: record.themes for record in records}
    rows: list[dict[str, object]] = []
    for mention in cited_author_mentions.to_dict(orient="records"):
        themes = theme_map.get(str(mention["record_id"]), ())
        for theme in themes:
            rows.append(
                {
                    "author_key": mention["author_key"],
                    "author_display": mention["author_display"],
                    "record_id": mention["record_id"],
                    "theme": theme,
                }
            )
    if not rows:
        return empty

    frame = pd.DataFrame.from_records(rows)
    grouped = (
        frame.groupby(["author_key", "author_display", "theme"], dropna=False)
        .agg(article_count=("record_id", "nunique"), mention_count=("record_id", "size"))
        .reset_index()
    )
    author_totals = grouped.groupby("author_key")["article_count"].sum().to_dict()
    grouped["share_within_author"] = grouped.apply(
        lambda row: _safe_ratio(row["article_count"], author_totals.get(row["author_key"], 0)),
        axis=1,
    )
    return grouped.rename(
        columns={"author_key": "cited_author_key", "author_display": "cited_author_display"}
    ).sort_values(
        by=["cited_author_display", "article_count", "mention_count", "theme"],
        ascending=[True, False, False, True],
    ).reset_index(drop=True)


def build_theme_label_matrix(records: list[BibliometricRecord]) -> pd.DataFrame:
    empty = pd.DataFrame(
        columns=["theme", "label_id", "label_name", "article_count", "share_within_theme", "share_within_label"]
    )
    rows: list[dict[str, object]] = []
    for record in records:
        if not record.label_id:
            continue
        for theme in record.themes:
            rows.append(
                {
                    "record_id": record.record_id,
                    "theme": theme,
                    "label_id": record.label_id,
                    "label_name": record.label_name or "",
                }
            )
    if not rows:
        return empty

    frame = pd.DataFrame.from_records(rows).drop_duplicates(subset=["record_id", "theme", "label_id"])
    grouped = (
        frame.groupby(["theme", "label_id", "label_name"], dropna=False)
        .agg(article_count=("record_id", "nunique"))
        .reset_index()
    )
    theme_totals = grouped.groupby("theme")["article_count"].sum().to_dict()
    label_totals = _label_totals(records)
    grouped["share_within_theme"] = grouped.apply(
        lambda row: _safe_ratio(row["article_count"], theme_totals.get(str(row["theme"]), 0)),
        axis=1,
    )
    grouped["share_within_label"] = grouped.apply(
        lambda row: _safe_ratio(row["article_count"], label_totals.get(str(row["label_id"]), 0)),
        axis=1,
    )
    return grouped.sort_values(by=["theme", "article_count", "label_name"], ascending=[True, False, True]).reset_index(
        drop=True
    )


def build_keyword_label_matrix(
    records: list[BibliometricRecord],
    *,
    config: BibliometricConfig,
) -> pd.DataFrame:
    empty = pd.DataFrame(
        columns=["keyword", "keyword_source", "label_id", "label_name", "article_count", "keyword_count", "share_within_keyword"]
    )
    keyword_rows = _build_keyword_rows(records, config=config)
    if keyword_rows.empty:
        return empty

    grouped = (
        keyword_rows.groupby(["keyword", "keyword_source", "label_id", "label_name"], dropna=False)
        .agg(article_count=("record_id", "nunique"), keyword_count=("record_id", "size"))
        .reset_index()
    )
    keyword_totals = grouped.groupby(["keyword", "keyword_source"])["article_count"].sum().to_dict()
    grouped["share_within_keyword"] = grouped.apply(
        lambda row: _safe_ratio(
            row["article_count"],
            keyword_totals.get((str(row["keyword"]), str(row["keyword_source"])), 0),
        ),
        axis=1,
    )
    return grouped.sort_values(
        by=["keyword_source", "keyword", "article_count", "label_name"],
        ascending=[True, True, False, True],
    ).reset_index(drop=True)


def _derive_keyword_themes(
    record: BibliometricRecord,
    *,
    limit: int,
) -> tuple[str, ...]:
    for candidate_terms in (record.author_keywords, record.index_keywords):
        normalized = _normalize_themes(candidate_terms, limit=limit)
        if normalized:
            return normalized
    return ()


def _normalize_themes(values: tuple[str, ...], *, limit: int) -> tuple[str, ...]:
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        theme = _normalize_term(value)
        if not _is_meaningful_theme(theme) or theme in seen:
            continue
        seen.add(theme)
        normalized.append(theme)
        if len(normalized) >= limit:
            break
    return tuple(normalized)


def build_descriptive_stats(
    records: list[BibliometricRecord],
    *,
    parsed_references: pd.DataFrame,
    corpus_author_frequency: pd.DataFrame,
    cited_author_frequency: pd.DataFrame,
    keyword_label_matrix: pd.DataFrame,
    theme_assignment_summary: dict[str, int],
) -> dict[str, object]:
    total_articles = len(records)
    labels_distribution: dict[str, int] = {}
    themes_distribution: dict[str, int] = {}
    publication_years: list[int] = []
    authors_per_article: list[int] = []
    references_per_article: list[int] = []
    keywords_per_article: list[int] = []
    abstract_word_count: list[int] = []
    for record in records:
        label = record.label_name or record.label_id or "unassigned"
        labels_distribution[label] = labels_distribution.get(label, 0) + 1
        for theme in record.themes:
            themes_distribution[theme] = themes_distribution.get(theme, 0) + 1
        if record.year is not None:
            publication_years.append(int(record.year))
        authors_per_article.append(len(record.corpus_authors))
        references_per_article.append(len(record.references_raw))
        keywords_per_article.append(len(record.author_keywords) + len(record.index_keywords))
        abstract_word_count.append(len(record.abstract.split()))

    parsed_success = 0
    if not parsed_references.empty:
        parsed_success = int((parsed_references["parse_confidence"].astype(str) != "FAILED").sum())

    keyword_top_rows: list[dict[str, object]] = []
    if not keyword_label_matrix.empty:
        keyword_top_rows = (
            keyword_label_matrix.groupby(["keyword", "keyword_source"], dropna=False)["article_count"]
            .sum()
            .reset_index()
            .sort_values(by=["article_count", "keyword"], ascending=[False, True])
            .head(10)
            .to_dict(orient="records")
        )

    top_cited_authors: list[dict[str, object]] = []
    if not cited_author_frequency.empty:
        top_cited_authors = cited_author_frequency.head(10).to_dict(orient="records")

    top_theme_names = [
        theme
        for theme, _count in sorted(themes_distribution.items(), key=lambda item: (-item[1], item[0]))[:10]
    ]

    return {
        "total_articles": total_articles,
        "articles_with_abstract": sum(1 for record in records if record.abstract.strip()),
        "articles_with_keywords": sum(
            1 for record in records if record.author_keywords or record.index_keywords
        ),
        "articles_with_references": sum(1 for record in records if record.references_raw),
        "total_corpus_authors": int(len(corpus_author_frequency)),
        "total_cited_authors": int(len(cited_author_frequency)),
        "total_references_raw": int(sum(len(record.references_raw) for record in records)),
        "total_references_parsed": parsed_success,
        "reference_parse_success_rate": _safe_ratio(parsed_success, sum(len(record.references_raw) for record in records)),
        "labels_distribution": labels_distribution,
        "themes_distribution": themes_distribution,
        "theme_assignment_summary": theme_assignment_summary,
        "top_keywords": keyword_top_rows,
        "top_cited_authors": top_cited_authors,
        "numeric_descriptives": {
            "publication_year": _numeric_profile(publication_years),
            "authors_per_article": _numeric_profile(authors_per_article),
            "references_per_article": _numeric_profile(references_per_article),
            "keywords_per_article": _numeric_profile(keywords_per_article),
            "abstract_word_count": _numeric_profile(abstract_word_count),
        },
        "distribution_snapshots": {
            "publication_year": _exact_distribution(publication_years),
            "authors_per_article": _exact_distribution(authors_per_article),
            "references_per_article": _binned_distribution(references_per_article, bin_size=10),
            "keywords_per_article": _exact_distribution(keywords_per_article),
            "abstract_word_count": _binned_distribution(abstract_word_count, bin_size=50),
        },
        "theme_year_timeline": _theme_year_timeline(records, selected_themes=tuple(top_theme_names)),
    }


def build_bibliometric_outputs(
    input_rows: pd.DataFrame,
    *,
    config: BibliometricConfig,
) -> BibliometricArtifacts:
    columns = resolve_bibliometric_columns(input_rows, config)
    records = build_bibliometric_records(input_rows, columns=columns)
    records, theme_assignment_summary = hydrate_record_themes(records, config=config)
    parsed_references = parse_references(records, config=config)
    cited_author_mentions = extract_cited_authors(parsed_references, records=records)
    corpus_author_mentions = _build_corpus_author_mentions(records)
    corpus_author_frequency = build_author_frequency(corpus_author_mentions, mention_source="CORPUS_AUTHOR")
    cited_author_frequency = build_author_frequency(cited_author_mentions, mention_source="CITED_AUTHOR")
    author_label_matrix = build_author_label_matrix(cited_author_mentions, records=records)
    author_theme_matrix = build_author_theme_matrix(cited_author_mentions, records=records)
    theme_label_matrix = build_theme_label_matrix(records)
    keyword_label_matrix = build_keyword_label_matrix(records, config=config)
    descriptive_stats = build_descriptive_stats(
        records,
        parsed_references=parsed_references,
        corpus_author_frequency=corpus_author_frequency,
        cited_author_frequency=cited_author_frequency,
        keyword_label_matrix=keyword_label_matrix,
        theme_assignment_summary=theme_assignment_summary,
    )
    enriched_rows = _build_enriched_rows(input_rows, records=records, columns=columns)
    return BibliometricArtifacts(
        enriched_rows=enriched_rows,
        parsed_references=parsed_references,
        corpus_author_frequency=corpus_author_frequency,
        cited_author_frequency=cited_author_frequency,
        author_label_matrix=author_label_matrix,
        author_theme_matrix=author_theme_matrix,
        theme_label_matrix=theme_label_matrix,
        keyword_label_matrix=keyword_label_matrix,
        descriptive_stats=descriptive_stats,
    )


def write_bibliometric_outputs(
    artifacts: BibliometricArtifacts,
    *,
    input_artifact: str | Path,
    output_dir: str | Path | None,
    config: BibliometricConfig,
    root: Path | None = None,
) -> BibliometricRunArtifacts:
    project_root = root or ROOT
    resolved_output_dir = _resolve_output_dir(output_dir, config=config, root=project_root)
    tables_dir = resolved_output_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)

    descriptive_stats_path = resolved_output_dir / "descriptive_stats.json"
    enriched_rows_path = tables_dir / "client_results_enriched.csv"
    parsed_references_path = tables_dir / "parsed_references.csv"
    corpus_author_frequency_path = tables_dir / "author_frequency.csv"
    cited_author_frequency_path = tables_dir / "cited_author_frequency.csv"
    author_label_matrix_path = tables_dir / "author_label_matrix.csv"
    author_theme_matrix_path = tables_dir / "author_theme_matrix.csv"
    theme_label_matrix_path = tables_dir / "theme_label_matrix.csv"
    keyword_label_matrix_path = tables_dir / "keyword_label_matrix.csv"
    manifest_path = resolved_output_dir / "bibliometric_manifest.json"

    artifacts.enriched_rows.to_csv(enriched_rows_path, index=False, encoding="utf-8")
    artifacts.parsed_references.to_csv(parsed_references_path, index=False, encoding="utf-8")
    artifacts.corpus_author_frequency.to_csv(corpus_author_frequency_path, index=False, encoding="utf-8")
    artifacts.cited_author_frequency.to_csv(cited_author_frequency_path, index=False, encoding="utf-8")
    artifacts.author_label_matrix.to_csv(author_label_matrix_path, index=False, encoding="utf-8")
    artifacts.author_theme_matrix.to_csv(author_theme_matrix_path, index=False, encoding="utf-8")
    artifacts.theme_label_matrix.to_csv(theme_label_matrix_path, index=False, encoding="utf-8")
    artifacts.keyword_label_matrix.to_csv(keyword_label_matrix_path, index=False, encoding="utf-8")
    descriptive_stats_path.write_text(
        json.dumps(artifacts.descriptive_stats, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    manifest_path.write_text(
        json.dumps(
            {
                "config_path": _relative_path(config.config_path, project_root),
                "input_artifact": _relative_path(Path(input_artifact), project_root),
                "output_dir": _relative_path(resolved_output_dir, project_root),
                "artifacts": {
                    "descriptive_stats": _relative_path(descriptive_stats_path, project_root),
                    "client_results_enriched": _relative_path(enriched_rows_path, project_root),
                    "parsed_references": _relative_path(parsed_references_path, project_root),
                    "author_frequency": _relative_path(corpus_author_frequency_path, project_root),
                    "cited_author_frequency": _relative_path(cited_author_frequency_path, project_root),
                    "author_label_matrix": _relative_path(author_label_matrix_path, project_root),
                    "author_theme_matrix": _relative_path(author_theme_matrix_path, project_root),
                    "theme_label_matrix": _relative_path(theme_label_matrix_path, project_root),
                    "keyword_label_matrix": _relative_path(keyword_label_matrix_path, project_root),
                },
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return BibliometricRunArtifacts(
        output_dir=resolved_output_dir,
        descriptive_stats_path=descriptive_stats_path,
        enriched_rows_path=enriched_rows_path,
        parsed_references_path=parsed_references_path,
        corpus_author_frequency_path=corpus_author_frequency_path,
        cited_author_frequency_path=cited_author_frequency_path,
        author_label_matrix_path=author_label_matrix_path,
        author_theme_matrix_path=author_theme_matrix_path,
        theme_label_matrix_path=theme_label_matrix_path,
        keyword_label_matrix_path=keyword_label_matrix_path,
        manifest_path=manifest_path,
    )


def load_saved_bibliometric_outputs(
    output_dir: str | Path,
    *,
    root: Path | None = None,
) -> BibliometricArtifacts:
    project_root = root or ROOT
    resolved_output_dir = Path(output_dir)
    if not resolved_output_dir.is_absolute():
        resolved_output_dir = (project_root / resolved_output_dir).resolve()
    tables_dir = resolved_output_dir / "tables"
    descriptive_stats = json.loads((resolved_output_dir / "descriptive_stats.json").read_text(encoding="utf-8"))
    return BibliometricArtifacts(
        enriched_rows=pd.read_csv(tables_dir / "client_results_enriched.csv"),
        parsed_references=pd.read_csv(tables_dir / "parsed_references.csv", low_memory=False),
        corpus_author_frequency=pd.read_csv(tables_dir / "author_frequency.csv"),
        cited_author_frequency=pd.read_csv(tables_dir / "cited_author_frequency.csv"),
        author_label_matrix=pd.read_csv(tables_dir / "author_label_matrix.csv"),
        author_theme_matrix=pd.read_csv(tables_dir / "author_theme_matrix.csv"),
        theme_label_matrix=pd.read_csv(tables_dir / "theme_label_matrix.csv"),
        keyword_label_matrix=pd.read_csv(tables_dir / "keyword_label_matrix.csv"),
        descriptive_stats=descriptive_stats,
    )


def _resolve_output_dir(
    output_dir: str | Path | None,
    *,
    config: BibliometricConfig,
    root: Path,
) -> Path:
    if output_dir is None:
        return config.default_output_root.resolve()
    candidate = Path(output_dir)
    if not candidate.is_absolute():
        candidate = root / candidate
    return candidate.resolve()


def _build_corpus_author_mentions(records: list[BibliometricRecord]) -> pd.DataFrame:
    mentions: list[dict[str, object]] = []
    for record in records:
        for author in record.corpus_authors:
            mentions.append(
                AuthorMention(
                    record_id=record.record_id,
                    author_key=_author_key(author),
                    author_display=author,
                    mention_source="CORPUS_AUTHOR",
                    label_id=record.label_id,
                    theme=None,
                ).__dict__
            )
    return pd.DataFrame.from_records(
        mentions,
        columns=["record_id", "author_key", "author_display", "mention_source", "label_id", "theme"],
    )


def _build_enriched_rows(
    input_rows: pd.DataFrame,
    *,
    records: list[BibliometricRecord],
    columns: dict[str, str | None],
) -> pd.DataFrame:
    enriched = input_rows.copy()
    lookup = {record.record_id: record for record in records}
    record_id_column = columns["record_id"]
    record_ids = enriched[record_id_column].map(lambda value: _clean_text(value) or "")
    enriched["label_id"] = record_ids.map(lambda value: lookup[value].label_id or "")
    enriched["label_name"] = record_ids.map(lambda value: lookup[value].label_name or "")
    enriched["corpus_authors_normalized"] = record_ids.map(
        lambda value: " | ".join(lookup[value].corpus_authors)
    )
    enriched["author_keywords_normalized"] = record_ids.map(
        lambda value: " | ".join(lookup[value].author_keywords)
    )
    enriched["index_keywords_normalized"] = record_ids.map(
        lambda value: " | ".join(lookup[value].index_keywords)
    )
    enriched["references_count"] = record_ids.map(lambda value: len(lookup[value].references_raw))
    enriched["themes_normalized"] = record_ids.map(lambda value: " | ".join(lookup[value].themes))
    return enriched


def _build_keyword_rows(records: list[BibliometricRecord], *, config: BibliometricConfig) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for record in records:
        if not record.label_id:
            continue
        for keyword in record.author_keywords:
            rows.append(
                {
                    "record_id": record.record_id,
                    "keyword": keyword,
                    "keyword_source": "AUTHOR_KEYWORD",
                    "label_id": record.label_id,
                    "label_name": record.label_name or "",
                }
            )
        for keyword in record.index_keywords:
            rows.append(
                {
                    "record_id": record.record_id,
                    "keyword": keyword,
                    "keyword_source": "INDEX_KEYWORD",
                    "label_id": record.label_id,
                    "label_name": record.label_name or "",
                }
            )

    tfidf_rows = _build_tfidf_keyword_rows(records, config=config)
    rows.extend(tfidf_rows)
    return pd.DataFrame.from_records(
        rows,
        columns=["record_id", "keyword", "keyword_source", "label_id", "label_name"],
    )


def _build_record_tfidf_terms(
    records: list[BibliometricRecord],
    *,
    config: BibliometricConfig,
) -> dict[str, tuple[str, ...]]:
    if not records:
        return {}
    texts = [
        "\n".join(
            part
            for part in (
                record.title,
                record.abstract,
                " ".join(record.author_keywords),
                " ".join(record.index_keywords),
            )
            if part.strip()
        )
        for record in records
    ]
    try:
        vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words="english",
            ngram_range=(config.themes.ngram_min, config.themes.ngram_max),
            max_features=config.themes.max_terms,
            min_df=config.themes.min_term_frequency,
        )
        matrix = vectorizer.fit_transform(texts)
    except ValueError:
        return {}

    feature_names = vectorizer.get_feature_names_out()
    derived: dict[str, tuple[str, ...]] = {}
    for position, record in enumerate(records):
        row_vector = matrix.getrow(position)
        if row_vector.nnz == 0:
            derived[record.record_id] = ()
            continue
        score_pairs = sorted(
            zip(row_vector.indices, row_vector.data, strict=False),
            key=lambda item: item[1],
            reverse=True,
        )
        seen: list[str] = []
        seen_keys: set[str] = set()
        for feature_index, _score in score_pairs:
            theme = _normalize_term(str(feature_names[feature_index]))
            if not _is_meaningful_theme(theme) or theme in seen_keys:
                continue
            seen_keys.add(theme)
            seen.append(theme)
            if len(seen) >= config.themes.tfidf_terms_per_record:
                break
        derived[record.record_id] = tuple(seen)
    return derived


def _build_tfidf_keyword_rows(
    records: list[BibliometricRecord],
    *,
    config: BibliometricConfig,
) -> list[dict[str, object]]:
    eligible_records = [record for record in records if record.label_id]
    if not eligible_records:
        return []
    texts = [
        "\n".join(
            part
            for part in (
                record.title,
                record.abstract,
                " ".join(record.author_keywords),
                " ".join(record.index_keywords),
            )
            if part.strip()
        )
        for record in eligible_records
    ]
    try:
        vectorizer = TfidfVectorizer(
            lowercase=True,
            stop_words="english",
            ngram_range=(config.themes.ngram_min, config.themes.ngram_max),
            max_features=config.themes.max_terms,
            min_df=config.themes.min_term_frequency,
        )
        matrix = vectorizer.fit_transform(texts)
    except ValueError:
        return []

    feature_names = vectorizer.get_feature_names_out()
    rows: list[dict[str, object]] = []
    for position, record in enumerate(eligible_records):
        row_vector = matrix.getrow(position)
        if row_vector.nnz == 0:
            continue
        score_pairs = sorted(
            zip(row_vector.indices, row_vector.data, strict=False),
            key=lambda item: item[1],
            reverse=True,
        )
        seen: set[str] = set()
        for feature_index, _score in score_pairs:
            keyword = _normalize_term(str(feature_names[feature_index]))
            if not keyword or keyword in seen:
                continue
            seen.add(keyword)
            rows.append(
                {
                    "record_id": record.record_id,
                    "keyword": keyword,
                    "keyword_source": "TFIDF_TERM",
                    "label_id": record.label_id or "",
                    "label_name": record.label_name or "",
                }
            )
            if len(seen) >= config.themes.tfidf_terms_per_record:
                break
    return rows


def _numeric_profile(values: list[int]) -> dict[str, float | int | None]:
    if not values:
        return {
            "count": 0,
            "mean": None,
            "median": None,
            "mode": None,
            "min": None,
            "max": None,
        }
    ordered = sorted(int(value) for value in values)
    midpoint = len(ordered) // 2
    if len(ordered) % 2 == 0:
        median: float | int = (ordered[midpoint - 1] + ordered[midpoint]) / 2
    else:
        median = ordered[midpoint]
    counts = pd.Series(ordered).value_counts(sort=True)
    mode = int(counts.index[0]) if not counts.empty else None
    return {
        "count": len(ordered),
        "mean": round(sum(ordered) / len(ordered), 3),
        "median": median,
        "mode": mode,
        "min": ordered[0],
        "max": ordered[-1],
    }


def _exact_distribution(values: list[int]) -> list[dict[str, int]]:
    if not values:
        return []
    counts = pd.Series([int(value) for value in values]).value_counts().sort_index()
    return [
        {"bucket": str(index), "bucket_sort": int(index), "count": int(count)}
        for index, count in counts.items()
    ]


def _binned_distribution(values: list[int], *, bin_size: int) -> list[dict[str, int]]:
    if not values:
        return []
    counts: dict[int, int] = {}
    for value in values:
        start = (int(value) // bin_size) * bin_size
        counts[start] = counts.get(start, 0) + 1
    rows: list[dict[str, int]] = []
    for start in sorted(counts):
        end = start + bin_size - 1
        rows.append(
            {
                "bucket": f"{start}-{end}",
                "bucket_sort": start,
                "count": counts[start],
            }
        )
    return rows


def _theme_year_timeline(
    records: list[BibliometricRecord],
    *,
    selected_themes: tuple[str, ...],
) -> list[dict[str, object]]:
    if not records or not selected_themes:
        return []
    counts: dict[tuple[int, str], int] = {}
    for record in records:
        if record.year is None:
            continue
        for theme in record.themes:
            if theme not in selected_themes:
                continue
            key = (int(record.year), theme)
            counts[key] = counts.get(key, 0) + 1
    rows: list[dict[str, object]] = []
    for (year, theme), count in sorted(counts.items(), key=lambda item: (item[0][0], item[0][1])):
        rows.append({"year": year, "theme": theme, "article_count": count})
    return rows


def _is_meaningful_theme(theme: str) -> bool:
    if not theme or theme in _GENERIC_THEME_TERMS:
        return False
    if not any(character.isalpha() for character in theme):
        return False
    if len(theme) < 3:
        return False
    tokens = [token for token in theme.split() if token]
    if not tokens:
        return False
    numeric_tokens = sum(1 for token in tokens if token.isdigit())
    if numeric_tokens == len(tokens):
        return False
    return True


def _extract_record_themes(
    *,
    row: dict[str, object],
    columns: dict[str, str | None],
) -> tuple[str, ...]:
    values: list[str] = []
    if columns["theme"]:
        values.extend(_split_terms(_clean_text(row.get(columns["theme"])) or ""))
    if columns["themes"]:
        values.extend(_split_pipe_values(_clean_text(row.get(columns["themes"])) or ""))
    return tuple(dict.fromkeys(values))


def _extract_title_fragment(reference: str, author_segment: str, year: int | None) -> str | None:
    text = _LEADING_REF_MARKER_RE.sub("", reference.strip())
    candidate = text
    if author_segment:
        candidate = candidate[len(author_segment) :].lstrip(" ,.;:-")
    if year is not None:
        candidate = re.sub(rf"^\(?{year}\)?[.,;:\s-]*", "", candidate).strip()
    if '"' in candidate:
        quoted = re.findall(r'"([^"]+)"', candidate)
        if quoted:
            return normalize_author_name(quoted[0]).strip() or None
    first_chunk = candidate.split(".", 1)[0].strip(" ,.;:-")
    if first_chunk:
        return first_chunk
    return None


def _assign_parse_confidence(
    *,
    authors: tuple[str, ...],
    year: int | None,
    doi: str | None,
    title_fragment: str | None,
) -> str:
    if authors and year and (doi or title_fragment):
        return "HIGH"
    if authors and year:
        return "MEDIUM"
    if authors:
        return "LOW"
    return "FAILED"


def _resolve_first_column(
    available_columns: Any,
    aliases: tuple[str, ...],
    *,
    required: bool,
) -> str | None:
    for alias in aliases:
        if alias in available_columns:
            return alias
    if required:
        raise ValueError(f"Input artifact is missing required column aliases: {list(aliases)}")
    return None


def _tuple_aliases(values: Any) -> tuple[str, ...]:
    return tuple(str(value) for value in values)


def _split_terms(raw_value: str) -> list[str]:
    text = raw_value.strip()
    if not text:
        return []
    if ";" in text or "|" in text:
        parts = re.split(r"\s*[;|]\s*", text)
    elif "," in text:
        parts = [part.strip() for part in text.split(",")]
    else:
        parts = [text]
    return [term for term in (_normalize_term(part) for part in parts) if term]


def _split_pipe_values(raw_value: str) -> list[str]:
    text = raw_value.strip()
    if not text:
        return []
    if "|" in text:
        parts = [part.strip() for part in text.split("|")]
    elif ";" in text:
        parts = [part.strip() for part in text.split(";")]
    elif "," in text:
        parts = [part.strip() for part in text.split(",")]
    else:
        parts = [text]
    return [term for term in (_normalize_term(part) for part in parts) if term]


def _split_display_values(raw_value: str) -> list[str]:
    text = raw_value.strip()
    if not text:
        return []
    if "|" in text:
        parts = [part.strip() for part in text.split("|")]
    elif ";" in text:
        parts = [part.strip() for part in text.split(";")]
    else:
        parts = [text]
    return [value for value in (normalize_author_name(part) for part in parts) if value]


def _split_authors(raw_value: str) -> list[str]:
    text = raw_value.strip()
    if not text:
        return []
    if ";" in text:
        parts = [part.strip() for part in text.split(";")]
    elif " and " in text:
        parts = [part.strip() for part in text.split(" and ")]
    elif " & " in text:
        parts = [part.strip() for part in text.split(" & ")]
    else:
        parts = [part.strip() for part in text.split("|")] if "|" in text else [text]
    values = [normalize_author_name(part) for part in parts if normalize_author_name(part)]
    return [value for value in values if value]


def _normalize_term(value: str) -> str:
    text = _clean_text(value) or ""
    text = text.lower()
    text = re.sub(r"[_/]+", " ", text)
    text = re.sub(r"[^\w\s-]", " ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip(" -")
    if len(text) < 3:
        return ""
    return text


def _clean_text(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, float) and pd.isna(value):
        return None
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    return text


def _clean_author_text(value: str) -> str:
    text = _PARENS_RE.sub("", value)
    text = _LEADING_REF_MARKER_RE.sub("", text)
    text = _NON_AUTHOR_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text


def _author_key(author_display: str) -> str:
    text = normalize_author_name(author_display)
    if not text:
        return ""
    if "," in text:
        surname, initials = [part.strip() for part in text.split(",", 1)]
        canonical = f"{surname} {initials}".strip()
    else:
        tokens = text.split()
        if len(tokens) >= 2 and all(token.rstrip(".").isupper() and len(token.rstrip(".")) <= 2 for token in tokens[:-1]):
            canonical = " ".join([tokens[-1], *tokens[:-1]])
        else:
            canonical = text
    canonical = unicodedata.normalize("NFKD", canonical)
    canonical = "".join(char for char in canonical if not unicodedata.combining(char))
    canonical = canonical.lower()
    canonical = canonical.replace(".", " ")
    canonical = _NON_KEY_RE.sub(" ", canonical)
    return _WHITESPACE_RE.sub(" ", canonical).strip()


def _author_has_signal(author: str, *, min_token_length: int) -> bool:
    if not author:
        return False
    tokens = [token.strip(".") for token in author.split()]
    return any(len(token) >= min_token_length for token in tokens)


def _is_plausible_author_candidate(author: str) -> bool:
    if not author:
        return False
    tokens = [token.strip("., ") for token in author.split() if token.strip("., ")]
    if not tokens:
        return False
    if len(tokens) > 4:
        return False
    has_initial = any(
        len(token.replace(".", "")) <= 3 and token.replace(".", "").isupper()
        for token in tokens
    )
    has_name = any(len(token) >= 3 and any(character.isalpha() for character in token) for token in tokens)
    if "," in author:
        surname, _rest = [part.strip() for part in author.split(",", 1)]
        if len(surname) < 2:
            return False
        return has_initial
    if len(tokens) < 2 or not has_initial or not has_name:
        return False
    initial_like = lambda token: token.replace(".", "").isupper() and len(token.replace(".", "")) <= 3
    first_is_initials = all(initial_like(token) for token in tokens[:-1]) and len(tokens[-1]) >= 3
    last_is_initial = initial_like(tokens[-1]) and any(len(token) >= 3 for token in tokens[:-1])
    return first_is_initials or last_is_initial


def _label_totals(records: list[BibliometricRecord]) -> dict[str, int]:
    totals: dict[str, int] = {}
    for record in records:
        if not record.label_id:
            continue
        totals[record.label_id] = totals.get(record.label_id, 0) + 1
    return totals


def _safe_ratio(numerator: int | float, denominator: int | float) -> float:
    if not denominator:
        return 0.0
    return float(numerator) / float(denominator)


def _relative_path(path: Path, root: Path) -> str:
    candidate = path
    if not candidate.is_absolute():
        candidate = (root / candidate).resolve()
    try:
        return candidate.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(candidate.resolve())
