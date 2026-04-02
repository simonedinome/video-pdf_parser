# CLAUDE.md — Guida per AI assistants

## Struttura del progetto

L'applicazione è suddivisa in moduli sotto `src/`:

- **`src/config.py`** — Caricamento `.env`, dataclass `Settings`, funzione `get_api_key(provider)`.
- **`src/providers/`** — Ogni file implementa `BaseProvider` (da `base.py`) con un metodo `generate()` che ritorna `(raw_json, input_tokens, output_tokens)`. Provider disponibili: `google.py`, `openrouter.py`. La logica di retry è in `retry.py`.
- **`src/pipeline/`** — Logica di elaborazione: prompt, parsing JSON, estrazione screenshot via ffmpeg, orchestratore `DocumentationGenerator`.
- **`src/output/`** — Generazione artefatti: HTML (standalone e folder), testo (`glossario.txt`, `procedura.txt`), RAG JSONL (`rag_chunks.jsonl`), logger in-memory, creazione ZIP in-memory.
- **`app.py`** — UI Streamlit con upload multiplo di video, punto di ingresso web.
- **`src/cli.py`** — Entry point CLI per elaborazione batch in Codespace.

## Provider supportati

Solo Google Gemini e OpenRouter sono supportati. Il provider OpenAI è stato rimosso.

## Struttura output per video

Ogni video produce una cartella `output/{video_stem}/` con:

```
output/
  {video_stem}/
    rag_chunks.jsonl   ← chunk RAG per retrieval semantico
    procedura.txt      ← procedura testuale leggibile (e dai tokenizer)
    glossario.txt      ← glossario dei termini tecnici
    log.txt            ← log della generazione
    [documentazione.html o documentazione_standalone.html]  ← solo se html_mode != none
  processed.json       ← checkpoint batch (root level)
```

## RAG JSONL — src/output/rag_builder.py

Funzione: `build_rag_jsonl(data: dict, video_filename: str) -> str`

Produce tre tipi di chunk per video:
- `{stem}_summary` — sommario del video con prerequisiti
- `{stem}_step_NNN` — un chunk per step, con `embedding_keywords` e `glossary_terms`
- `{stem}_glossary` — glossario completo

Il campo `embedding_keywords` in ogni step è generato dal modello AI (5-8 keyword dense per retrieval semantico). Se assente o non-lista viene normalizzato a `[]` dal parser.

## CLI batch — src/cli.py

Entry point per elaborazione batch. Legge video da `input/`, scrive in `output/`.

```bash
# Esecuzione base
python -m src.cli

# Con opzioni
python -m src.cli --provider google --input-dir ./input --output-dir ./output --max-retries 3
```

Variabili d'ambiente supportate: `PROVIDER`, `INPUT_DIR`, `OUTPUT_DIR`, `MAX_RETRIES`.

Il checkpoint `output/processed.json` tiene traccia dei video già elaborati e dei fallimenti, permettendo di riprendere il batch senza rielaborare i video già completati.

## Retry logic — src/providers/retry.py

Funzione: `with_retry(fn, max_attempts=3, base_delay=5.0)`

- Backoff lineare: 5s, 10s, 15s
- Usato in `google.py` per `generate_content()` e in `openrouter.py` per `chat.completions.create()`
- NON wrappare l'upload su Files API di Google (è idempotente lato server)

## Come aggiungere un nuovo provider

1. Crea `src/providers/nuovo_provider.py`
2. Implementa una classe che estende `BaseProvider` da `src/providers/base.py`
3. Il metodo `generate(video_path, mime_type, system_prompt, user_prompt)` deve ritornare `tuple[str, int, int]`
4. Usa `with_retry()` da `retry.py` per wrappare le chiamate API
5. Aggiungi il provider in `src/config.py` (`_ENV_KEY_MAP`, `_MODEL_MAP`)
6. Aggiungi il caso in `_make_provider()` dentro `src/pipeline/generator.py`
7. Aggiungi la label nella UI in `app.py` (`PROVIDER_LABELS`, `_COST_TABLE`)
8. Aggiorna `.env.example` con la nuova variabile d'ambiente

## Convenzioni

- **Type hints** su tutte le funzioni e metodi.
- **Nessun `print()`** nei moduli `src/` — usare solo il `Logger` (o `logging` nel CLI).
- **ffmpeg** chiamato via `subprocess`, non librerie wrapper Python.
- **Nessuna variabile globale di stato** — tutto passa come parametri.
- File temporanei in `tempfile.mkdtemp()`, puliti dopo la generazione dello ZIP.
- Lo ZIP è sempre generato in-memory (`io.BytesIO`), mai scritto su disco (tranne nel CLI).

## File protetti

**`src/pipeline/prompts.py` NON va modificato senza approvazione esplicita.**
I prompt sono calibrati per ottenere output JSON strutturato dal modello e modificarli
può rompere il parsing downstream.

## Comandi utili

```bash
# Avvio app web
streamlit run app.py

# Elaborazione batch CLI
python -m src.cli --input-dir ./input --output-dir ./output

# Verifica import
python -c "from src.providers.google import GoogleProvider"
python -c "from src.output.rag_builder import build_rag_jsonl"
python -c "from src.output.txt_builder import build_procedura"
python -c "from src.providers.retry import with_retry"
```
