from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

from .taxonomy import ROOT, SplitPolicy, SupervisionPolicy, load_supervision_policy

SPLIT_OUTPUT_COLUMNS = [
    "record_id",
    "split",
    "split_version",
    "split_seed",
    "same_article_group",
]


def build_split_assignments(
    candidate_rows: pd.DataFrame,
    *,
    root: Path | None = None,
    policy: SupervisionPolicy | None = None,
) -> pd.DataFrame:
    project_root = root or ROOT
    supervision_policy = policy or load_supervision_policy(root=project_root)
    split_policy = supervision_policy.split_defaults

    gold_rows = candidate_rows.loc[candidate_rows["include_in_gold"]].copy()
    if gold_rows.empty:
        return pd.DataFrame(columns=SPLIT_OUTPUT_COLUMNS)

    gold_rows["same_article_group"] = gold_rows.apply(
        lambda row: _same_article_group_key(
            record_id=str(row["record_id"]),
            doi_normalized=str(row.get("doi_normalized", "")),
            title_normalized=str(row.get("title_normalized", "")),
            year=_coerce_year(row.get("year")),
        ),
        axis=1,
    )

    group_labels = (
        gold_rows.groupby("same_article_group", dropna=False)["label_canonica"]
        .agg(lambda values: sorted(set(value for value in values if isinstance(value, str) and value)))
        .to_dict()
    )
    for group_key, labels in group_labels.items():
        if len(labels) > 1:
            raise ValueError(
                f"Same-article group `{group_key}` has conflicting canonical labels."
            )

    group_frame = (
        gold_rows.groupby("same_article_group", dropna=False)["label_canonica"]
        .first()
        .reset_index()
        .rename(columns={"label_canonica": "group_label"})
    )
    group_assignments = _assign_groups_to_splits(group_frame, split_policy)
    split_lookup = dict(
        zip(group_assignments["same_article_group"], group_assignments["split"])
    )

    gold_rows["split"] = gold_rows["same_article_group"].map(split_lookup)
    gold_rows["split_version"] = split_policy.version
    gold_rows["split_seed"] = split_policy.seed
    return gold_rows.loc[:, SPLIT_OUTPUT_COLUMNS].sort_values(
        by=["split", "same_article_group", "record_id"]
    ).reset_index(drop=True)


def _assign_groups_to_splits(
    groups: pd.DataFrame,
    split_policy: SplitPolicy,
) -> pd.DataFrame:
    assignments: list[dict[str, object]] = []
    for label, label_groups in groups.groupby("group_label", dropna=False):
        group_keys = sorted(label_groups["same_article_group"].tolist())
        ordered_groups = sorted(
            group_keys,
            key=lambda group_key: _stable_hash(f"{split_policy.seed}:{label}:{group_key}"),
        )
        train_count, val_count, test_count = _planned_split_counts(
            len(ordered_groups),
            split_policy,
        )

        for index, group_key in enumerate(ordered_groups):
            if index < test_count:
                split = "test"
            elif index < test_count + val_count:
                split = "val"
            else:
                split = "train"
            assignments.append(
                {
                    "same_article_group": group_key,
                    "split": split,
                }
            )

    return pd.DataFrame.from_records(assignments)


def _planned_split_counts(
    group_count: int,
    split_policy: SplitPolicy,
) -> tuple[int, int, int]:
    if group_count <= 0:
        return 0, 0, 0
    if group_count == 1:
        return 1, 0, 0

    test_count = int(round(group_count * split_policy.test_ratio))
    val_count = int(round(group_count * split_policy.val_ratio))

    if group_count >= 3 and test_count == 0:
        test_count = 1
    if group_count >= 6 and val_count == 0:
        val_count = 1

    while test_count + val_count >= group_count:
        if val_count > 0:
            val_count -= 1
        elif test_count > 0:
            test_count -= 1
        else:
            break

    train_count = group_count - test_count - val_count
    return train_count, val_count, test_count


def _same_article_group_key(
    *,
    record_id: str,
    doi_normalized: str,
    title_normalized: str,
    year: int | None,
) -> str:
    if doi_normalized:
        return f"doi:{doi_normalized}"
    if title_normalized and year is not None:
        return f"title_year:{title_normalized}:{year}"
    return f"record:{record_id}"


def _coerce_year(value: object) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def write_split_assignments(
    candidate_rows: pd.DataFrame,
    output: str | Path,
    *,
    root: Path | None = None,
    policy: SupervisionPolicy | None = None,
) -> Path:
    project_root = root or ROOT
    output_path = Path(output)
    if not output_path.is_absolute():
        output_path = project_root / output_path
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    split_frame = build_split_assignments(
        candidate_rows,
        root=project_root,
        policy=policy,
    )
    split_frame.to_csv(output_path, index=False, encoding="utf-8")
    return output_path
