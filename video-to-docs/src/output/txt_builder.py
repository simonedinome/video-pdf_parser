from __future__ import annotations

from datetime import date


def build_glossario(data: dict) -> str:
    """Build a plain-text glossary file from parsed documentation data."""
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("GLOSSARIO")
    lines.append("=" * 60)
    lines.append("")

    glossary = data.get("glossary", [])
    if not glossary:
        lines.append("Nessun termine nel glossario.")
    else:
        for entry in glossary:
            term = entry.get("term", "")
            definition = entry.get("definition", "")
            lines.append(f"  {term}")
            lines.append(f"    {definition}")
            lines.append("")

    return "\n".join(lines)


def build_procedura(data: dict, video_filename: str) -> str:
    """Build a plain-text procedure file from parsed documentation data.

    Produces clean ASCII output suitable for tokenizers, without decorative
    characters (no ===, ---, bullets, or emoji).
    """
    title: str = data.get("title", "")
    summary: str = data.get("summary", "")
    prerequisites: list[str] = data.get("prerequisites", [])
    steps: list[dict] = data.get("steps", [])
    notes: list[str] = data.get("notes", [])

    today = date.today().isoformat()

    lines: list[str] = []

    lines.append(title)
    lines.append(f"Video: {video_filename}")
    lines.append(f"Generato il: {today}")
    lines.append("=" * 18)
    lines.append("")

    lines.append("SOMMARIO")
    lines.append(summary)
    lines.append("")

    lines.append("PREREQUISITI")
    if prerequisites:
        for i, prereq in enumerate(prerequisites, 1):
            lines.append(f"{i}. {prereq}")
    else:
        lines.append("Nessun prerequisito.")
    lines.append("")

    lines.append("PROCEDURA")
    lines.append("")
    for step in steps:
        number: int = step.get("number", 0)
        step_title: str = step.get("title", "")
        timestamp: str = step.get("timestamp", "")
        description: str = step.get("description", "")
        step_notes: str = step.get("notes", "") or ""

        lines.append(f"STEP {number} — {step_title} [{timestamp}]")
        lines.append(description)
        if step_notes:
            lines.append(f"Note: {step_notes}")
        lines.append("")

    if notes:
        lines.append("NOTE GENERALI")
        for i, note in enumerate(notes, 1):
            lines.append(f"{i}. {note}")
        lines.append("")

    return "\n".join(lines)
