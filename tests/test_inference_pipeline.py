from __future__ import annotations

from abstract_classifier.contracts.sources import NormalizedSourceRow
from abstract_classifier.inference import assemble_inference_corpus
from abstract_classifier.normalization import normalize_doi, normalize_title


def _build_row(
    *,
    record_id: str,
    source_dataset: str,
    source_system: str,
    title: str,
    year: int,
    doi: str = "",
    abstract: str = "",
    author_keywords: str = "",
    references: str = "",
) -> NormalizedSourceRow:
    return NormalizedSourceRow(
        record_id=record_id,
        row_number=2,
        source_dataset=source_dataset,
        source_sheet="Sheet1",
        source_path="synthetic.xlsx",
        source_role="corpus",
        source_system=source_system,
        title=title,
        authors="A Author",
        doi=doi,
        abstract=abstract,
        journal="Journal",
        author_keywords=author_keywords,
        index_keywords="",
        references=references,
        label_original="",
        year=year,
        title_normalized=normalize_title(title),
        doi_normalized=normalize_doi(doi),
    )


def test_assemble_inference_corpus_exact_merges_and_keeps_manual_review_pairs() -> None:
    rows = [
        _build_row(
            record_id="google_corpus:sheet:2",
            source_dataset="google_corpus",
            source_system="google_scholar",
            title="Science of knowledge in practice",
            year=2020,
            doi="10.1000/test-doi",
            abstract="Short abstract.",
        ),
        _build_row(
            record_id="scopus_base:sheet:2",
            source_dataset="scopus_base",
            source_system="scopus",
            title="Science of knowledge in practice",
            year=2020,
            doi="10.1000/test-doi",
            abstract="Richer abstract with more metadata.",
            author_keywords="knowledge",
            references="Smith J.",
        ),
        _build_row(
            record_id="google_corpus:sheet:3",
            source_dataset="google_corpus",
            source_system="google_scholar",
            title="Science of knowledge in society practice",
            year=2021,
        ),
        _build_row(
            record_id="scopus_base:sheet:3",
            source_dataset="scopus_base",
            source_system="scopus",
            title="Science of knowledge in society practice zeta",
            year=2021,
        ),
    ]

    bundle = assemble_inference_corpus(rows)

    assert len(bundle.corpus_frame) == 3
    assert len(bundle.merge_decisions_frame) == 1
    assert len(bundle.overlap_review_frame) == 1

    merged_row = bundle.corpus_frame.loc[
        bundle.corpus_frame["merge_cluster_size"] == 2
    ].iloc[0]
    assert merged_row["record_id"] == "scopus_base:sheet:2"
    assert merged_row["merge_status"] == "exact_merged"
    assert "google_corpus:sheet:2" in merged_row["merged_record_ids"]
