from __future__ import annotations

from abstract_classifier.contracts import NormalizedSourceRow
from abstract_classifier.overlap import (
    OverlapOutcome,
    build_overlap_decisions,
    classify_overlap,
    select_winner,
)


def make_row(
    *,
    record_id: str,
    source_dataset: str,
    source_system: str,
    title: str,
    title_normalized: str,
    year: int | None,
    doi_normalized: str = "",
    abstract: str = "",
    author_keywords: str = "",
    index_keywords: str = "",
    references: str = "",
) -> NormalizedSourceRow:
    return NormalizedSourceRow(
        record_id=record_id,
        row_number=2,
        source_dataset=source_dataset,
        source_sheet="Sheet1",
        source_path="fixture.xlsx",
        source_role="corpus",
        source_system=source_system,
        title=title,
        authors="Author",
        doi=doi_normalized,
        abstract=abstract,
        journal="Journal",
        author_keywords=author_keywords,
        index_keywords=index_keywords,
        references=references,
        label_original="",
        year=year,
        title_normalized=title_normalized,
        doi_normalized=doi_normalized,
    )


def test_classify_overlap_prefers_exact_doi_match() -> None:
    left = make_row(
        record_id="google:1",
        source_dataset="google_corpus",
        source_system="google_scholar",
        title="Paper A",
        title_normalized="paper a",
        year=2020,
        doi_normalized="10.1000/example",
    )
    right = make_row(
        record_id="scopus:1",
        source_dataset="scopus_base",
        source_system="scopus",
        title="Paper A revised",
        title_normalized="paper a revised",
        year=2021,
        doi_normalized="10.1000/example",
    )

    assert classify_overlap(left, right) == OverlapOutcome.MERGE_DOI


def test_classify_overlap_allows_exact_title_and_year_merge_without_doi() -> None:
    left = make_row(
        record_id="google:2",
        source_dataset="google_corpus",
        source_system="google_scholar",
        title="Sociology of science case study",
        title_normalized="sociology of science case study",
        year=2021,
    )
    right = make_row(
        record_id="seed:2",
        source_dataset="seed_gold",
        source_system="seed",
        title="Sociology of science case study",
        title_normalized="sociology of science case study",
        year=2021,
    )

    assert classify_overlap(left, right) == OverlapOutcome.MERGE_TITLE_YEAR


def test_non_exact_title_match_requires_manual_review() -> None:
    left = make_row(
        record_id="google:3",
        source_dataset="google_corpus",
        source_system="google_scholar",
        title="Benefits motivations and challenges of international collaborative research",
        title_normalized="benefits motivations and challenges of international collaborative research",
        year=2021,
    )
    right = make_row(
        record_id="seed:3",
        source_dataset="seed_gold",
        source_system="seed",
        title="Benefits motivations and challenges of collaborative international research",
        title_normalized="benefits motivations and challenges of collaborative international research",
        year=2021,
    )

    assert classify_overlap(left, right) == OverlapOutcome.MANUAL_REVIEW


def test_title_match_with_year_mismatch_requires_manual_review() -> None:
    left = make_row(
        record_id="google:4",
        source_dataset="google_corpus",
        source_system="google_scholar",
        title="Scientific writing as a social act",
        title_normalized="scientific writing as a social act",
        year=2019,
    )
    right = make_row(
        record_id="scopus:4",
        source_dataset="scopus_base",
        source_system="scopus",
        title="Scientific writing as a social act",
        title_normalized="scientific writing as a social act",
        year=2020,
    )

    assert classify_overlap(left, right) == OverlapOutcome.MANUAL_REVIEW


def test_select_winner_uses_completeness_then_scopus_tie_breaker() -> None:
    left = make_row(
        record_id="google:5",
        source_dataset="google_corpus",
        source_system="google_scholar",
        title="Paper",
        title_normalized="paper",
        year=2020,
        abstract="Short abstract",
    )
    right = make_row(
        record_id="scopus:5",
        source_dataset="scopus_base",
        source_system="scopus",
        title="Paper",
        title_normalized="paper",
        year=2020,
        abstract="Short abstract",
    )

    winner, selection_reason, left_score, right_score = select_winner(left, right)

    assert left_score == right_score
    assert winner is right
    assert selection_reason == "scopus_tie_breaker"


def test_build_overlap_decisions_tracks_all_review_statuses() -> None:
    rows = [
        make_row(
            record_id="google:6",
            source_dataset="google_corpus",
            source_system="google_scholar",
            title="Exact DOI left",
            title_normalized="exact doi left",
            year=2020,
            doi_normalized="10.1000/doi",
        ),
        make_row(
            record_id="scopus:6",
            source_dataset="scopus_base",
            source_system="scopus",
            title="Exact DOI right",
            title_normalized="exact doi right",
            year=2021,
            doi_normalized="10.1000/doi",
            references="Ref A",
        ),
        make_row(
            record_id="google:7",
            source_dataset="google_corpus",
            source_system="google_scholar",
            title="Exact title year",
            title_normalized="exact title year",
            year=2022,
        ),
        make_row(
            record_id="seed:7",
            source_dataset="seed_gold",
            source_system="seed",
            title="Exact title year",
            title_normalized="exact title year",
            year=2022,
        ),
        make_row(
            record_id="google:8",
            source_dataset="google_corpus",
            source_system="google_scholar",
            title="Near title research collaboration challenges",
            title_normalized="near title research collaboration challenges",
            year=2023,
        ),
        make_row(
            record_id="muestras:8",
            source_dataset="scopus_muestras",
            source_system="scopus",
            title="Near title collaboration research challenges",
            title_normalized="near title collaboration research challenges",
            year=2023,
        ),
    ]

    decisions = build_overlap_decisions(rows)
    outcomes = {decision.outcome for decision in decisions}

    assert outcomes == {
        OverlapOutcome.MERGE_DOI,
        OverlapOutcome.MERGE_TITLE_YEAR,
        OverlapOutcome.MANUAL_REVIEW,
    }
