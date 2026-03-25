from __future__ import annotations

import argparse
import csv
import statistics
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


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


def build_report() -> str:
    lines: list[str] = []
    lines.append("# Data Audit")
    lines.append("")
    lines.append(f"Root: `{ROOT}`")
    lines.append("")

    seed_labeled = ROOT / "seed_labeled.csv"
    seed_generated = ROOT / "seed_generated.csv"
    cleaned = ROOT / "abstracs_cleaned.csv"
    final_csv = ROOT / "abstracts_con_metodologia_optimizado.csv"

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
        abstracts = [row.get("Abstract", "") for row in rows if row.get("Abstract", "").strip()]
        missing_abstract = sum(1 for row in rows if not row.get("Abstract", "").strip())
        missing_title = sum(1 for row in rows if not row.get("Title", "").strip())
        year_zero = sum(1 for row in rows if row.get("Year", "").strip() == "0")
        year_blank = sum(1 for row in rows if not row.get("Year", "").strip())
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
            lines.append(f"- confidence avg: `{statistics.mean(confidences):.4f}`")
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Audita los CSV principales del proyecto.")
    parser.add_argument(
        "--output",
        default="reports/data_audit.md",
        help="Ruta de salida del reporte en Markdown.",
    )
    args = parser.parse_args()

    report = build_report()
    output_path = (ROOT / args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(f"Reporte generado en: {output_path}")


if __name__ == "__main__":
    main()
