"""video-to-docs — Streamlit web app per generare documentazione da video."""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import streamlit as st

from src.config import Settings, get_api_key, SUPPORTED_EXTENSIONS, MAX_UPLOAD_MB
from src.pipeline.generator import DocumentationGenerator

# ---------------------------------------------------------------------------
# Costanti per la stima dei costi (USD per 1 M token, approssimativi)
# ---------------------------------------------------------------------------
_COST_TABLE: dict[str, tuple[float, float]] = {
    "google": (0.15, 0.60),       # Gemini 2.5 Flash input/output
    "openrouter": (0.15, 0.60),   # same model via OpenRouter
    "openai": (2.50, 10.00),      # GPT-4o
}

PROVIDER_LABELS: dict[str, str] = {
    "Google Gemini": "google",
    "OpenRouter": "openrouter",
    "OpenAI": "openai",
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

# ---------------------------------------------------------------------------
# Main area
# ---------------------------------------------------------------------------
st.title("video-to-docs")
st.markdown("Carica un video e genera documentazione strutturata con AI.")

uploaded = st.file_uploader(
    "Carica un video",
    type=SUPPORTED_EXTENSIONS,
    help=f"Formati supportati: {', '.join(SUPPORTED_EXTENSIONS)}. Max {MAX_UPLOAD_MB} MB.",
)

generate_btn = st.button("Genera documentazione", type="primary", disabled=uploaded is None)

if generate_btn and uploaded is not None:
    # --- Validations ---------------------------------------------------------
    if not api_key:
        st.error("Inserisci una API key nella sidebar o configurala nel file .env.")
        st.stop()

    file_size_mb = len(uploaded.getvalue()) / (1024 * 1024)
    if file_size_mb > MAX_UPLOAD_MB:
        st.error(f"Il file è {file_size_mb:.1f} MB — il limite è {MAX_UPLOAD_MB} MB.")
        st.stop()

    if provider_key == "openrouter" and file_size_mb > 19:
        st.error(
            f"Il file è {file_size_mb:.1f} MB. "
            "OpenRouter supporta al massimo 19 MB. Usa Google Gemini per file più grandi."
        )
        st.stop()

    # Check ffmpeg availability
    if shutil.which("ffmpeg") is None:
        st.warning(
            "ffmpeg non trovato nel PATH — gli screenshot non verranno estratti. "
            "Installa ffmpeg per abilitare l'estrazione automatica."
        )

    # --- Prepare temp video --------------------------------------------------
    tmp_video = Path(tempfile.mktemp(suffix=Path(uploaded.name).suffix))
    tmp_video.write_bytes(uploaded.getvalue())

    settings = Settings(
        provider=provider_key,
        api_key=api_key,
    )

    generator = DocumentationGenerator(
        settings=settings,
        video_path=tmp_video,
        html_mode=html_mode,
    )

    # --- Run pipeline with progress ------------------------------------------
    progress_bar = st.progress(0)
    status = st.status("Avvio generazione...", expanded=True)
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
        st.error(f"Errore di validazione: {exc}")
    except Exception as exc:
        status.update(label="Errore", state="error")
        st.error(f"Errore imprevisto: {exc}")
    finally:
        tmp_video.unlink(missing_ok=True)

    # --- Results -------------------------------------------------------------
    if result_data is not None:
        st.success("Documentazione generata con successo!")

        # Metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("Step trovati", result_data["n_steps"])
        col2.metric("Screenshot estratti", result_data["n_screenshots"])
        col3.metric("Durata", f'{result_data["duration_s"]:.1f}s')

        col4, col5, col6 = st.columns(3)
        col4.metric("Token input", f'{result_data["input_tokens"]:,}')
        col5.metric("Token output", f'{result_data["output_tokens"]:,}')

        # Cost estimate
        costs = _COST_TABLE.get(provider_key, (0, 0))
        cost_usd = (
            result_data["input_tokens"] * costs[0] / 1_000_000
            + result_data["output_tokens"] * costs[1] / 1_000_000
        )
        col6.metric("Costo stimato", f"${cost_usd:.4f}")

        # Download
        st.download_button(
            label="Scarica ZIP",
            data=result_data["zip_bytes"],
            file_name=f"video_to_docs_{result_data['title'][:30]}.zip",
            mime="application/zip",
            type="primary",
        )
