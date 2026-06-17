from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
from typing import Sequence

import pandas as pd

from ..contracts import NormalizedSourceRow, SourceManifest
from ..io import load_normalized_rows, load_source_manifest
from ..overlap import OverlapDecision, OverlapOutcome, build_overlap_decisions

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT = Path("reports/data_audit.md")
DEFAULT_SOURCES_CONFIG = Path("configs/sources.toml")
STATUS_ORDER = (
    OverlapOutcome.MERGE_DOI,
    OverlapOutcome.MERGE_TITLE_YEAR,
    OverlapOutcome.MANUAL_REVIEW,
)
NORMALIZED_COLUMNS = [
    "record_id",
    "row_number",
    "source_dataset",
    "source_sheet",
    "source_path",
    "source_role",
    "source_system",
    "title",
    "authors",
    "doi",
    "abstract",
    "journal",
    "author_keywords",
    "index_keywords",
    "references",
    "label_original",
    "year",
    "title_normalized",
    "doi_normalized",
]
DECISION_COLUMNS = [
    "outcome",
    "left_record_id",
    "left_source_dataset",
    "left_source_sheet",
    "left_source_path",
    "left_source_role",
    "left_title",
    "left_year",
    "left_doi_normalized",
    "left_title_normalized",
    "left_completeness_score",
    "right_record_id",
    "right_source_dataset",
    "right_source_sheet",
    "right_source_path",
    "right_source_role",
    "right_title",
    "right_year",
    "right_doi_normalized",
    "right_title_normalized",
    "right_completeness_score",
    "winner_record_id",
    "winner_source_dataset",
    "selection_reason",
]


def resolve_output_path(output: str | Path, *, root: Path = ROOT) -> Path:
    output_path = Path(output)
    if not output_path.is_absolute():
        output_path = root / output_path
    return output_path.resolve()


def resolve_structured_dir(
    output_path: Path,
    structured_dir: str | Path | None,
    *,
    root: Path = ROOT,
) -> Path:
    if structured_dir is None:
        return output_path.with_name(f"{output_path.stem}_tables")

    path = Path(structured_dir)
    if not path.is_absolute():
        path = root / path
    return path.resolve()


def run_audit(
    *,
    source_config_path: Path,
    root: Path = ROOT,
) -> tuple[SourceManifest, list[NormalizedSourceRow], list[OverlapDecision]]:
    manifest = load_source_manifest(source_config_path)
    rows = load_normalized_rows(source_config_path, project_root=root)
    decisions = build_overlap_decisions(rows)
    return manifest, rows, decisions


def write_structured_outputs(
    rows: list[NormalizedSourceRow],
    decisions: list[OverlapDecision],
    *,
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}

    normalized_path = output_dir / "normalized_rows.csv"
    _write_csv(
        normalized_path,
        [row.to_dict() for row in rows],
        columns=NORMALIZED_COLUMNS,
    )
    paths["normalized_rows"] = normalized_path

    for outcome in STATUS_ORDER:
        status_path = output_dir / f"{outcome.value}.csv"
        _write_csv(
            status_path,
            [decision.to_dict() for decision in decisions if decision.outcome == outcome],
            columns=DECISION_COLUMNS,
        )
        paths[outcome.value] = status_path

    return paths


def build_report(
    *,
    manifest: SourceManifest,
    source_config_path: Path,
    rows: list[NormalizedSourceRow],
    decisions: list[OverlapDecision],
    structured_paths: dict[str, Path],
    root: Path = ROOT,
) -> str:
    lines: list[str] = ["# Data Audit", ""]
    lines.append(f"Source config: `{_display_path(source_config_path, root)}`")
    lines.append(f"Governed sources: `{len(manifest.sources)}`")
    lines.append(f"Normalized rows: `{len(rows)}`")
    lines.append("")

    lines.append("## Source Coverage")
    lines.append("")
    lines.append("| Dataset | Role | Sheet | Rows | Path |")
    lines.append("| --- | --- | --- | ---: | --- |")

    counts = Counter((row.source_dataset, row.source_sheet or "") for row in rows)
    for source in manifest.sources:
        key = (source.source_dataset, source.sheet or "")
        lines.append(
            "| "
            + " | ".join(
                (
                    source.source_dataset,
                    source.role.value,
                    source.sheet or "",
                    str(counts.get(key, 0)),
                    source.path,
                )
            )
            + " |"
        )
    lines.append("")

    lines.append("## Overlap Outcomes")
    lines.append("")
    outcome_counts = Counter(decision.outcome.value for decision in decisions)
    for outcome in STATUS_ORDER:
        lines.append(f"- `{outcome.value}`: `{outcome_counts.get(outcome.value, 0)}`")
    lines.append("")

    lines.append("## Structured Outputs")
    lines.append("")
    for name in ("normalized_rows", *(outcome.value for outcome in STATUS_ORDER)):
        lines.append(
            f"- `{name}`: `{_display_path(structured_paths[name], root)}`"
        )
    lines.append("")

    return "\n".join(lines)


def write_report(
    *,
    source_config_path: str | Path = DEFAULT_SOURCES_CONFIG,
    output: str | Path = DEFAULT_OUTPUT,
    structured_dir: str | Path | None = None,
    root: Path = ROOT,
) -> tuple[Path, dict[str, Path]]:
    source_config = resolve_output_path(source_config_path, root=root)
    output_path = resolve_output_path(output, root=root)
    structured_output_dir = resolve_structured_dir(output_path, structured_dir, root=root)

    manifest, rows, decisions = run_audit(source_config_path=source_config, root=root)
    structured_paths = write_structured_outputs(
        rows,
        decisions,
        output_dir=structured_output_dir,
    )
    report = build_report(
        manifest=manifest,
        source_config_path=source_config,
        rows=rows,
        decisions=decisions,
        structured_paths=structured_paths,
        root=root,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    return output_path, structured_paths


def handle_command(args: argparse.Namespace) -> int:
    output_path, structured_paths = write_report(
        source_config_path=args.sources_config,
        output=args.output,
        structured_dir=args.structured_dir,
        root=ROOT,
    )
    print(f"Report generated at: {output_path}")
    print(f"Structured outputs written to: {structured_paths['normalized_rows'].parent}")
    return 0


def register(subparsers) -> None:
    parser = subparsers.add_parser(
        "audit",
        help="Audit governed workbook sources and overlap outcomes.",
        description="Generate a Markdown audit report and overlap review tables from governed sources.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Output path for the Markdown report.",
    )
    parser.add_argument(
        "--sources-config",
        default=str(DEFAULT_SOURCES_CONFIG),
        help="Path to the governed source manifest TOML file.",
    )
    parser.add_argument(
        "--structured-dir",
        default=None,
        help="Optional directory for the structured CSV outputs.",
    )
    parser.set_defaults(handler=handle_command)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit governed workbook sources and overlap outcomes."
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Output path for the Markdown report.",
    )
    parser.add_argument(
        "--sources-config",
        default=str(DEFAULT_SOURCES_CONFIG),
        help="Path to the governed source manifest TOML file.",
    )
    parser.add_argument(
        "--structured-dir",
        default=None,
        help="Optional directory for the structured CSV outputs.",
    )
    args = parser.parse_args(argv)
    return handle_command(args)


def _display_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _write_csv(path: Path, rows: list[dict[str, object]], *, columns: list[str]) -> None:
    frame = pd.DataFrame(rows, columns=columns)
    frame.to_csv(path, index=False)
