# video-to-docs

Applicazione Streamlit per generare documentazione strutturata a partire da video tutorial.

Carica un video, scegli il provider AI (Google Gemini, OpenRouter, OpenAI) e scarica un pacchetto ZIP con:

- **HTML** della procedura documentata (standalone con immagini base64 o con cartella screenshots)
- **Glossario** dei termini tecnici in formato testo
- **Note** e suggerimenti in formato testo
- **Log** della generazione

## Requisiti

- Python 3.11+
- ffmpeg installato e nel PATH (per l'estrazione degli screenshot)

## Setup

```bash
cd video-to-docs
cp .env.example .env
# Inserisci le tue API key nel file .env

pip install -r requirements.txt
streamlit run app.py
```

## Provider supportati

| Provider | Modello | Limite file |
|---|---|---|
| Google Gemini | gemini-2.5-flash | Upload via Files API |
| OpenRouter | google/gemini-2.5-flash | 19 MB (base64) |
| OpenAI | gpt-4o | Base64 encoding |

## Struttura

```
video-to-docs/
├── app.py                  # UI Streamlit
├── .env.example
├── requirements.txt
└── src/
    ├── config.py           # Settings e env loading
    ├── providers/          # Integrazioni AI
    │   ├── base.py         # Abstract BaseProvider
    │   ├── google.py       # Google Gemini
    │   ├── openrouter.py   # OpenRouter
    │   └── openai_provider.py  # OpenAI
    ├── pipeline/           # Logica di elaborazione
    │   ├── prompts.py      # System e user prompt
    │   ├── parser.py       # JSON parsing e validazione
    │   ├── screenshots.py  # Estrazione frame con ffmpeg
    │   └── generator.py    # Orchestratore pipeline
    └── output/             # Generazione artefatti
        ├── html_builder.py # HTML standalone e cartella
        ├── txt_builder.py  # Glossario e note in testo
        ├── logger.py       # Logger in-memory
        └── zipper.py       # Creazione ZIP in memoria
```
