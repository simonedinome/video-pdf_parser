"""video-to-docs — CLI entry point per esecuzione batch in Codespace."""
from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
_CHECKPOINT_FILE = "processed.json"


# ---------------------------------------------------------------------------
# Queue item
# ---------------------------------------------------------------------------

@dataclass
class QueueItem:
    name: str
    source: Literal["file", "url"]
    path: Path | None = None
    url: str | None = None


# ---------------------------------------------------------------------------
# Checkpoint helpers
# ---------------------------------------------------------------------------

def _load_checkpoint(output_dir: Path) -> dict:
    cp_path = output_dir / _CHECKPOINT_FILE
    if cp_path.exists():
        try:
            return json.loads(cp_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {"processed": [], "failed": {}}


def _save_checkpoint(output_dir: Path, checkpoint: dict) -> None:
    cp_path = output_dir / _CHECKPOINT_FILE
    cp_path.write_text(json.dumps(checkpoint, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------------------
# Input discovery
# ---------------------------------------------------------------------------

def _list_videos(input_dir: Path) -> list[Path]:
    return sorted(
        p for p in input_dir.iterdir()
        if p.is_file() and p.suffix.lower() in _VIDEO_EXTENSIONS
    )


def _load_urls(path: Path) -> list[str]:
    """Read *path* and return non-empty, non-comment lines."""
    lines = path.read_text(encoding="utf-8").splitlines()
    return [
        line.strip()
        for line in lines
        if line.strip() and not line.strip().startswith("#")
    ]


# ---------------------------------------------------------------------------
# Video processing
# ---------------------------------------------------------------------------

def _process_video(
    video_path: Path,
    output_dir: Path,
    provider: str,
    api_key: str,
    max_retries: int,
    html_mode: str = "standalone",
) -> tuple[float, int]:
    """Run the full pipeline for a single video and write output files.

    Returns:
        Tuple of (duration_s, n_steps).
    """
    from .config import Settings
    from .pipeline.generator import DocumentationGenerator

    settings = Settings(provider=provider, api_key=api_key)

    stem = video_path.stem
    video_out_dir = output_dir / stem
    video_out_dir.mkdir(parents=True, exist_ok=True)

    tmp_video = Path(tempfile.mktemp(suffix=video_path.suffix))
    shutil.copy2(video_path, tmp_video)

    try:
        gen = DocumentationGenerator(
            settings=settings,
            video_path=tmp_video,
            html_mode=html_mode,
            max_retries=max_retries,
        )

        result_data: dict | None = None
        for event in gen.generate():
            msg = event.get("message", "")
            pct = event.get("pct", 0)
            logger.info("[%s] %d%% — %s", video_path.name, pct, msg)
            if "result" in event:
                result_data = event["result"]

        if result_data is None:
            raise RuntimeError("Pipeline completata senza risultato")

        import io
        import zipfile

        with zipfile.ZipFile(io.BytesIO(result_data["zip_bytes"]), "r") as zf:
            for name in zf.namelist():
                dest = video_out_dir / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(zf.read(name))

        logger.info("[%s] Output scritto in %s", video_path.name, video_out_dir)
        return result_data["duration_s"], result_data["n_steps"]

    finally:
        tmp_video.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="video-to-docs batch CLI",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--input-dir",
        default=os.environ.get("INPUT_DIR", "./input"),
        help="Cartella con i video da processare",
    )
    parser.add_argument(
        "--output-dir",
        default=os.environ.get("OUTPUT_DIR", "./output"),
        help="Cartella dove scrivere gli output",
    )
    parser.add_argument(
        "--provider",
        default=os.environ.get("PROVIDER", "google"),
        choices=["google", "openrouter"],
        help="Provider AI da usare",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=int(os.environ.get("MAX_RETRIES", "3")),
        help="Numero massimo di retry per ogni video",
    )
    parser.add_argument(
        "--urls-file",
        default=None,
        metavar="PATH",
        help="File .txt con un URL per riga (commenti con # ignorati)",
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Resolve API key
    from .config import get_api_key
    api_key = get_api_key(args.provider) or ""
    if not api_key:
        logger.error(
            "API key non trovata per il provider '%s'. "
            "Imposta la variabile d'ambiente corrispondente nel file .env.",
            args.provider,
        )
        raise SystemExit(1)

    # Build queue: files first, then URLs
    queue: list[QueueItem] = []

    for video_path in _list_videos(input_dir):
        queue.append(QueueItem(name=video_path.name, source="file", path=video_path))

    if args.urls_file:
        urls_file = Path(args.urls_file)
        if not urls_file.exists():
            logger.error("--urls-file non trovato: %s", urls_file)
            raise SystemExit(1)
        for url in _load_urls(urls_file):
            name = url.split("/")[-1] or url
            queue.append(QueueItem(name=name, source="url", url=url))

    if not queue:
        logger.info("Nessun video trovato e nessun URL specificato — nulla da fare.")
        return

    checkpoint = _load_checkpoint(output_dir)
    processed_set: set[str] = set(checkpoint.get("processed", []))
    failed_map: dict[str, str] = checkpoint.get("failed", {})

    logger.info(
        "%d elementi in coda, %d già processati, %d falliti in precedenza.",
        len(queue),
        len(processed_set),
        len(failed_map),
    )

    # Initialise RunLogger
    from .output.run_logger import RunLogger
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_logger = RunLogger(output_dir=output_dir, run_id=run_id)

    succeeded = 0
    failed_count = 0
    skipped_count = 0

    for item in queue:
        if item.name in processed_set:
            logger.info("Skipping %s (già processato)", item.name)
            run_logger.video_skipped(item.name, "già processato")
            skipped_count += 1
            continue

        run_logger.video_start(item.name)
        logger.info("Inizio elaborazione: %s", item.name)

        # For URL items: download to a temp dir first
        tmp_url_dir: Path | None = None
        video_path: Path

        if item.source == "url":
            from .downloader import download_url
            tmp_url_dir = Path(tempfile.mkdtemp(prefix="vd_url_"))
            try:
                logger.info("Download URL: %s", item.url)
                video_path = download_url(item.url, tmp_url_dir)  # type: ignore[arg-type]
            except Exception as exc:
                error_msg = f"{type(exc).__name__}: {exc}"
                logger.error("Download fallito: %s — %s", item.name, error_msg)
                run_logger.video_failed(item.name, 1, args.max_retries, error_msg)
                failed_map[item.name] = error_msg
                checkpoint["failed"] = failed_map
                _save_checkpoint(output_dir, checkpoint)
                failed_count += 1
                shutil.rmtree(tmp_url_dir, ignore_errors=True)
                continue
        else:
            video_path = item.path  # type: ignore[assignment]

        try:
            duration_s, n_steps = _process_video(
                video_path=video_path,
                output_dir=output_dir,
                provider=args.provider,
                api_key=api_key,
                max_retries=args.max_retries,
            )
            processed_set.add(item.name)
            failed_map.pop(item.name, None)
            checkpoint["processed"] = sorted(processed_set)
            checkpoint["failed"] = failed_map
            _save_checkpoint(output_dir, checkpoint)
            run_logger.video_success(item.name, duration_s, n_steps)
            logger.info("Completato: %s", item.name)
            succeeded += 1
        except Exception as exc:
            error_msg = f"{type(exc).__name__}: {exc}"
            logger.error("Fallito: %s — %s", item.name, error_msg)
            run_logger.video_failed(item.name, 1, args.max_retries, error_msg)
            failed_map[item.name] = error_msg
            checkpoint["failed"] = failed_map
            _save_checkpoint(output_dir, checkpoint)
            failed_count += 1
        finally:
            if tmp_url_dir is not None:
                shutil.rmtree(tmp_url_dir, ignore_errors=True)

    total = len(queue)
    run_logger.summary(
        total=total,
        succeeded=succeeded,
        failed=failed_count,
        skipped=skipped_count,
    )
    run_logger.close()

    logger.info(
        "Batch completato. Processati: %d, Falliti: %d, Saltati: %d",
        succeeded,
        failed_count,
        skipped_count,
    )


if __name__ == "__main__":
    main()
