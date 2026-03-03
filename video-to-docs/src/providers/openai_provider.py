from __future__ import annotations

import base64
from pathlib import Path

from openai import OpenAI

from .base import BaseProvider


class OpenAIProvider(BaseProvider):
    """Provider that uses the native OpenAI API with vision."""

    def __init__(self, api_key: str, model: str = "gpt-4o") -> None:
        self._client = OpenAI(api_key=api_key)
        self._model = model

    def generate(
        self,
        video_path: Path,
        mime_type: str,
        system_prompt: str,
        user_prompt: str,
    ) -> tuple[str, int, int]:
        video_b64 = base64.b64encode(video_path.read_bytes()).decode()
        data_url = f"data:{mime_type};base64,{video_b64}"

        response = self._client.chat.completions.create(
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
        )

        raw = response.choices[0].message.content or ""
        usage = response.usage
        input_tokens = usage.prompt_tokens if usage else 0
        output_tokens = usage.completion_tokens if usage else 0

        return raw, input_tokens, output_tokens
