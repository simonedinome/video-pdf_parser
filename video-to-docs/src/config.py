from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_ENV_KEY_MAP: dict[str, str] = {
    "google": "GOOGLE_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}

_MODEL_MAP: dict[str, str] = {
    "google": "gemini-2.5-flash",
    "openrouter": "google/gemini-2.5-flash",
}

SUPPORTED_EXTENSIONS: list[str] = ["mp4", "mov", "avi", "mkv", "webm"]

MAX_UPLOAD_MB: int = 200


def get_api_key(provider: str) -> str | None:
    """Return the API key for *provider* from the environment, or ``None``."""
    env_var = _ENV_KEY_MAP.get(provider)
    if env_var is None:
        return None
    return os.getenv(env_var)


@dataclass
class Settings:
    provider: str = "google"
    api_key: str = ""
    openrouter_max_mb: int = 19
    max_retries: int = 3

    @property
    def model(self) -> str:
        return _MODEL_MAP[self.provider]
