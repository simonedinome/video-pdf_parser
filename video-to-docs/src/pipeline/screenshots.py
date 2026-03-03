from __future__ import annotations

import re
import subprocess
from pathlib import Path


def _timestamp_to_seconds(ts: str) -> float:
    """Convert a ``MM:SS`` or ``HH:MM:SS`` timestamp to seconds."""
    parts = ts.strip().split(":")
    if len(parts) == 2:
        minutes, seconds = parts
        return int(minutes) * 60 + float(seconds)
    if len(parts) == 3:
        hours, minutes, seconds = parts
        return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
    raise ValueError(f"Formato timestamp non valido: {ts!r}")


def extract_screenshots(
    video_path: Path,
    steps: list[dict],
    output_dir: Path,
) -> dict[int, Path | None]:
    """Extract a screenshot from *video_path* for each step's timestamp.

    Returns a mapping ``{step_number: path_or_None}``.  If ``ffmpeg`` fails
    for a given step the value is ``None``.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    result: dict[int, Path | None] = {}

    for step in steps:
        num: int = step["number"]
        ts: str = step.get("timestamp", "")
        if not ts:
            result[num] = None
            continue

        try:
            seconds = _timestamp_to_seconds(ts)
        except ValueError:
            result[num] = None
            continue

        out_path = output_dir / f"step_{num:03d}.png"
        cmd = [
            "ffmpeg",
            "-y",
            "-ss", str(seconds),
            "-i", str(video_path),
            "-frames:v", "1",
            "-q:v", "2",
            str(out_path),
        ]

        try:
            subprocess.run(
                cmd,
                capture_output=True,
                check=True,
                timeout=30,
            )
            result[num] = out_path if out_path.exists() else None
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            result[num] = None

    return result
