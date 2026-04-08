"""video-to-docs — Persistent run logger for batch processing sessions."""
from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path


class RunLogger:
    """Writes a real-time log file for a single batch run.

    Each run produces a file at ``output_dir/logs/run_{run_id}.log``.
    Lines are written unbuffered so progress is visible even if the process
    is interrupted.

    Args:
        output_dir: Root output directory (``logs/`` sub-dir is created automatically).
        run_id: Timestamp string in ``YYYYMMDD_HHMMSS`` format.
    """

    def __init__(self, output_dir: Path, run_id: str) -> None:
        log_dir = output_dir / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        self._path = log_dir / f"run_{run_id}.log"
        # buffering=1 → line-buffered (real-time writes)
        self._file: io.TextIOWrapper = self._path.open(
            "w", encoding="utf-8", buffering=1
        )
        self.log("INFO", f"=== START RUN {run_id} ===")

    # ------------------------------------------------------------------
    # Core logging
    # ------------------------------------------------------------------

    def log(self, level: str, message: str) -> None:
        """Write a single log line with timestamp prefix."""
        ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        self._file.write(f"[{ts}] [{level}] {message}\n")

    # ------------------------------------------------------------------
    # Shortcut helpers
    # ------------------------------------------------------------------

    def video_start(self, name: str) -> None:
        """Log the start of processing for a single video."""
        self.log("INFO", f"START: {name}")

    def video_success(self, name: str, duration_s: float, n_steps: int) -> None:
        """Log successful completion of a video."""
        self.log(
            "INFO",
            f"SUCCESS: {name} — {duration_s:.1f}s, {n_steps} step",
        )

    def video_failed(
        self, name: str, attempt: int, max_attempts: int, error: str
    ) -> None:
        """Log a failed attempt for a video."""
        self.log(
            "ERROR",
            f"FAILED: {name} (tentativo {attempt}/{max_attempts}) — {error}",
        )

    def video_skipped(self, name: str, reason: str) -> None:
        """Log a skipped video with its reason."""
        self.log("INFO", f"SKIPPED: {name} — {reason}")

    # ------------------------------------------------------------------
    # Finalisation
    # ------------------------------------------------------------------

    def summary(
        self, total: int, succeeded: int, failed: int, skipped: int
    ) -> None:
        """Write a summary block at the end of the run."""
        self.log("INFO", "=== SUMMARY ===")
        self.log(
            "INFO",
            (
                f"Totale: {total} | Successo: {succeeded} "
                f"| Falliti: {failed} | Saltati: {skipped}"
            ),
        )

    def close(self) -> None:
        """Write the final sentinel line and close the file."""
        self.log("INFO", "=== END RUN ===")
        self._file.close()
