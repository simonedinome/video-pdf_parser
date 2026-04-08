"""video-to-docs — HTTP video downloader."""
from __future__ import annotations

from pathlib import Path
from urllib.parse import unquote, urlparse

import requests


def download_url(url: str, dest_dir: Path, timeout: int = 120) -> Path:
    """Download a video file from *url* into *dest_dir*.

    The filename is determined from the ``Content-Disposition`` response header
    when available, falling back to the last path segment of the URL.

    Args:
        url: HTTP/HTTPS URL pointing to a video file.
        dest_dir: Directory where the downloaded file will be written.
        timeout: Request timeout in seconds (default 120).

    Returns:
        Path to the downloaded file.

    Raises:
        requests.HTTPError: If the HTTP response status is not 2xx.
        ValueError: If the ``Content-Type`` header does not start with ``video/``.
    """
    with requests.get(url, stream=True, timeout=timeout) as response:
        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "")
        if not content_type.startswith("video/"):
            raise ValueError(
                f"URL non è un video: Content-Type='{content_type}' (atteso: video/*)"
            )

        filename = _filename_from_headers(response.headers, url)
        dest = dest_dir / filename

        with dest.open("wb") as fh:
            for chunk in response.iter_content(chunk_size=8 * 1024 * 1024):
                if chunk:
                    fh.write(chunk)

    return dest


def _filename_from_headers(headers: requests.structures.CaseInsensitiveDict, url: str) -> str:
    """Extract a filename from response headers or fall back to the URL path."""
    content_disposition = headers.get("Content-Disposition", "")
    if content_disposition:
        for part in content_disposition.split(";"):
            part = part.strip()
            if part.lower().startswith("filename="):
                name = part[len("filename="):].strip().strip('"').strip("'")
                if name:
                    return name

    path_segment = unquote(urlparse(url).path.split("/")[-1])
    return path_segment or "video"
