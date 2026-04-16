from __future__ import annotations

import argparse
import csv
import statistics
from collections import Counter
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT = Path("reports/data_audit.md")


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def safe_float(value: str | None) -> float | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def length_stats(values: list[str]) -> str:
    if not values:
        return "n/a"
    lengths = [len(value) for value in values]
    return (
        f"min={min(lengths)}, "
        f"avg={statistics.mean(lengths):.1f}, "
        f"max={max(lengths)}"
    )


def counter_lines(counter: Counter[str], top_n: int | None = None) -> list[str]:
    items = counter.most_common(top_n)
    return [f"- `{label}`: `{count}`" for label, count in items]


def build_report(root: Path | None = None) -> str:
    project_root = root or ROOT

    lines: list[str] = []
    lines.append("# Data Audit")
    lines.append("")
    lines.append(f"Root: `{project_root}`")
    lines.append("")

    seed_labeled = project_root / "seed_labeled.csv"
    seed_generated = project_root / "seed_generated.csv"
    cleaned = project_root / "abstracs_cleaned.csv"
    final_csv = project_root / "abstracts_con_metodologia_optimizado.csv"

    if seed_labeled.exists():
        rows = read_csv_rows(seed_labeled)
        labels = Counter(row.get("label_text", "").strip() for row in rows)
        texts = [row.get("text", "") for row in rows]
        lines.append("## Seed labeled")
        lines.append("")
        lines.append(f"- rows: `{len(rows)}`")
        lines.append(f"- unique texts: `{len(set(texts))}`")
        lines.append(f"- text length stats: `{length_stats(texts)}`")
        lines.extend(counter_lines(labels))
        lines.append("")

    if seed_generated.exists():
        rows = read_csv_rows(seed_generated)
        labels = Counter(row.get("label_text", "").strip() for row in rows)
        texts = [row.get("text", "") for row in rows]
        unique_texts = len(set(texts))
        lines.append("## Seed generated")
        lines.append("")
        lines.append(f"- rows: `{len(rows)}`")
        lines.append(f"- unique texts: `{unique_texts}`")
        lines.append(f"- duplicate texts: `{len(rows) - unique_texts}`")
        lines.append(f"- text length stats: `{length_stats(texts)}`")
        lines.extend(counter_lines(labels))
        lines.append("")

    if cleaned.exists():
        rows = read_csv_rows(cleaned)
        abstracts = [
            row.get("Abstract", "")
            for row in rows
            if row.get("Abstract", "").strip()
        ]
        missing_abstract = sum(
            1 for row in rows if not row.get("Abstract", "").strip()
        )
        missing_title = sum(
            1 for row in rows if not row.get("Title", "").strip()
        )
        year_zero = sum(
            1 for row in rows if row.get("Year", "").strip() == "0"
        )
        year_blank = sum(
            1 for row in rows if not row.get("Year", "").strip()
        )
        lines.append("## Cleaned dataset")
        lines.append("")
        lines.append(f"- rows: `{len(rows)}`")
        lines.append(f"- missing abstract: `{missing_abstract}`")
        lines.append(f"- missing title: `{missing_title}`")
        lines.append(f"- year == 0: `{year_zero}`")
        lines.append(f"- blank year: `{year_blank}`")
        lines.append(f"- abstract length stats: `{length_stats(abstracts)}`")
        lines.append("")

    if final_csv.exists():
        rows = read_csv_rows(final_csv)
        stance = Counter(row.get("Predicted_Label", "").strip() for row in rows)
        methodology = Counter(row.get("Methodology", "").strip() for row in rows)
        topics = Counter(row.get("Topic_Label", "").strip() for row in rows)
        confidences = [
            value
            for row in rows
            if (value := safe_float(row.get("Confidence"))) is not None
        ]
        lines.append("## Final enriched output")
        lines.append("")
        lines.append(f"- rows: `{len(rows)}`")
        if confidences:
            lines.append(f"- confidence min: `{min(confidences):.4f}`")
            lines.append(
                f"- confidence avg: `{statistics.mean(confidences):.4f}`"
            )
            lines.append(f"- confidence max: `{max(confidences):.4f}`")
            lines.append(
                f"- confidence >= 0.8: `{sum(1 for value in confidences if value >= 0.8)}`"
            )
        lines.append("")
        lines.append("### Predicted label distribution")
        lines.extend(counter_lines(stance))
        lines.append("")
        lines.append("### Methodology distribution")
        lines.extend(counter_lines(methodology))
        lines.append("")
        lines.append("### Top topic labels")
        lines.extend(counter_lines(topics, top_n=15))
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_report(output: str | Path = DEFAULT_OUTPUT, root: Path | None = None) -> Path:
    project_root = root or ROOT
    output_path = Path(output)
    if not output_path.is_absolute():
        output_path = project_root / output_path
    output_path = output_path.resolve()

    report = build_report(project_root)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    return output_path


def handle_command(args: argparse.Namespace) -> int:
    output_path = write_report(args.output, root=ROOT)
    print(f"Report generated at: {output_path}")
    return 0


def register(subparsers) -> None:
    parser = subparsers.add_parser(
        "audit",
        help="Audit the current project CSV artifacts.",
        description="Generate a Markdown audit report for the current dataset artifacts.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Output path for the Markdown report.",
    )
    parser.set_defaults(handler=handle_command)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit the main CSV artifacts in the project."
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Output path for the Markdown report.",
    )
    args = parser.parse_args(argv)
    return handle_command(args)
