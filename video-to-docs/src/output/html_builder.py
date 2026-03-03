from __future__ import annotations

import base64
from pathlib import Path

_CSS = """\
body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    max-width: 960px;
    margin: 0 auto;
    padding: 2rem;
    background: #f8f9fa;
    color: #212529;
    line-height: 1.6;
}
h1 {
    color: #1a73e8;
    border-bottom: 3px solid #1a73e8;
    padding-bottom: 0.5rem;
}
h2 {
    color: #1a73e8;
    margin-top: 2rem;
}
h3 {
    color: #333;
}
.summary {
    background: #e8f0fe;
    border-left: 4px solid #1a73e8;
    padding: 1rem 1.5rem;
    margin: 1.5rem 0;
    border-radius: 0 8px 8px 0;
}
.step {
    background: #fff;
    border: 1px solid #dadce0;
    border-radius: 8px;
    padding: 1.5rem;
    margin: 1rem 0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}
.step-header {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 0.75rem;
}
.step-number {
    background: #1a73e8;
    color: #fff;
    width: 32px;
    height: 32px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: bold;
    font-size: 0.9rem;
    flex-shrink: 0;
}
.timestamp {
    background: #e8f0fe;
    color: #1a73e8;
    padding: 0.15rem 0.6rem;
    border-radius: 12px;
    font-size: 0.85rem;
    font-weight: 500;
}
.step img {
    max-width: 100%;
    border-radius: 6px;
    margin-top: 0.75rem;
    border: 1px solid #dadce0;
}
.step .notes {
    background: #fff8e1;
    border-left: 3px solid #f9a825;
    padding: 0.5rem 1rem;
    margin-top: 0.75rem;
    border-radius: 0 6px 6px 0;
    font-size: 0.9rem;
}
.prerequisites {
    background: #fce8e6;
    border-left: 4px solid #d93025;
    padding: 1rem 1.5rem;
    border-radius: 0 8px 8px 0;
    margin: 1rem 0;
}
.prerequisites ul {
    margin: 0.5rem 0 0 0;
    padding-left: 1.25rem;
}
.glossary-table {
    width: 100%;
    border-collapse: collapse;
    margin: 1rem 0;
}
.glossary-table th,
.glossary-table td {
    border: 1px solid #dadce0;
    padding: 0.6rem 1rem;
    text-align: left;
}
.glossary-table th {
    background: #1a73e8;
    color: #fff;
}
.glossary-table tr:nth-child(even) {
    background: #f1f3f4;
}
.notes-section {
    background: #e6f4ea;
    border-left: 4px solid #34a853;
    padding: 1rem 1.5rem;
    border-radius: 0 8px 8px 0;
    margin: 1rem 0;
}
"""


def _render_steps_folder(steps: list[dict], screenshot_map: dict[int, Path | None]) -> str:
    """Render step HTML with relative ``<img src>`` paths."""
    parts: list[str] = []
    for step in steps:
        num = step["number"]
        ts = step.get("timestamp", "")
        title = step.get("title", "")
        desc = step.get("description", "")
        note = step.get("notes", "")
        img_html = ""
        sc = screenshot_map.get(num)
        if sc is not None:
            img_html = f'<img src="screenshots/{sc.name}" alt="Step {num}">'
        note_html = f'<div class="notes">{note}</div>' if note else ""
        parts.append(f"""
<div class="step">
  <div class="step-header">
    <div class="step-number">{num}</div>
    <h3>{title}</h3>
    <span class="timestamp">{ts}</span>
  </div>
  <p>{desc}</p>
  {img_html}
  {note_html}
</div>""")
    return "\n".join(parts)


def _render_steps_standalone(steps: list[dict], screenshot_map: dict[int, Path | None]) -> str:
    """Render step HTML with base64-embedded images."""
    parts: list[str] = []
    for step in steps:
        num = step["number"]
        ts = step.get("timestamp", "")
        title = step.get("title", "")
        desc = step.get("description", "")
        note = step.get("notes", "")
        img_html = ""
        sc = screenshot_map.get(num)
        if sc is not None and sc.exists():
            b64 = base64.b64encode(sc.read_bytes()).decode()
            img_html = f'<img src="data:image/png;base64,{b64}" alt="Step {num}">'
        note_html = f'<div class="notes">{note}</div>' if note else ""
        parts.append(f"""
<div class="step">
  <div class="step-header">
    <div class="step-number">{num}</div>
    <h3>{title}</h3>
    <span class="timestamp">{ts}</span>
  </div>
  <p>{desc}</p>
  {img_html}
  {note_html}
</div>""")
    return "\n".join(parts)


def _render_html(
    data: dict,
    steps_html: str,
) -> str:
    title = data.get("title", "Documentazione")
    summary = data.get("summary", "")
    prerequisites = data.get("prerequisites", [])
    glossary = data.get("glossary", [])
    notes = data.get("notes", [])

    prereq_items = "\n".join(f"    <li>{p}</li>" for p in prerequisites)
    prereq_html = f"""
<div class="prerequisites">
  <h2>Prerequisiti</h2>
  <ul>
{prereq_items}
  </ul>
</div>""" if prerequisites else ""

    glossary_rows = "\n".join(
        f'    <tr><td><strong>{g["term"]}</strong></td><td>{g["definition"]}</td></tr>'
        for g in glossary
    )
    glossary_html = f"""
<h2>Glossario</h2>
<table class="glossary-table">
  <thead><tr><th>Termine</th><th>Definizione</th></tr></thead>
  <tbody>
{glossary_rows}
  </tbody>
</table>""" if glossary else ""

    notes_items = "\n".join(f"  <li>{n}</li>" for n in notes)
    notes_html = f"""
<div class="notes-section">
  <h2>Note</h2>
  <ul>
{notes_items}
  </ul>
</div>""" if notes else ""

    return f"""<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>{_CSS}</style>
</head>
<body>
  <h1>{title}</h1>
  <div class="summary">{summary}</div>
  {prereq_html}
  <h2>Procedura</h2>
  {steps_html}
  {glossary_html}
  {notes_html}
</body>
</html>"""


def build_html_folder(data: dict, screenshot_map: dict[int, Path | None]) -> str:
    """Build HTML with relative ``screenshots/`` image paths."""
    steps_html = _render_steps_folder(data.get("steps", []), screenshot_map)
    return _render_html(data, steps_html)


def build_html_standalone(data: dict, screenshot_map: dict[int, Path | None]) -> str:
    """Build a single self-contained HTML file with base64-embedded images."""
    steps_html = _render_steps_standalone(data.get("steps", []), screenshot_map)
    return _render_html(data, steps_html)
