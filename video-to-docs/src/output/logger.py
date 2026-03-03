from __future__ import annotations

import datetime


class Logger:
    """In-memory logger that collects lines for the final log file."""

    def __init__(self) -> None:
        self._lines: list[str] = []

    def log(self, level: str, message: str) -> None:
        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._lines.append(f"[{ts}] [{level}] {message}")

    @property
    def lines(self) -> list[str]:
        return list(self._lines)


def build_log_txt(log_lines: list[str]) -> str:
    """Build a plain-text log file from collected log lines."""
    header = [
        "=" * 60,
        "LOG DI GENERAZIONE",
        "=" * 60,
        "",
    ]
    return "\n".join(header + log_lines + [""])
