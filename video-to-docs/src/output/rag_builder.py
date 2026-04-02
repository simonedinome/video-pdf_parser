from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def _video_stem(video_filename: str) -> str:
    return Path(video_filename).stem


def _iso_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _glossary_terms_in_content(content: str, glossary: list[dict]) -> list[str]:
    """Return glossary terms that appear (case-insensitive) in *content*."""
    content_lower = content.lower()
    return [
        entry["term"]
        for entry in glossary
        if entry.get("term", "").lower() in content_lower
    ]


def build_rag_jsonl(data: dict, video_filename: str) -> str:
    """Build a JSONL string (one JSON object per line) for RAG ingestion.

    Chunks produced:
    - One summary chunk for the whole video
    - One chunk per step
    - One glossary chunk
    """
    stem = _video_stem(video_filename)
    processed_at = _iso_now()
    title = data.get("title", "")
    summary = data.get("summary", "")
    prerequisites: list[str] = data.get("prerequisites", [])
    steps: list[dict] = data.get("steps", [])
    glossary: list[dict] = data.get("glossary", [])

    chunks: list[dict] = []

    # --- Summary chunk -------------------------------------------------------
    prereq_str = ", ".join(prerequisites)
    summary_content = summary
    if prereq_str:
        summary_content = f"{summary}\n\nPrerequisiti: {prereq_str}"

    chunks.append({
        "chunk_id": f"{stem}_summary",
        "video_filename": video_filename,
        "chunk_type": "summary",
        "processed_at": processed_at,
        "title": title,
        "content": summary_content,
        "embedding_text": f"{title} {summary} {prereq_str}".strip(),
    })

    # --- Step chunks ---------------------------------------------------------
    for step in steps:
        number: int = step.get("number", 0)
        step_title: str = step.get("title", "")
        timestamp: str = step.get("timestamp", "")
        description: str = step.get("description", "")
        notes: str = step.get("notes", "") or ""
        embedding_keywords: list[str] = step.get("embedding_keywords", [])
        if not isinstance(embedding_keywords, list):
            embedding_keywords = []

        content = description
        if notes:
            content = f"{description}\n\n{notes}"

        glossary_terms = _glossary_terms_in_content(content, glossary)

        keywords_str = " ".join(embedding_keywords)
        glossary_str = " ".join(glossary_terms)
        embedding_text = (
            f"{title} step {number} {step_title} {timestamp} {content} "
            f"{keywords_str} {glossary_str}"
        ).strip()

        chunks.append({
            "chunk_id": f"{stem}_step_{number:03d}",
            "video_filename": video_filename,
            "chunk_type": "step",
            "processed_at": processed_at,
            "title": title,
            "step_number": number,
            "step_title": step_title,
            "timestamp": timestamp,
            "content": content,
            "glossary_terms": glossary_terms,
            "embedding_keywords": embedding_keywords,
            "embedding_text": embedding_text,
        })

    # --- Glossary chunk ------------------------------------------------------
    glossary_lines = [
        f"{entry.get('term', '')}: {entry.get('definition', '')}"
        for entry in glossary
    ]
    glossary_content = "\n".join(glossary_lines)
    chunks.append({
        "chunk_id": f"{stem}_glossary",
        "video_filename": video_filename,
        "chunk_type": "glossary",
        "processed_at": processed_at,
        "content": glossary_content,
        "embedding_text": glossary_content,
    })

    return "\n".join(json.dumps(chunk, ensure_ascii=False) for chunk in chunks)
