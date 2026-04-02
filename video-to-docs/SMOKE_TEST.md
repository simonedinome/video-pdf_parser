# Smoke test — video-to-docs

Eseguire questi test manualmente in Codespace dopo aver configurato la variabile
d'ambiente `GOOGLE_API_KEY` (o `OPENROUTER_API_KEY`) nel file `.env`.

---

## Smoke test — CLI

- [ ] `python -m src.cli --help` mostra tutti gli argomenti incluso `--urls-file`
- [ ] `python -m src.cli` con cartella `input/` vuota termina senza errori
- [ ] `python -m src.cli --urls-file input/urls.example.txt` non crasha (nessun URL da processare)
- [ ] Con un video reale in `input/`: viene processato, `output/` contiene i file, log in `output/logs/`
- [ ] Con `--max-retries 1`: il retry è limitato a 1 tentativo in caso di errore

---

## Smoke test — UI Streamlit

- [ ] `streamlit run app.py` parte senza errori di import
- [ ] Tab "📁 Carica file": upload funziona come prima
- [ ] Tab "🔗 URL diretti": URL non valido (senza `https://`) mostra errore inline
- [ ] Tab "🔗 URL diretti": URL valido viene scaricato e processato
- [ ] Sidebar: slider retry visibile, toggle "Salva su disco" visibile
- [ ] Con "Salva su disco" attivo: i file compaiono in `output/{stem}/`
- [ ] ZIP scaricabile anche in modalità URL
