# CLAUDE.md — Guida per AI assistants

## Struttura del progetto

L'applicazione è suddivisa in moduli sotto `src/`:

- **`src/config.py`** — Caricamento `.env`, dataclass `Settings`, funzione `get_api_key(provider)`.
- **`src/providers/`** — Ogni file implementa `BaseProvider` (da `base.py`) con un metodo `generate()` che ritorna `(raw_json, input_tokens, output_tokens)`.
- **`src/pipeline/`** — Logica di elaborazione: prompt, parsing JSON, estrazione screenshot via ffmpeg, orchestratore `DocumentationGenerator`.
- **`src/output/`** — Generazione artefatti: HTML (standalone e folder), testo (glossario, note), logger in-memory, creazione ZIP in-memory.
- **`app.py`** — UI Streamlit, punto di ingresso.

## Come aggiungere un nuovo provider

1. Crea `src/providers/nuovo_provider.py`
2. Implementa una classe che estende `BaseProvider` da `src/providers/base.py`
3. Il metodo `generate(video_path, mime_type, system_prompt, user_prompt)` deve ritornare `tuple[str, int, int]`
4. Aggiungi il provider in `src/config.py` (`_ENV_KEY_MAP`, `_MODEL_MAP`)
5. Aggiungi il caso in `_make_provider()` dentro `src/pipeline/generator.py`
6. Aggiungi la label nella UI in `app.py` (`PROVIDER_LABELS`)
7. Aggiorna `.env.example` con la nuova variabile d'ambiente

## Convenzioni

- **Type hints** su tutte le funzioni e metodi.
- **Nessun `print()`** nei moduli `src/` — usare solo il `Logger`.
- **ffmpeg** chiamato via `subprocess`, non librerie wrapper Python.
- **Nessuna variabile globale di stato** — tutto passa come parametri.
- File temporanei in `tempfile.mkdtemp()`, puliti dopo la generazione dello ZIP.
- Lo ZIP è sempre generato in-memory (`io.BytesIO`), mai scritto su disco.

## File protetti

**`src/pipeline/prompts.py` NON va modificato senza approvazione esplicita.**
I prompt sono calibrati per ottenere output JSON strutturato dal modello e modificarli
può rompere il parsing downstream.

## Comandi utili

```bash
# Avvio app
streamlit run app.py

# Verifica import
python -c "from src.providers.google import GoogleProvider"
python -c "from src.output.html_builder import build_html_standalone"
```
