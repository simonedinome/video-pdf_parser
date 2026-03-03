from __future__ import annotations

import io
import zipfile
from pathlib import Path


def create_zip(
    files: dict[str, bytes],
    screenshot_dir: Path | None,
    mode: str,
) -> bytes:
    """Create an in-memory ZIP archive and return the raw bytes.

    Parameters
    ----------
    files:
        Mapping of ``{filename: content_bytes}`` for text/HTML artefacts.
    screenshot_dir:
        Directory containing screenshot PNGs (may be ``None``).
    mode:
        One of ``"standalone"``, ``"folder"``, or ``"both"``.

    Returns
    -------
    bytes
        The ZIP file content, ready for download.
    """
    buf = io.BytesIO()

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            # In standalone mode, skip the folder-variant HTML
            if mode == "standalone" and name == "documentazione.html":
                continue
            # In folder mode, skip the standalone-variant HTML
            if mode == "folder" and name == "documentazione_standalone.html":
                continue
            zf.writestr(name, content)

        # Include screenshots for folder / both modes
        if mode in ("folder", "both") and screenshot_dir is not None and screenshot_dir.exists():
            for img in sorted(screenshot_dir.glob("*.png")):
                zf.write(img, f"screenshots/{img.name}")

    return buf.getvalue()
