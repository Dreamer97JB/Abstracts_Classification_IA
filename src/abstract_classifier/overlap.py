from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from itertools import combinations
from typing import Iterable

from .contracts import NormalizedSourceRow


class OverlapOutcome(StrEnum):
    MERGE_DOI = "merge_doi"
    MERGE_TITLE_YEAR = "merge_title_year"
    MANUAL_REVIEW = "manual_review"


@dataclass(frozen=True, slots=True)
class OverlapDecision:
    outcome: OverlapOutcome
    left: NormalizedSourceRow
    right: NormalizedSourceRow
    winner: NormalizedSourceRow
    left_completeness_score: int
    right_completeness_score: int
    selection_reason: str

    def to_dict(self) -> dict[str, object]:
        return {
            "outcome": self.outcome.value,
            "left_record_id": self.left.record_id,
            "left_source_dataset": self.left.source_dataset,
            "left_source_sheet": self.left.source_sheet or "",
            "left_source_path": self.left.source_path,
            "left_source_role": self.left.source_role,
            "left_title": self.left.title,
            "left_year": self.left.year,
            "left_doi_normalized": self.left.doi_normalized,
            "left_title_normalized": self.left.title_normalized,
            "left_completeness_score": self.left_completeness_score,
            "right_record_id": self.right.record_id,
            "right_source_dataset": self.right.source_dataset,
            "right_source_sheet": self.right.source_sheet or "",
            "right_source_path": self.right.source_path,
            "right_source_role": self.right.source_role,
            "right_title": self.right.title,
            "right_year": self.right.year,
            "right_doi_normalized": self.right.doi_normalized,
            "right_title_normalized": self.right.title_normalized,
            "right_completeness_score": self.right_completeness_score,
            "winner_record_id": self.winner.record_id,
            "winner_source_dataset": self.winner.source_dataset,
            "selection_reason": self.selection_reason,
        }


def completeness_score(record: NormalizedSourceRow) -> int:
    score = 0
    fields = (
        record.title,
        record.abstract,
        record.doi_normalized,
        record.authors,
        record.journal,
        record.author_keywords,
        record.index_keywords,
        record.references,
    )
    for field in fields:
        if field:
            score += 1
    if record.year is not None:
        score += 1
    return score


def classify_overlap(left: NormalizedSourceRow, right: NormalizedSourceRow) -> OverlapOutcome | None:
    if left.record_id == right.record_id or left.source_dataset == right.source_dataset:
        return None

    if left.doi_normalized and left.doi_normalized == right.doi_normalized:
        return OverlapOutcome.MERGE_DOI

    if (
        left.title_normalized
        and left.title_normalized == right.title_normalized
        and left.year is not None
        and left.year == right.year
    ):
        return OverlapOutcome.MERGE_TITLE_YEAR

    if _requires_manual_review(left, right):
        return OverlapOutcome.MANUAL_REVIEW

    return None


def build_overlap_decisions(rows: Iterable[NormalizedSourceRow]) -> list[OverlapDecision]:
    records = list(rows)
    decisions: list[OverlapDecision] = []
    seen_pairs: set[tuple[str, str]] = set()

    for groups in (
        _group_by_doi(records),
        _group_by_title_year(records),
        _group_by_title(records),
        _group_by_review_block(records),
    ):
        for group in groups.values():
            if len(group) < 2:
                continue
            for left, right in combinations(group, 2):
                pair_key = tuple(sorted((left.record_id, right.record_id)))
                if pair_key in seen_pairs:
                    continue
                outcome = classify_overlap(left, right)
                if outcome is None:
                    continue
                winner, selection_reason, left_score, right_score = select_winner(left, right)
                decisions.append(
                    OverlapDecision(
                        outcome=outcome,
                        left=left,
                        right=right,
                        winner=winner,
                        left_completeness_score=left_score,
                        right_completeness_score=right_score,
                        selection_reason=selection_reason,
                    )
                )
                seen_pairs.add(pair_key)

    return sorted(
        decisions,
        key=lambda item: (
            item.outcome.value,
            item.left.source_dataset,
            item.right.source_dataset,
            item.left.record_id,
            item.right.record_id,
        ),
    )


def select_winner(
    left: NormalizedSourceRow,
    right: NormalizedSourceRow,
) -> tuple[NormalizedSourceRow, str, int, int]:
    left_score = completeness_score(left)
    right_score = completeness_score(right)

    if left_score > right_score:
        return left, "higher_completeness_score", left_score, right_score
    if right_score > left_score:
        return right, "higher_completeness_score", left_score, right_score

    if left.source_system == "scopus" and right.source_system != "scopus":
        return left, "scopus_tie_breaker", left_score, right_score
    if right.source_system == "scopus" and left.source_system != "scopus":
        return right, "scopus_tie_breaker", left_score, right_score

    winner = left if left.record_id <= right.record_id else right
    return winner, "stable_record_id_tie_breaker", left_score, right_score


def _requires_manual_review(left: NormalizedSourceRow, right: NormalizedSourceRow) -> bool:
    if not left.title_normalized or not right.title_normalized:
        return False

    if left.title_normalized == right.title_normalized and left.year != right.year:
        return True

    same_year = left.year is not None and left.year == right.year
    return same_year and _near_title_match(left.title_normalized, right.title_normalized)


def _near_title_match(left_title: str, right_title: str) -> bool:
    if left_title == right_title:
        return False

    left_tokens = tuple(left_title.split())
    right_tokens = tuple(right_title.split())
    if len(left_tokens) < 4 or len(right_tokens) < 4:
        return False

    left_set = set(left_tokens)
    right_set = set(right_tokens)
    overlap = len(left_set & right_set)
    union = len(left_set | right_set)
    if overlap < 4:
        return False
    return (overlap / union) >= 0.8


def _group_by_doi(rows: list[NormalizedSourceRow]) -> dict[str, list[NormalizedSourceRow]]:
    groups: dict[str, list[NormalizedSourceRow]] = {}
    for row in rows:
        if not row.doi_normalized:
            continue
        groups.setdefault(row.doi_normalized, []).append(row)
    return groups


def _group_by_title_year(rows: list[NormalizedSourceRow]) -> dict[tuple[str, int], list[NormalizedSourceRow]]:
    groups: dict[tuple[str, int], list[NormalizedSourceRow]] = {}
    for row in rows:
        if not row.title_normalized or row.year is None:
            continue
        groups.setdefault((row.title_normalized, row.year), []).append(row)
    return groups


def _group_by_title(rows: list[NormalizedSourceRow]) -> dict[str, list[NormalizedSourceRow]]:
    groups: dict[str, list[NormalizedSourceRow]] = {}
    for row in rows:
        if not row.title_normalized:
            continue
        groups.setdefault(row.title_normalized, []).append(row)
    return groups


def _group_by_review_block(rows: list[NormalizedSourceRow]) -> dict[tuple[int, str], list[NormalizedSourceRow]]:
    groups: dict[tuple[int, str], list[NormalizedSourceRow]] = {}
    for row in rows:
        if row.year is None or not row.title_normalized:
            continue
        block = _review_block_key(row)
        groups.setdefault(block, []).append(row)
    return groups


def _review_block_key(row: NormalizedSourceRow) -> tuple[int, str]:
    tokens = sorted(set(row.title_normalized.split()))
    return row.year or 0, " ".join(tokens[:5])
