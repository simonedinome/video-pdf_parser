from __future__ import annotations


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


def build_note(data: dict) -> str:
    """Build a plain-text notes file from parsed documentation data."""
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("NOTE E SUGGERIMENTI")
    lines.append("=" * 60)
    lines.append("")

    notes = data.get("notes", [])
    if not notes:
        lines.append("Nessuna nota aggiuntiva.")
    else:
        for i, note in enumerate(notes, 1):
            lines.append(f"  {i}. {note}")
            lines.append("")

    return "\n".join(lines)
