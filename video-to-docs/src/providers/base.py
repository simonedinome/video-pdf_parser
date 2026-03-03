from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class BaseProvider(ABC):
    """Abstract base class for AI video-analysis providers."""

    @abstractmethod
    def generate(
        self,
        video_path: Path,
        mime_type: str,
        system_prompt: str,
        user_prompt: str,
    ) -> tuple[str, int, int]:
        """Analyse *video_path* and return structured documentation.

        Returns
        -------
        tuple[str, int, int]
            ``(raw_json, input_tokens, output_tokens)``
        """
        ...
