from __future__ import annotations

import json
import re

_REQUIRED_KEYS: list[str] = [
    "title",
    "summary",
    "steps",
    "glossary",
    "notes",
    "prerequisites",
]


def parse_response(raw: str) -> dict:
    """Parse the raw model output into a validated documentation dict.

    Strips markdown code-fence wrappers, loads JSON, and checks that all
    required top-level keys are present and that ``steps`` is non-empty.

    Raises
    ------
    ValueError
        If the JSON is invalid or the structure does not meet requirements.
    """
    # Remove markdown code fences (```json ... ``` or ``` ... ```)
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", raw.strip())
    cleaned = re.sub(r"\n?```\s*$", "", cleaned)

    try:
        data: dict = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON non valido nella risposta del modello: {exc}") from exc

    missing = [k for k in _REQUIRED_KEYS if k not in data]
    if missing:
        raise ValueError(
            f"Chiavi obbligatorie mancanti nella risposta: {', '.join(missing)}"
        )

    if not isinstance(data["steps"], list) or len(data["steps"]) == 0:
        raise ValueError(
            "La risposta deve contenere almeno uno step nella lista 'steps'."
        )

    # Soft validation: embedding_keywords is optional but must be a list if present
    for step in data["steps"]:
        if "embedding_keywords" in step and not isinstance(step["embedding_keywords"], list):
            step["embedding_keywords"] = []

    return data
