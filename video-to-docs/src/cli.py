"""video-to-docs — CLI entry point per esecuzione batch in Codespace."""
from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import tempfile
from pathlib import Path

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


def _list_videos(input_dir: Path) -> list[Path]:
    return sorted(
        p for p in input_dir.iterdir()
        if p.is_file() and p.suffix.lower() in _VIDEO_EXTENSIONS
    )


def _process_video(
    video_path: Path,
    output_dir: Path,
    provider: str,
    api_key: str,
    max_retries: int,
    html_mode: str = "standalone",
) -> None:
    """Run the full pipeline for a single video and write output files."""
    from .config import Settings
    from .pipeline.generator import DocumentationGenerator
    from .output.txt_builder import build_glossario, build_procedura
    from .output.rag_builder import build_rag_jsonl
    from .output.logger import build_log_txt

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

        # Write individual output files from the ZIP
        # Re-generate outputs directly for clean file writes
        # (generator already has the data — use zip_bytes is easiest)
        import io
        import zipfile

        with zipfile.ZipFile(io.BytesIO(result_data["zip_bytes"]), "r") as zf:
            for name in zf.namelist():
                dest = video_out_dir / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(zf.read(name))

        logger.info("[%s] Output scritto in %s", video_path.name, video_out_dir)

    finally:
        tmp_video.unlink(missing_ok=True)


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

    videos = _list_videos(input_dir)
    if not videos:
        logger.info("Nessun video trovato in %s — nulla da fare.", input_dir)
        return

    checkpoint = _load_checkpoint(output_dir)
    processed_set: set[str] = set(checkpoint.get("processed", []))
    failed_map: dict[str, str] = checkpoint.get("failed", {})

    logger.info(
        "%d video trovati, %d già processati, %d falliti in precedenza.",
        len(videos),
        len(processed_set),
        len(failed_map),
    )

    for video_path in videos:
        name = video_path.name
        if name in processed_set:
            logger.info("Skipping %s (già processato)", name)
            continue

        logger.info("Inizio elaborazione: %s", name)
        try:
            _process_video(
                video_path=video_path,
                output_dir=output_dir,
                provider=args.provider,
                api_key=api_key,
                max_retries=args.max_retries,
            )
            processed_set.add(name)
            failed_map.pop(name, None)
            checkpoint["processed"] = sorted(processed_set)
            checkpoint["failed"] = failed_map
            _save_checkpoint(output_dir, checkpoint)
            logger.info("Completato: %s", name)
        except Exception as exc:
            error_msg = f"{type(exc).__name__}: {exc}"
            logger.error("Fallito: %s — %s", name, error_msg)
            failed_map[name] = error_msg
            checkpoint["failed"] = failed_map
            _save_checkpoint(output_dir, checkpoint)

    logger.info(
        "Batch completato. Processati: %d, Falliti: %d",
        len(processed_set),
        len(failed_map),
    )


if __name__ == "__main__":
    main()
