from __future__ import annotations

import base64
from pathlib import Path

from openai import OpenAI

from .base import BaseProvider
from .retry import with_retry


class OpenRouterProvider(BaseProvider):
    """Provider that routes requests through OpenRouter (openai-compatible)."""

    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
    MAX_MB = 19

    def __init__(
        self,
        api_key: str,
        model: str = "google/gemini-2.5-flash",
        max_mb: int = 19,
        max_retries: int = 3,
    ) -> None:
        self._client = OpenAI(
            api_key=api_key,
            base_url=self.OPENROUTER_BASE_URL,
        )
        self._model = model
        self._max_mb = max_mb
        self._max_retries = max_retries

    def generate(
        self,
        video_path: Path,
        mime_type: str,
        system_prompt: str,
        user_prompt: str,
    ) -> tuple[str, int, int]:
        size_mb = video_path.stat().st_size / (1024 * 1024)
        if size_mb > self._max_mb:
            raise ValueError(
                f"Il file video è {size_mb:.1f} MB, "
                f"ma OpenRouter supporta al massimo {self._max_mb} MB."
            )

        video_b64 = base64.b64encode(video_path.read_bytes()).decode()
        data_url = f"data:{mime_type};base64,{video_b64}"

        response = with_retry(
            lambda: self._client.chat.completions.create(
                model=self._model,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": data_url},
                            },
                            {"type": "text", "text": user_prompt},
                        ],
                    },
                ],
            ),
            max_attempts=self._max_retries,
        )

        raw = response.choices[0].message.content or ""
        usage = response.usage
        input_tokens = usage.prompt_tokens if usage else 0
        output_tokens = usage.completion_tokens if usage else 0

        return raw, input_tokens, output_tokens
