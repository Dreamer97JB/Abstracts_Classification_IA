from __future__ import annotations

from pathlib import Path

from abstract_classifier.bibliometrics import (
    extract_doi,
    extract_year,
    guess_reference_style,
    load_bibliometric_config,
    normalize_author_name,
    parse_references,
    resolve_bibliometric_columns,
    split_reference_authors,
)
import pandas as pd


def test_resolve_bibliometric_columns_accepts_aliases(project_root: Path) -> None:
    config = load_bibliometric_config(root=project_root)
    frame = pd.DataFrame(
        [
            {
                "record_id": "s:1",
                "Title": "One",
                "Abstract": "Two",
                "Authors": "Smith, J.",
                "References": "Smith, J. (2020). Title.",
                "predicted_label_canonica": "Tipo 1",
            }
        ]
    )

    columns = resolve_bibliometric_columns(frame, config)

    assert columns["title"] == "Title"
    assert columns["references"] == "References"
    assert columns["label_name"] == "predicted_label_canonica"


def test_reference_parser_handles_mixed_styles(project_root: Path) -> None:
    config = load_bibliometric_config(root=project_root)
    records = pd.DataFrame(
        [
            {
                "record_id": "r1",
                "title": "Paper 1",
                "abstract": "Theory and evidence",
                "authors": "A Author; B Author",
                "references": 'Smith, J., & Brown, P. (2020). Example title. doi:10.1000/xyz123; [1] J. Adams and P. Baker, "Network title", Journal, 2021.',
                "predicted_canonical_id": "tipo_1",
                "predicted_label_canonica": "Tipo 1",
            }
        ]
    )

    parsed = parse_references(
        __import__("abstract_classifier.bibliometrics", fromlist=["build_bibliometric_records"]).build_bibliometric_records(
            records,
            columns=resolve_bibliometric_columns(records, config),
        ),
        config=config,
    )

    assert len(parsed) == 2
    assert set(parsed["style_guess"]) == {"APA_LIKE", "IEEE_LIKE"}
    assert "HIGH" in set(parsed["parse_confidence"])


def test_reference_parser_extractors_and_normalization() -> None:
    apa = "Smith, J., & Brown, P. (2020). Example title. https://doi.org/10.1000/xyz123"
    ieee = '[1] J. Smith and P. Brown, "Example title", Journal, 2020.'

    assert guess_reference_style(apa) == "APA_LIKE"
    assert guess_reference_style(ieee) == "IEEE_LIKE"
    assert extract_year(apa) == 2020
    assert extract_doi(apa) == "10.1000/xyz123"
    assert split_reference_authors("Smith, J., & Brown, P.") == ("Smith, J.", "Brown, P.")
    assert normalize_author_name("  Smith, J.  ") == "Smith, J."


def test_reference_parser_exports_failed_rows(project_root: Path) -> None:
    config = load_bibliometric_config(root=project_root)
    frame = pd.DataFrame(
        [
            {
                "record_id": "r1",
                "title": "Paper 1",
                "abstract": "Theory",
                "authors": "A Author",
                "references": "%%% ??? ###",
                "predicted_canonical_id": "tipo_1",
                "predicted_label_canonica": "Tipo 1",
            }
        ]
    )

    parsed = parse_references(
        __import__("abstract_classifier.bibliometrics", fromlist=["build_bibliometric_records"]).build_bibliometric_records(
            frame,
            columns=resolve_bibliometric_columns(frame, config),
        ),
        config=config,
    )

    assert parsed.loc[0, "parse_confidence"] == "FAILED"


def test_reference_parser_keeps_author_not_book_title() -> None:
    assert split_reference_authors("Latour B., Science in Action: How to Follow Scientists and Engineers Through Society") == (
        "Latour B",
    )
    assert split_reference_authors("Bloor D., Knowledge and Social Imagery") == (
        "Bloor D",
    )


def test_reference_parser_avoids_journal_as_author() -> None:
    assert split_reference_authors("Environment and Planning D: Society and Space") == ()
    assert split_reference_authors("Planning D: Society & Space") == ()
