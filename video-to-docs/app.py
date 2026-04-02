"""video-to-docs — Streamlit web app per generare documentazione da video."""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import streamlit as st

from src.config import Settings, get_api_key, SUPPORTED_EXTENSIONS, MAX_UPLOAD_MB
from src.pipeline.generator import DocumentationGenerator

# ---------------------------------------------------------------------------
# Costanti per la stima dei costi (USD per 1 M token, approssimativi)
# ---------------------------------------------------------------------------
_COST_TABLE: dict[str, tuple[float, float]] = {
    "google": (0.15, 0.60),       # Gemini 2.5 Flash input/output
    "openrouter": (0.15, 0.60),   # same model via OpenRouter
}

PROVIDER_LABELS: dict[str, str] = {
    "Google Gemini": "google",
    "OpenRouter": "openrouter",
}

HTML_MODE_LABELS: dict[str, str] = {
    "Standalone (base64)": "standalone",
    "Cartella screenshots": "folder",
    "Entrambi": "both",
}

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="video-to-docs",
    page_icon="🎬",
    layout="centered",
)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("Impostazioni")

    provider_label = st.selectbox(
        "Provider AI",
        options=list(PROVIDER_LABELS.keys()),
    )
    provider_key = PROVIDER_LABELS[provider_label]

    env_key = get_api_key(provider_key) or ""
    api_key = st.text_input(
        "API Key",
        value=env_key,
        type="password",
        help="Se lasciato vuoto, verrà usata la chiave dal file .env",
    )

    html_mode_label = st.selectbox(
        "Modalità output HTML",
        options=list(HTML_MODE_LABELS.keys()),
    )
    html_mode = HTML_MODE_LABELS[html_mode_label]

    max_retries = st.slider(
        "Retry per video",
        min_value=1,
        max_value=5,
        value=3,
        help="Numero massimo di tentativi in caso di errore API",
    )

    save_to_disk = st.toggle(
        "Salva output su disco",
        value=False,
        help="Se attivo, scrive i file anche in output/{stem}/ sul server",
    )
    disk_output_dir = "output"

# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------
st.title("video-to-docs")
st.markdown("Carica uno o più video e genera documentazione strutturata con AI.")

# Two input tabs
tab_file, tab_url = st.tabs(["📁 Carica file", "🔗 URL diretti"])

with tab_file:
    uploaded_files = st.file_uploader(
        "Carica video",
        type=SUPPORTED_EXTENSIONS,
        accept_multiple_files=True,
        help=f"Formati supportati: {', '.join(SUPPORTED_EXTENSIONS)}. Max {MAX_UPLOAD_MB} MB per file.",
    )

with tab_url:
    urls_text = st.text_area(
        "URL video (uno per riga)",
        placeholder="https://example.com/tutorial.mp4\nhttps://cdn.example.com/demo.mov",
        help="Inserisci un URL per riga. Righe vuote ignorate.",
    )

# ---------------------------------------------------------------------------
# Build unified queue
# ---------------------------------------------------------------------------
queue: list[dict] = []

for uf in (uploaded_files or []):
    queue.append({"type": "file", "name": uf.name, "data": uf})

for raw_line in (urls_text or "").splitlines():
    line = raw_line.strip()
    if not line:
        continue
    queue.append({"type": "url", "name": line.split("/")[-1] or line, "url": line})

generate_btn = st.button(
    "Genera documentazione",
    type="primary",
    disabled=not queue,
)

if generate_btn and queue:
    # --- Validations ---------------------------------------------------------
    if not api_key:
        st.error("Inserisci una API key nella sidebar o configurala nel file .env.")
        st.stop()

    # Check ffmpeg availability once
    if shutil.which("ffmpeg") is None:
        st.warning(
            "ffmpeg non trovato nel PATH — gli screenshot non verranno estratti. "
            "Installa ffmpeg per abilitare l'estrazione automatica."
        )

    all_results: list[dict] = []

    for idx, item in enumerate(queue, 1):
        item_name = item["name"]
        st.markdown(f"**Video {idx}/{len(queue)}: {item_name}**")

        # ------------------------------------------------------------------
        # Resolve video path (file upload or URL download)
        # ------------------------------------------------------------------
        tmp_video: Path | None = None
        tmp_url_dir: Path | None = None

        if item["type"] == "file":
            uploaded = item["data"]
            file_size_mb = len(uploaded.getvalue()) / (1024 * 1024)

            if file_size_mb > MAX_UPLOAD_MB:
                st.error(
                    f"{item_name}: file {file_size_mb:.1f} MB — il limite è {MAX_UPLOAD_MB} MB. Saltato."
                )
                continue

            if provider_key == "openrouter" and file_size_mb > 19:
                st.error(
                    f"{item_name}: {file_size_mb:.1f} MB. "
                    "OpenRouter supporta al massimo 19 MB. Usa Google Gemini per file più grandi. Saltato."
                )
                continue

            tmp_video = Path(tempfile.mktemp(suffix=Path(item_name).suffix))
            tmp_video.write_bytes(uploaded.getvalue())

        else:
            # URL item — validate and download
            url = item["url"]
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                st.error(f"URL non valido (deve iniziare con http:// o https://): {url}")
                continue

            with st.status(f"Download in corso: {url}...", expanded=False):
                from src.downloader import download_url
                tmp_url_dir = Path(tempfile.mkdtemp(prefix="vd_url_"))
                try:
                    tmp_video = download_url(url, tmp_url_dir)
                    st.write(f"Scaricato: {tmp_video.name}")
                except Exception as exc:
                    st.error(f"{item_name} — Download fallito: {exc}")
                    import shutil as _shutil
                    _shutil.rmtree(tmp_url_dir, ignore_errors=True)
                    tmp_url_dir = None
                    continue

        # ------------------------------------------------------------------
        # Run pipeline
        # ------------------------------------------------------------------
        settings = Settings(
            provider=provider_key,
            api_key=api_key,
        )

        generator = DocumentationGenerator(
            settings=settings,
            video_path=tmp_video,
            html_mode=html_mode,
            max_retries=max_retries,
        )

        progress_bar = st.progress(0)
        status = st.status(f"Avvio generazione {item_name}...", expanded=True)
        result_data: dict | None = None

        try:
            for event in generator.generate():
                pct = event.get("pct", 0)
                msg = event.get("message", "")
                progress_bar.progress(pct / 100, text=msg)
                status.update(label=msg)

                if "result" in event:
                    result_data = event["result"]

            status.update(label="Completato!", state="complete")
        except ValueError as exc:
            status.update(label="Errore", state="error")
            st.error(f"{item_name} — Errore di validazione: {exc}")
            continue
        except Exception as exc:
            status.update(label="Errore", state="error")
            st.error(f"{item_name} — Errore imprevisto: {exc}")
            continue
        finally:
            if tmp_video is not None:
                tmp_video.unlink(missing_ok=True)
            if tmp_url_dir is not None:
                import shutil as _shutil
                _shutil.rmtree(tmp_url_dir, ignore_errors=True)

        if result_data is not None:
            result_data["filename"] = item_name

            # Optionally write to disk
            if save_to_disk:
                import io
                import zipfile

                stem = Path(item_name).stem
                video_out_dir = Path(disk_output_dir) / stem
                video_out_dir.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(io.BytesIO(result_data["zip_bytes"]), "r") as zf:
                    for fname in zf.namelist():
                        dest = video_out_dir / fname
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        dest.write_bytes(zf.read(fname))

            all_results.append(result_data)

    # --- Results -------------------------------------------------------------
    if all_results:
        st.success(f"Completato: {len(all_results)}/{len(queue)} video processati.")

        for result_data in all_results:
            filename = result_data["filename"]
            st.markdown(f"### {filename}")

            col1, col2, col3 = st.columns(3)
            col1.metric("Step trovati", result_data["n_steps"])
            col2.metric("Screenshot estratti", result_data["n_screenshots"])
            col3.metric("Durata", f'{result_data["duration_s"]:.1f}s')

            col4, col5, col6 = st.columns(3)
            col4.metric("Token input", f'{result_data["input_tokens"]:,}')
            col5.metric("Token output", f'{result_data["output_tokens"]:,}')

            costs = _COST_TABLE.get(provider_key, (0, 0))
            cost_usd = (
                result_data["input_tokens"] * costs[0] / 1_000_000
                + result_data["output_tokens"] * costs[1] / 1_000_000
            )
            col6.metric("Costo stimato", f"${cost_usd:.4f}")

            # Preview section
            with st.expander(f"Preview — {filename}"):
                st.markdown(f"**Chunk RAG prodotti:** {result_data['n_rag_chunks']}")
                st.markdown("**procedura.txt**")
                st.text(result_data["procedura_txt"])

            # Per-video download
            stem = Path(filename).stem
            st.download_button(
                label=f"Scarica ZIP — {filename}",
                data=result_data["zip_bytes"],
                file_name=f"video_to_docs_{result_data['title'][:30]}.zip",
                mime="application/zip",
                key=f"dl_{stem}",
            )
