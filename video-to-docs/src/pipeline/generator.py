from __future__ import annotations

import tempfile
import shutil
from pathlib import Path
from typing import Generator

from ..config import Settings, _MODEL_MAP
from ..providers.base import BaseProvider
from ..providers.google import GoogleProvider
from ..providers.openrouter import OpenRouterProvider
from ..output.html_builder import build_html_folder, build_html_standalone
from ..output.txt_builder import build_glossario, build_procedura
from ..output.rag_builder import build_rag_jsonl
from ..output.logger import Logger, build_log_txt
from ..output.zipper import create_zip
from .prompts import SYSTEM_PROMPT, USER_PROMPT
from .parser import parse_response
from .screenshots import extract_screenshots

_MIME_MAP: dict[str, str] = {
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".avi": "video/x-msvideo",
    ".mkv": "video/x-matroska",
    ".webm": "video/webm",
}


def _make_provider(settings: Settings) -> BaseProvider:
    if settings.provider == "google":
        return GoogleProvider(
            api_key=settings.api_key,
            model=settings.model,
            max_retries=settings.max_retries,
        )
    if settings.provider == "openrouter":
        return OpenRouterProvider(
            api_key=settings.api_key,
            model=settings.model,
            max_mb=settings.openrouter_max_mb,
            max_retries=settings.max_retries,
        )
    raise ValueError(f"Provider sconosciuto: {settings.provider!r}")


class DocumentationGenerator:
    """Orchestrates the full documentation pipeline.

    The :meth:`generate` method is a Python **generator** that yields progress
    dicts with keys ``pct``, ``message``, and optionally ``data`` or
    ``result``.
    """

    def __init__(
        self,
        settings: Settings,
        video_path: Path,
        html_mode: str,
        max_retries: int = 3,
    ) -> None:
        self._settings = settings
        self._settings.max_retries = max_retries
        self._video_path = video_path
        self._html_mode = html_mode  # "standalone" | "folder" | "both"

    def generate(self) -> Generator[dict, None, None]:
        logger = Logger()
        tmp_dir = Path(tempfile.mkdtemp(prefix="video_to_docs_"))

        try:
            yield {"pct": 5, "message": "Inizializzazione..."}
            logger.log("INFO", "Pipeline avviata")

            mime = _MIME_MAP.get(
                self._video_path.suffix.lower(), "video/mp4"
            )
            provider = _make_provider(self._settings)
            logger.log("INFO", f"Provider: {self._settings.provider}, modello: {self._settings.model}")

            # --- API call ---
            yield {"pct": 10, "message": "Invio video al modello AI..."}
            import time
            t0 = time.time()
            raw_json, input_tokens, output_tokens = provider.generate(
                video_path=self._video_path,
                mime_type=mime,
                system_prompt=SYSTEM_PROMPT,
                user_prompt=USER_PROMPT,
            )
            duration = time.time() - t0
            logger.log("INFO", f"Risposta ricevuta in {duration:.1f}s  (in={input_tokens}, out={output_tokens})")
            yield {"pct": 55, "message": "Risposta ricevuta dal modello."}

            # --- Parsing ---
            yield {"pct": 60, "message": "Parsing della risposta JSON..."}
            data = parse_response(raw_json)
            n_steps = len(data["steps"])
            logger.log("INFO", f"Parsing OK — {n_steps} step trovati")

            # --- Screenshots ---
            yield {"pct": 60, "message": "Estrazione screenshot dai timestamp..."}
            screenshot_dir = tmp_dir / "screenshots"
            screenshot_map = extract_screenshots(
                self._video_path, data["steps"], screenshot_dir
            )
            n_screenshots = sum(1 for v in screenshot_map.values() if v is not None)
            logger.log("INFO", f"Screenshot estratti: {n_screenshots}/{n_steps}")
            yield {"pct": 75, "message": f"{n_screenshots} screenshot estratti."}

            # --- HTML ---
            files_generated: dict[str, bytes] = {}

            if self._html_mode in ("folder", "both"):
                yield {"pct": 80, "message": "Generazione HTML (cartella)..."}
                html_folder = build_html_folder(data, screenshot_map)
                files_generated["documentazione.html"] = html_folder.encode("utf-8")
                logger.log("INFO", "HTML cartella generato")

            if self._html_mode in ("standalone", "both"):
                yield {"pct": 82, "message": "Generazione HTML (standalone)..."}
                html_sa = build_html_standalone(data, screenshot_map)
                files_generated["documentazione_standalone.html"] = html_sa.encode("utf-8")
                logger.log("INFO", "HTML standalone generato")

            # --- Glossario ---
            yield {"pct": 87, "message": "Generazione glossario..."}
            glossario_txt = build_glossario(data)
            files_generated["glossario.txt"] = glossario_txt.encode("utf-8")
            logger.log("INFO", "Glossario generato")

            # --- Procedura ---
            yield {"pct": 90, "message": "Generazione procedura..."}
            procedura_txt = build_procedura(data, self._video_path.name)
            files_generated["procedura.txt"] = procedura_txt.encode("utf-8")
            logger.log("INFO", "Procedura generata")

            # --- RAG JSONL ---
            yield {"pct": 93, "message": "Generazione RAG chunks..."}
            rag_jsonl = build_rag_jsonl(data, self._video_path.name)
            files_generated["rag_chunks.jsonl"] = rag_jsonl.encode("utf-8")
            logger.log("INFO", f"RAG JSONL generato")

            # --- Log ---
            log_txt = build_log_txt(logger.lines)
            files_generated["log.txt"] = log_txt.encode("utf-8")

            # --- ZIP ---
            yield {"pct": 97, "message": "Creazione archivio ZIP..."}
            zip_bytes = create_zip(
                files=files_generated,
                screenshot_dir=screenshot_dir if self._html_mode in ("folder", "both") else None,
                mode=self._html_mode,
            )
            logger.log("INFO", "ZIP creato in memoria")

            yield {
                "pct": 100,
                "message": "Completato!",
                "result": {
                    "zip_bytes": zip_bytes,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "duration_s": duration,
                    "n_steps": n_steps,
                    "n_screenshots": n_screenshots,
                    "title": data.get("title", "Documentazione"),
                    "procedura_txt": procedura_txt,
                    "n_rag_chunks": rag_jsonl.count("\n") + 1 if rag_jsonl else 0,
                },
            }
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
