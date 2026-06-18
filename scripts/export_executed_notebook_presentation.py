from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

import mistune


def _render_markdown(text: str) -> str:
    return mistune.html(text)


def _render_output(output: dict[str, object]) -> str:
    output_type = str(output.get("output_type", ""))
    if output_type in {"display_data", "execute_result"}:
        data = output.get("data", {})
        if not isinstance(data, dict):
            return ""
        if "text/html" in data:
            html_value = data["text/html"]
            return "".join(html_value) if isinstance(html_value, list) else str(html_value)
        if "text/markdown" in data:
            markdown_value = data["text/markdown"]
            markdown_text = "".join(markdown_value) if isinstance(markdown_value, list) else str(markdown_value)
            return _render_markdown(markdown_text)
        if "text/plain" in data:
            plain_value = data["text/plain"]
            plain_text = "".join(plain_value) if isinstance(plain_value, list) else str(plain_value)
            return f"<pre>{html.escape(plain_text)}</pre>"
        return ""
    if output_type == "stream":
        text_value = output.get("text", "")
        text = "".join(text_value) if isinstance(text_value, list) else str(text_value)
        return f"<pre>{html.escape(text)}</pre>"
    if output_type == "error":
        traceback = output.get("traceback", [])
        text = "\n".join(traceback) if isinstance(traceback, list) else str(traceback)
        return f"<pre class='error'>{html.escape(text)}</pre>"
    return ""


def build_html(notebook: dict[str, object], title: str) -> str:
    sections: list[str] = []
    for cell in notebook.get("cells", []):
        cell_type = cell.get("cell_type")
        source = "".join(cell.get("source", []))
        if cell_type == "markdown":
            sections.append(f"<section class='block markdown-block'>{_render_markdown(source)}</section>")
            continue
        if cell_type == "code":
            rendered_outputs = [
                fragment
                for output in cell.get("outputs", [])
                if isinstance(output, dict)
                for fragment in [_render_output(output)]
                if fragment.strip()
            ]
            if rendered_outputs:
                sections.append(f"<section class='block output-block'>{''.join(rendered_outputs)}</section>")

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    :root {{
      --bg: #f4f0e8;
      --panel: #fffdf9;
      --ink: #20323a;
      --muted: #5f6c76;
      --line: #d9d2c3;
      --accent: #0f766e;
      --shadow: 0 10px 28px rgba(16, 24, 40, 0.08);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      padding: 0;
      font-family: "Segoe UI", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, #f8edd1 0, transparent 34%),
        radial-gradient(circle at top right, #dcefe2 0, transparent 28%),
        linear-gradient(180deg, #faf6ef 0%, var(--bg) 100%);
    }}
    main {{
      max-width: 1360px;
      margin: 0 auto;
      padding: 28px 20px 80px;
      display: grid;
      gap: 16px;
    }}
    .block {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      box-shadow: var(--shadow);
      padding: 18px 20px;
      overflow-x: auto;
    }}
    h1, h2, h3 {{
      color: #12343b;
      margin-top: 0;
    }}
    p, li {{
      line-height: 1.6;
      color: var(--ink);
    }}
    .markdown-block p {{
      color: var(--muted);
    }}
    .output-block pre {{
      white-space: pre-wrap;
      background: #fbf8f2;
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 12px 14px;
      font-size: 13px;
    }}
    .output-block .error {{
      color: #7f1d1d;
      background: #fff1f2;
      border-color: #fecdd3;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: white;
      margin: 10px 0;
    }}
    th, td {{
      border: 1px solid var(--line);
      padding: 8px 10px;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      background: #efe7d8;
    }}
    ul {{
      padding-left: 22px;
    }}
  </style>
</head>
<body>
  <main>
    {''.join(sections)}
  </main>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Export an executed notebook into a presentation-first HTML file.")
    parser.add_argument("--notebook", type=Path, required=True, help="Executed notebook path.")
    parser.add_argument("--output", type=Path, required=True, help="Output HTML path.")
    parser.add_argument("--title", default="Scopus analytics presentation", help="HTML title.")
    args = parser.parse_args()

    notebook = json.loads(args.notebook.read_text(encoding="utf-8"))
    html_text = build_html(notebook, args.title)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html_text, encoding="utf-8")
    print(f"Presentation HTML written to {args.output.resolve()}")


if __name__ == "__main__":
    main()
