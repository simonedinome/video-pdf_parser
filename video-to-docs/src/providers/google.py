from __future__ import annotations

import time
from pathlib import Path

from google import genai
from google.genai import types as genai_types

from .base import BaseProvider
from .retry import with_retry


class GoogleProvider(BaseProvider):
    """Provider that uses the Google Gemini API via *google-genai* SDK."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash") -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model

    def generate(
        self,
        video_path: Path,
        mime_type: str,
        system_prompt: str,
        user_prompt: str,
    ) -> tuple[str, int, int]:
        # Upload to Google Files API
        uploaded = self._client.files.upload(
            file=video_path,
            config=genai_types.UploadFileConfig(mime_type=mime_type),
        )

        # Poll until processing is complete
        while uploaded.state.name == "PROCESSING":
            time.sleep(2)
            uploaded = self._client.files.get(name=uploaded.name)

        if uploaded.state.name == "FAILED":
            raise RuntimeError(f"Google file processing failed: {uploaded.state}")

        try:
            response = with_retry(
                lambda: self._client.models.generate_content(
                    model=self._model,
                    contents=[
                        genai_types.Content(
                            role="user",
                            parts=[
                                genai_types.Part.from_uri(
                                    file_uri=uploaded.uri,
                                    mime_type=mime_type,
                                ),
                                genai_types.Part.from_text(text=user_prompt),
                            ],
                        ),
                    ],
                    config=genai_types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=0.2,
                    ),
                )
            )
        finally:
            # Always clean up the uploaded file
            self._client.files.delete(name=uploaded.name)

        raw = response.text or ""
        usage = response.usage_metadata
        input_tokens = usage.prompt_token_count if usage else 0
        output_tokens = usage.candidates_token_count if usage else 0

        return raw, input_tokens, output_tokens
